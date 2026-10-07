"""Strategy B: EM carry timed by the global geopolitical prediction-market index (spec 7).

Base portfolio (spec 7.2): at each month-end, sort the eligible EM currencies by 1-month
forward-implied carry (carry = s - f, annualised; s, f = log USD price of one unit of
the currency). Long the top `n_long`, short the bottom `n_short`, risk weights 1/sigma
(60-day volatility), both legs with equal gross, scaled to the volatility target with
the ex-ante covariance at the rebalance date, then held for the month.

Timing (spec 7.4 as amended by D16), exposure w(t) in [0, 1] multiplies the base portfolio:
  - escalation, monthly: w_escalation = 1 if the escalation z-score < z1, 0.5 if in
    [z1, z2), 0 if >= z2 (escalation = EWMA of daily index changes, a stationary measure);
  - shock, daily: on a confirmed shock, w = min(w, cut) from that snapshot;
  - asymmetric re-risking: after the last confirmed shock, w rises linearly back to
    w_escalation over `rerisk_days` trading days, unless a new shock occurs.
The same rule run on VIX (expanding z-score of the VIX level, which is stationary, and
daily VIX-change shocks) is the benchmark
that answers "is the prediction-market index just VIX?".
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.backtest import engine

PPY = 252


@dataclass
class TimingParams:
    z_cuts: tuple[float, float] = (1.0, 2.0)
    escalation_weights: tuple[float, float, float] = (1.0, 0.5, 0.0)
    shock_cut: float = 0.25
    rerisk_days: int = 10
    exec_lag: int = 0   # trading days between signal snapshot and execution


def month_ends(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    s = pd.Series(index, index=index)
    return pd.DatetimeIndex(s.groupby(index.to_period("M")).max().values)


def _cap_leg(w: pd.Series, cap_in_leg: float) -> tuple[pd.Series, bool]:
    """Water-filling: no name above `cap_in_leg` of its leg; excess redistributed pro rata to
    the uncapped names. Returns equal weights (flag True) when the cap is infeasible."""
    if len(w) * cap_in_leg < 1.0 - 1e-12:
        return pd.Series(1.0 / len(w), index=w.index), True
    w = w / w.sum()
    for _ in range(50):
        over = w > cap_in_leg + 1e-12
        if not over.any():
            break
        excess = (w[over] - cap_in_leg).sum()
        w[over] = cap_in_leg
        free = ~over & (w < cap_in_leg)
        w[free] += excess * w[free] / w[free].sum()
    return w, False


def leg_size(n_available: int, rule: str = "tercile", fixed: int = 3) -> int:
    """Names per leg: floor(N/3), at least 1 (D23), or a fixed number."""
    return max(1, n_available // 3) if rule == "tercile" else fixed


def base_carry_weights(carry: pd.DataFrame, returns: pd.DataFrame, n_long: int = 3,
                       n_short: int = 3, vol_lookback: int = 60, target_vol: float = 0.10,
                       long_only: bool = False, universe: pd.DataFrame | None = None,
                       leg_rule: str = "fixed", single_cap: float | None = None) -> pd.DataFrame:
    """leg_rule='tercile': long the top tercile, short the bottom tercile (D23).
    single_cap: maximum share of gross exposure per currency (D23 variant)."""
    """Monthly carry sort, inverse-vol risk weights, vol-targeted at the rebalance date.

    carry, returns: trading-day x currency. universe: optional boolean mask of eligible
    currencies (True = tradable) on each date.
    """
    idx = returns.index
    rebal = month_ends(idx)
    vol = returns.rolling(vol_lookback, min_periods=40).std() * np.sqrt(PPY)
    covs = engine.ewma_cov(returns.fillna(0.0), span=vol_lookback)
    w = pd.DataFrame(np.nan, index=idx, columns=returns.columns)
    for t in rebal:
        known = carry.loc[:t]
        if known.empty:
            continue
        c = known.iloc[-1]
        ok = c.notna() & vol.loc[t].notna()
        if universe is not None:
            ok &= universe.reindex(index=[t], columns=c.index).iloc[0].fillna(False).astype(bool)
        c = c[ok]
        nl = leg_size(len(c), leg_rule, n_long)
        ns = 0 if long_only else leg_size(len(c), leg_rule, n_short)
        if len(c) < nl + ns or nl < 1:
            continue
        ranked = c.sort_values()
        longs = ranked.index[-nl:]
        shorts = [] if long_only else list(ranked.index[:ns])
        iv = 1.0 / vol.loc[t]
        wt = pd.Series(0.0, index=returns.columns)
        legs = [(list(longs), 1.0)] + ([(shorts, -1.0)] if shorts else [])
        for names, sgn in legs:
            lw = iv[names] / iv[names].sum()
            if single_cap is not None:
                lw, _ = _cap_leg(lw, single_cap * len(legs))   # share of gross -> share of leg
            wt[names] = sgn * lw
        if t in covs:
            cov = covs[t].loc[wt.index, wt.index].values
            pv = float(np.sqrt(max(wt.values @ cov @ wt.values, 0.0)) * np.sqrt(PPY))
            if pv > 0:
                wt *= target_vol / pv
        w.loc[t] = wt
    return w.ffill().fillna(0.0)


def escalation_component(esc_z: pd.Series, index: pd.DatetimeIndex, p: TimingParams) -> pd.Series:
    """Monthly escalation exposure set at each month-end from the z-score known then
    (full exposure until the first z-score exists, i.e. during the burn-in)."""
    z = esc_z.reindex(index, method="ffill")
    rebal = month_ends(index)
    wl = pd.Series(np.nan, index=index)
    zr = z.loc[rebal]
    wl.loc[rebal] = np.select([zr < p.z_cuts[0], zr < p.z_cuts[1]],
                              [p.escalation_weights[0], p.escalation_weights[1]], p.escalation_weights[2])
    wl[zr.isna().reindex(index, fill_value=False)] = p.escalation_weights[0]
    return wl.ffill().fillna(p.escalation_weights[0])


def timing_exposure(esc_z: pd.Series, shocks: pd.Series, index: pd.DatetimeIndex,
                    p: TimingParams) -> pd.DataFrame:
    """Exposure w(t) on trading days. `shocks` is a boolean calendar-day series of
    confirmed shocks; shocks on non-trading days are carried to the next trading day."""
    wl = escalation_component(esc_z, index, p)
    sh = shocks.astype(bool)
    # Map calendar-day shocks to the next trading day (weekend shocks hit at Monday's snapshot).
    pos = index.searchsorted(sh[sh].index)
    hit = pd.Series(False, index=index)
    hit.iloc[np.unique(pos[pos < len(index)])] = True
    if p.exec_lag:
        hit = hit.shift(p.exec_lag, fill_value=False)
    w = np.empty(len(index))
    since = np.inf
    for i, t in enumerate(index):
        target = wl.iloc[i]
        if hit.iloc[i]:
            since = 0
        else:
            since += 1
        if since == 0:
            w[i] = min(target, p.shock_cut)
        elif since <= p.rerisk_days:
            start = min(target, p.shock_cut)
            w[i] = start + (target - start) * since / p.rerisk_days
        else:
            w[i] = target
    return pd.DataFrame({"w": w, "w_escalation": wl.values, "shock": hit.values}, index=index)


def tilt_weights(returns: pd.DataFrame, longs: list[str], shorts: list[str], vol_lookback: int = 60,
                 target_vol: float = 0.10) -> pd.DataFrame:
    """B2 (spec 7.5): long oil exporters, short oil importers, inverse-vol inside each leg,
    equal gross per leg, scaled daily to the volatility target with the covariance known at t."""
    vol = returns.rolling(vol_lookback, min_periods=40).std() * np.sqrt(PPY)
    covs = engine.ewma_cov(returns.fillna(0.0), span=vol_lookback)
    w = pd.DataFrame(0.0, index=returns.index, columns=returns.columns)
    for t in returns.index:
        if t not in covs or vol.loc[t, longs + shorts].isna().any():
            continue
        iv = 1.0 / vol.loc[t]
        wt = pd.Series(0.0, index=returns.columns)
        wt[longs] = iv[longs] / iv[longs].sum()
        wt[shorts] = -iv[shorts] / iv[shorts].sum()
        cov = covs[t].loc[wt.index, wt.index].values
        pv = float(np.sqrt(max(wt.values @ cov @ wt.values, 0.0)) * np.sqrt(PPY))
        w.loc[t] = wt * (target_vol / pv) if pv > 0 else 0.0
    return w


def brent_shocks(brent: pd.Series, k: float = 2.0, span: int = 60) -> pd.Series:
    """Brent-triggered benchmark for B2: daily log change of the front-month future above
    k times its EWMA standard deviation (known before the day)."""
    r = np.log(brent.dropna()).diff()
    sd = np.sqrt((r ** 2).ewm(span=span, min_periods=20).mean().shift(1))
    return r > k * sd


def vix_signals(vix: pd.Series, k: float = 2.0, span: int = 60) -> tuple[pd.Series, pd.Series]:
    """Benchmark timing inputs from VIX: expanding level z-score and daily-change shocks."""
    v = vix.dropna()
    z = (v - v.expanding(min_periods=60).mean()) / v.expanding(min_periods=60).std()
    dv = v.diff()
    sd = np.sqrt((dv ** 2).ewm(span=span, min_periods=20).mean().shift(1))
    return z, dv > k * sd
