"""Vectorised daily backtest engine.

Timing convention (spec 12): weights decided at the snapshot of day t use information up
to t only and earn the excess return from t to t+1, which `returns` stores on row t+1.
So pnl(t+1) = sum_i w_i(t) * r_i(t+1). Trading costs are paid at t on |w(t) - w(t-1)|.

Portfolio construction helpers:
  - `vol_target`: scales raw positions so that ex-ante volatility (EWMA covariance from
    returns up to t) equals the target, then applies the gross-leverage cap and the
    single-asset cap (share of gross);
  - `no_trade_band`: keeps the previous position unless the target moves by more than
    `band` times the current position (spec 6.5).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

PPY = 252


def ewma_cov(returns: pd.DataFrame, span: int = 60, min_periods: int = 20) -> dict:
    """EWMA covariance matrices known at each date t (built from returns up to and including t)."""
    r = returns.fillna(0.0)
    alpha = 2.0 / (span + 1.0)
    covs, S, n = {}, None, 0
    for t, row in r.iterrows():
        x = row.values[:, None]
        S = x @ x.T if S is None else (1 - alpha) * S + alpha * (x @ x.T)
        n += 1
        if n >= min_periods:
            covs[t] = pd.DataFrame(S, index=r.columns, columns=r.columns)
    return covs


def _scale(w: pd.Series, cov: np.ndarray, target_vol: float, gross_cap: float,
           single_cap_share: float | None):
    """Scale one day's raw weights to the volatility target, then apply the per-pair and gross
    caps. Returns (weights or None, per-pair cap binds, gross cap binds)."""
    vol = float(np.sqrt(max(w.values @ cov @ w.values, 0.0)) * np.sqrt(PPY))
    if vol <= 0:
        return None, False, False
    w = w * (target_vol / vol)
    pair = False
    if single_cap_share is not None and len(w) > 1:
        g = w.abs().sum()
        clipped = w.clip(-single_cap_share * g, single_cap_share * g)
        pair = bool((clipped - w).abs().max() > 1e-12)
        w = clipped
    g = w.abs().sum()
    gross = bool(g > gross_cap)
    if gross:
        w = w * (gross_cap / g)
    return w, pair, gross


def vol_target(raw: pd.DataFrame, returns: pd.DataFrame, target_vol: float, span: int = 60,
               gross_cap: float = 3.0, single_cap_share: float | None = 0.30) -> pd.DataFrame:
    covs = ewma_cov(returns.reindex(columns=raw.columns), span)
    out = pd.DataFrame(0.0, index=raw.index, columns=raw.columns)
    for t in raw.index:
        w = raw.loc[t].fillna(0.0)
        if t not in covs or not np.any(np.abs(w.values) > 1e-12):
            continue
        w, _, _ = _scale(w, covs[t].loc[w.index, w.index].values, target_vol, gross_cap, single_cap_share)
        if w is not None:
            out.loc[t] = w
    return out


def cap_flags(raw: pd.DataFrame, returns: pd.DataFrame, target_vol: float, span: int = 60,
              gross_cap: float = 3.0, single_cap_share: float | None = 0.30) -> pd.DataFrame:
    """For each day with a non-zero target: whether the per-pair cap and the gross cap bind in
    vol_target (same computation, before the no-trade band)."""
    covs = ewma_cov(returns.reindex(columns=raw.columns), span)
    rows = {}
    for t in raw.index:
        w = raw.loc[t].fillna(0.0)
        if t not in covs or not np.any(np.abs(w.values) > 1e-12):
            continue
        out, pair, gross = _scale(w, covs[t].loc[w.index, w.index].values, target_vol, gross_cap, single_cap_share)
        if out is not None:
            rows[t] = {"pair_cap": pair, "gross_cap": gross}
    return pd.DataFrame.from_dict(rows, orient="index", columns=["pair_cap", "gross_cap"])


def no_trade_band(target: pd.DataFrame, band: float) -> pd.DataFrame:
    if band <= 0:
        return target
    held = target.copy()
    prev = pd.Series(0.0, index=target.columns)
    for t in target.index:
        tgt = target.loc[t].fillna(0.0)
        move = (tgt - prev).abs()
        trade = (move > band * prev.abs()) | (prev == 0) | (tgt == 0)
        prev = prev.where(~trade, tgt)
        held.loc[t] = prev
    return held


@dataclass
class BacktestResult:
    weights: pd.DataFrame
    gross_ret: pd.Series
    costs: pd.Series
    net_ret: pd.Series
    turnover: pd.Series
    gross_exposure: pd.Series
    pnl_by_asset: pd.DataFrame


def run(weights: pd.DataFrame, returns: pd.DataFrame, half_spread: pd.DataFrame | float = 0.0,
        cost_mult: float = 1.0, roll_cost: pd.DataFrame | None = None) -> BacktestResult:
    """weights[t]: position held from t to t+1; returns[t+1]: excess return over that day;
    half_spread: cost per unit of traded notional (decimal), scalar or same shape as weights;
    roll_cost: cost per unit of held notional on roll days (decimal), same shape or None."""
    idx = returns.index.union(weights.index)
    w = weights.reindex(idx).ffill().fillna(0.0).reindex(columns=returns.columns, fill_value=0.0)
    r = returns.reindex(idx).fillna(0.0)
    pnl = w.shift(1).fillna(0.0) * r
    dw = w.diff().abs()
    dw.iloc[0] = w.iloc[0].abs()
    hs = half_spread if np.isscalar(half_spread) else half_spread.reindex(idx).ffill().reindex(
        columns=w.columns).fillna(0.0)
    cost = (dw * hs).sum(axis=1) * cost_mult
    if roll_cost is not None:
        rc = roll_cost.reindex(idx).reindex(columns=w.columns).fillna(0.0)
        cost = cost + (w.abs() * rc).sum(axis=1) * cost_mult
    gross = pnl.sum(axis=1)
    return BacktestResult(weights=w, gross_ret=gross, costs=cost, net_ret=gross - cost,
                          turnover=dw.sum(axis=1), gross_exposure=w.abs().sum(axis=1),
                          pnl_by_asset=pnl)
