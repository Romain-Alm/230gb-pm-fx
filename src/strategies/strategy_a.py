"""Strategy A: G10 currencies on prediction-market theme signals (spec 6; DECISIONS D2, D14, D15).

Cell signal (per zone x theme, calendar days):
  1. daily index change d(t) (volume-weighted); deadline drift is removed upstream by the
     hazard-rate transform (D18); the causal demeaning of D12 is a robustness variant;
  2. smoothed with an EWMA of half-life `ewma_halflife_days` (spec 4.6);
  3. scaled by its expanding standard deviation up to t-1 (equal risk across themes),
     only once the cell has `MIN_ACTIVE` active days.
Signals are sampled at the FX snapshot of each trading day.

Theory signs (effect of a higher cell signal on the zone's currency):
  MONETARY +1 (hawkish), INFLATION +1 (inflation-targeting central bank tightens),
  FISCAL_POLITICAL +1 under monetary dominance and -1 under fiscal dominance, with the
  regime given by the lagged yield-currency correlation (spec 6.4 as amended),
  TRADE_TARIFFS -1 (restriction affecting the zone), own-zone GEOPOLITICS -1 (non-US
  zones only; US geopolitics has no clear sign and is not used).
Spillovers (spec 6.3): GLOBAL GEOPOLITICS +1 on JPY and CHF (safe haven); oil-relevant
geopolitics +1 on NOK and CAD (terms of trade); CN TRADE_TARIFFS -1 on AUD and NZD;
JP FISCAL_POLITICAL on EUR/USD and USD/JPY is left out (its channel has no clear sign).

A pair p (foreign zone i against USD) has forecast
  y(p,t) = sum_k s_k(i,t) z_{i,k}(t) - sum_k s_k(US,t) z_{US,k}(t) + spillovers(p,t),
the expected excess return of the foreign currency. Variants (D14, D17):
  A1  dollar leg only (US MONETARY, US FISCAL regime-signed);
  A2  all G10 cells (USD 10k indices), each contributing when active;
  A3  only the cells that pass the coverage rule (spec strict);
  '+S' versions add the themes built from Strategy B's contracts (geopolitics, trade,
  spillovers); they are reported variants, with their correlation to B.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.backtest import engine

PAIRS = {"EUR": "EA", "JPY": "JP", "GBP": "UK", "CHF": "CH", "AUD": "AU", "NZD": "NZ",
         "CAD": "CA", "NOK": "NO", "SEK": "SE"}
THEMES = ["MONETARY", "INFLATION", "FISCAL_POLITICAL", "TRADE_TARIFFS", "GEOPOLITICS"]
STATIC_SIGN = {"MONETARY": 1.0, "INFLATION": 1.0, "TRADE_TARIFFS": -1.0, "GEOPOLITICS": -1.0}
SPILLOVERS = [  # (target currencies, zone, theme, sign)
    (("JPY", "CHF"), "GLOBAL", "GEOPOLITICS", 1.0),
    (("NOK", "CAD"), "GLOBAL", "GEO_OIL", 1.0),
    (("AUD", "NZD"), "CN", "TRADE_TARIFFS", -1.0),
]
MIN_ACTIVE = 20


def cell_signal(cell: pd.DataFrame, halflife: float, demean: bool = False) -> pd.Series:
    """Equal-risk smoothed signal for one cell (calendar-day index). demean=True applies the
    causal demeaning of D12 (robustness variant; the primary treatment of deadline drift is
    the hazard-rate transform of D18)."""
    c = cell.sort_values("day").set_index("day")
    active = c["n_contracts"] > 0
    if demean:
        mu = c["d_vw"].where(active).expanding().mean().shift(1).ffill().fillna(0.0)
    else:
        mu = 0.0
    d_adj = (c["d_vw"] - mu).where(active, 0.0)
    s = d_adj.ewm(halflife=halflife).mean()
    n_active = active.cumsum().shift(1).fillna(0)
    sd = s.where(n_active > 0).expanding(min_periods=MIN_ACTIVE).std().shift(1)
    z = (s / sd).where(n_active >= MIN_ACTIVE)
    return z.fillna(0.0)


def all_cell_signals(index: pd.DataFrame, halflife: float, demean: bool = False) -> dict[tuple[str, str], pd.Series]:
    return {(z, t): cell_signal(g, halflife, demean) for (z, t), g in index.groupby(["zone", "theme"])}


def fiscal_regime(yield_10y: pd.DataFrame, fx_value: pd.DataFrame, window: int = 60) -> pd.DataFrame:
    """1 = fiscal dominance (negative rolling correlation between daily changes in the
    10-year yield and the currency value), lagged one day. Columns are zones; fx_value
    holds the log value of each zone's currency (for US: dollar against the G10 basket)."""
    out = {}
    for z in yield_10y.columns.intersection(fx_value.columns):
        dy, dfx = yield_10y[z].diff(), fx_value[z].diff()
        corr = dy.rolling(window, min_periods=window // 2).corr(dfx)
        out[z] = (corr < 0).astype(float).where(corr.notna()).shift(1)
    return pd.DataFrame(out)


def pair_components(signals: dict, days: pd.DatetimeIndex, cells: set[tuple[str, str]],
                    regime: pd.DataFrame | None = None, use_spillovers: bool = True,
                    debt: dict | None = None) -> dict[str, pd.DataFrame]:
    """Signed theory components per theme for the 9 pairs (trading days x pairs).

    Each component is the contribution to the foreign currency's expected excess return:
    foreign-leg term minus US-leg term (spec 5), plus spillover components. Also returns
    the UNSIGNED fiscal component and its regime and debt interactions, used by the
    regression diagnostics (spec 6.4 as amended), under keys starting with '_'.
    """
    def sig(z, t):
        if (z, t) not in cells or (z, t) not in signals:
            return pd.Series(0.0, index=days)
        return signals[(z, t)].reindex(days, method="ffill").fillna(0.0)

    def reg(zone):
        if regime is None or zone not in regime:
            return pd.Series(0.0, index=days)       # monetary-dominance baseline (b0 > 0)
        return regime[zone].reindex(days, method="ffill").fillna(0.0)

    def leg(zone, theme):
        if theme == "GEOPOLITICS" and zone == "US":
            return pd.Series(0.0, index=days)
        if theme == "FISCAL_POLITICAL":
            return np.where(reg(zone) == 1, -1.0, 1.0) * sig(zone, theme)
        return STATIC_SIGN[theme] * sig(zone, theme)

    comps: dict[str, dict[str, pd.Series]] = {}
    for ccy, zone in PAIRS.items():
        for t in THEMES:
            comps.setdefault(t, {})[ccy] = leg(zone, t) - leg("US", t)
        f_i, f_us = sig(zone, "FISCAL_POLITICAL"), sig("US", "FISCAL_POLITICAL")
        comps.setdefault("_fiscal_raw", {})[ccy] = f_i - f_us
        comps.setdefault("_fiscal_x_regime", {})[ccy] = f_i * reg(zone) - f_us * reg("US")
        if debt:
            comps.setdefault("_fiscal_x_debt", {})[ccy] = f_i * debt.get(zone, 0.0) - f_us * debt.get("US", 0.0)
        if use_spillovers:
            for targets, z, t, sgn in SPILLOVERS:
                key = f"SPILL_{z}_{t}"
                comps.setdefault(key, {})[ccy] = (sgn * sig(z, t)) if ccy in targets else pd.Series(0.0, index=days)
    return {k: pd.DataFrame(v, index=days) for k, v in comps.items()}


def pair_forecasts(signals: dict, days: pd.DatetimeIndex, cells: set[tuple[str, str]],
                   regime: pd.DataFrame | None = None, use_spillovers: bool = True,
                   weights: dict[str, float] | None = None) -> pd.DataFrame:
    """Forecast y(p,t): sum of the signed components (theory rule), or a weighted sum with
    estimated coefficients `weights` (regression-gated variant)."""
    comps = pair_components(signals, days, cells, regime, use_spillovers)
    keys = [k for k in comps if not k.startswith("_")]
    if weights is not None:
        keys = [k for k in keys if k in weights]
    y = sum(comps[k] * (1.0 if weights is None else weights[k]) for k in keys)
    return y if isinstance(y, pd.DataFrame) else pd.DataFrame(0.0, index=days, columns=list(PAIRS))


# Themes built from the same contracts as Strategy B's index (D17): every geopolitics contract
# carries the GLOBAL zone and every tariff contract the US zone.
B_THEMES = {"GEOPOLITICS", "GEO_OIL", "GEO_TRADE", "TRADE_TARIFFS"}
SPILL_CELLS = {("GLOBAL", "GEOPOLITICS"), ("GLOBAL", "GEO_OIL"), ("CN", "TRADE_TARIFFS")}


def variant_cells(variant: str, available: set[tuple[str, str]], kept: set[tuple[str, str]]) -> set:
    """Cells used by a variant (D14, D17). 'A1', 'A2', 'A3' exclude the themes of Strategy B's
    index; the '+S' versions add them back (spillovers, own-zone geopolitics and trade) and
    are reported variants."""
    base, with_b = variant.split("+")[0], variant.endswith("+S")
    if base == "A1":
        cells = {("US", "MONETARY"), ("US", "FISCAL_POLITICAL")}
    elif base == "A2":
        g10 = set(PAIRS.values()) | {"US"}
        cells = {c for c in available if c[0] in g10}
    elif base == "A3":
        cells = set(kept)
    else:
        raise ValueError(variant)
    if with_b:
        cells |= SPILL_CELLS
    else:
        cells = {c for c in cells if c[1] not in B_THEMES}
    return cells & available


def raw_positions(forecast: pd.DataFrame, returns: pd.DataFrame, cfg: dict,
                  dollar_neutral: bool) -> pd.DataFrame:
    """Unscaled positions: forecast / sigma^2 (demeaned across pairs if dollar-neutral)."""
    a = cfg["strategy_a"]
    y = forecast.sub(forecast.mean(axis=1), axis=0) if dollar_neutral else forecast
    # A forecast identical across pairs (pure dollar signal) has no dollar-neutral content:
    # zero out floating-point residuals so the volatility target cannot amplify them.
    y = y.where(y.abs() > 1e-9, 0.0)
    var = returns.ewm(span=a["cov_ewma_span_days"], min_periods=20).var()
    return (y / var.reindex(y.index)).replace([np.inf, -np.inf], np.nan).fillna(0.0)


def positions(forecast: pd.DataFrame, returns: pd.DataFrame, cfg: dict,
              dollar_neutral: bool) -> pd.DataFrame:
    """Position proportional to forecast / sigma^2, then vol target, caps and no-trade band."""
    a = cfg["strategy_a"]
    raw = raw_positions(forecast, returns, cfg, dollar_neutral)
    w = engine.vol_target(raw, returns, a["vol_target_annual"], a["cov_ewma_span_days"],
                          a["gross_leverage_cap"], a["single_pair_cap_share"])
    return engine.no_trade_band(w, a["no_trade_band"])
