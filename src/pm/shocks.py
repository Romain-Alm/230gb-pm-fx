"""Global geopolitical index: level and confirmed shocks (spec 4.6, 7.3).

Composite contracts: GEOPOLITICS (zone GLOBAL) and US TRADE_TARIFFS, signed so that
higher = more escalation / restriction, standardised and volume-weighted (no weighting
by estimated market impact).

  d(t)            aggregated standardised change at the snapshot of t
  sigma(t)        EWMA (span 60) volatility of d, using changes strictly before t
  escalation(t)   EWMA (half-life `geo_escalation_halflife_days`) of the daily changes d,
                  i.e. the recent escalation trend (DECISIONS D16)
  escalation_z(t) expanding z-score of escalation(t), data up to t only, set only after a
                  burn-in of `geo_escalation_burnin_days` trading days
  level_z_spec_misspecified(t)  the original spec rule (expanding z-score of the EWMA of
                  the index LEVEL); misspecified because the cumulative index is a random
                  walk, kept only as a reported variant
  shock_raw   d(t) > k sigma(t)  (escalation only)
  confirmed   shock_raw and all of:
                - persistence: the move was already > k/2 sigma using prices at least
                  `shock_persist_hours` before the snapshot, or the two-day move
                  d(t-1) + d(t) still exceeds k sigma (shock late on t-1, confirmed at t);
                - volume: USD volume of contributing contracts >= `shock_min_volume_usd`;
                - cross-platform: when both venues contribute, both sub-indices moved up.

Output: data/processed/geo_signals.parquet (one row per calendar day)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.common import get_logger, load_config, rpath

log = get_logger("shocks")


def _vw(df: pd.DataFrame, col: str) -> pd.Series:
    d = df[df[col].notna()]
    return (d[col] * d["vol7d"]).groupby(d["day"]).sum() / d["vol7d"].groupby(d["day"]).sum()


def composite_rows(cfg: dict, proc, cd_file: str = "contract_days.parquet",
                   ch_file: str = "contract_changes.parquet", placebo: bool = False,
                   exclude_events: tuple = ()) -> pd.DataFrame:
    """Eligible contract-days of the global composite (or of the placebo cell), with their
    standardised changes. `exclude_events` drops events (leave-one-event-out)."""
    cd = pd.read_parquet(proc / cd_file,
                         columns=["contract_id", "platform", "event_key", "theme", "zone", "day",
                                  "eligible", "vol7d", "vol1d", "oil_relevant"])
    cd["day"] = pd.to_datetime(cd["day"])
    ch = pd.read_parquet(proc / ch_file, columns=["contract_id", "day", "z", "z_early"])
    if placebo:
        sel = cd[cd["theme"] == "PLACEBO"]
    else:
        sel = cd[((cd["theme"] == "GEOPOLITICS") & (cd["zone"] == "GLOBAL"))
                 | ((cd["theme"] == "TRADE_TARIFFS") & (cd["zone"] == "US"))]
    if exclude_events:
        sel = sel[~sel["event_key"].isin(exclude_events)]
    sel = sel[sel["eligible"].fillna(False).astype(bool)].drop_duplicates(["contract_id", "day"])
    return sel.merge(ch, on=["contract_id", "day"], how="inner")


def min_events_filter(rows: pd.DataFrame, n_min: int) -> pd.DataFrame:
    """D31 robustness (after D29): keep only the days on which at least `n_min` distinct events
    have eligible contracts; other days contribute nothing to the index, the escalation
    measure or the shock test."""
    n_ev = rows.groupby("day")["event_key"].nunique()
    return rows[rows["day"].isin(n_ev[n_ev >= n_min].index)]


def oil_contribution(rows: pd.DataFrame, days: pd.DatetimeIndex) -> pd.Series:
    """Part of the aggregated change d(t) carried by oil-relevant contracts (Middle East,
    Russia-Ukraine): sum over oil rows of z x volume, divided by the day's total volume."""
    tot = rows.groupby("day")["vol7d"].sum()
    oil = rows[rows["oil_relevant"].fillna(False).astype(bool)]
    num = (oil["z"] * oil["vol7d"]).groupby(oil["day"]).sum()
    return (num / tot).reindex(days).fillna(0.0)


def build_signals(rows: pd.DataFrame, cfg: dict, k: float | None = None) -> pd.DataFrame:
    sm = cfg["smoothing"]
    k = sm["geo_shock_k"] if k is None else k
    days = pd.date_range(cfg["sample"]["start"], cfg["sample"]["end"], freq="D")
    out = pd.DataFrame(index=days)
    out.index.name = "day"
    out["d"] = _vw(rows, "z").reindex(days).fillna(0.0)
    out["d_early"] = _vw(rows, "z_early").reindex(days).fillna(0.0)
    out["n_contracts"] = rows.groupby("day")["contract_id"].nunique().reindex(days).fillna(0)
    out["volume_usd"] = rows.groupby("day")["vol1d"].sum().reindex(days).fillna(0.0)
    plat = {p: _vw(g, "z").reindex(days) for p, g in rows.groupby("platform")}
    pm, ka = plat.get("polymarket"), plat.get("kalshi")
    both = pm.notna() & ka.notna() if pm is not None and ka is not None else pd.Series(False, index=days)
    out["xplat_ok"] = ~both | ((pm.fillna(0) > 0) & (ka.fillna(0) > 0))

    span = cfg["theme_index"]["vol_ewma_span_days"]
    active = out["n_contracts"] > 0
    var = (out["d"].where(active) ** 2).ewm(span=span, min_periods=20).mean().shift(1).ffill()
    out["sigma"] = np.sqrt(var)
    hl = sm["geo_escalation_halflife_days"]
    burn = (out.index.dayofweek < 5).cumsum() >= sm["geo_escalation_burnin_days"]
    out["index"] = out["d"].cumsum()
    out["escalation"] = out["d"].ewm(halflife=hl).mean()
    esc = out["escalation"]
    out["escalation_z"] = ((esc - esc.expanding().mean()) / esc.expanding().std()).where(burn)
    lvl = out["index"].ewm(halflife=hl).mean()
    out["level_z_spec_misspecified"] = ((lvl - lvl.expanding().mean()) / lvl.expanding().std()).where(burn)

    thr = k * out["sigma"]
    out["shock_raw"] = out["d"] > thr
    vol_ok = out["volume_usd"] >= sm["shock_min_volume_usd"]
    early_ok = out["d_early"] > 0.5 * thr
    confirmed = np.zeros(len(out), dtype=bool)
    raw, d, t_ = out["shock_raw"].values, out["d"].values, thr.values
    eo, vo, xo = early_ok.values, vol_ok.values, out["xplat_ok"].values
    for i in range(len(out)):
        same_day = raw[i] and eo[i] and vo[i] and xo[i]
        next_day = (i > 0 and raw[i - 1] and not confirmed[i - 1]
                    and d[i - 1] + d[i] > t_[i] and vo[i - 1] and xo[i - 1])
        confirmed[i] = bool(same_day or next_day)
    out["confirmed"] = confirmed
    # Oil-driven confirmed shocks (spec 7.5, B2): oil-relevant contracts carry more than half
    # of the move (same day, or the two-day move for a shock confirmed the next day).
    if "oil_relevant" in rows:
        oc = oil_contribution(rows, days)
        same = out["shock_raw"] & (out["d"] > 0)
        share = np.where(same, oc / out["d"].where(out["d"] > 0),
                         (oc + oc.shift(1).fillna(0)) / (out["d"] + out["d"].shift(1).fillna(0)))
        out["oil_share"] = pd.Series(share, index=days).where(out["confirmed"])
        out["oil_confirmed"] = out["confirmed"] & (out["oil_share"] > 0.5)
    return out.reset_index()


def build(cfg: dict | None = None) -> pd.DataFrame:
    cfg = cfg or load_config()
    proc = rpath("processed", cfg)
    rows = composite_rows(cfg, proc)
    sig = build_signals(rows, cfg)
    sig.to_parquet(proc / "geo_signals.parquet", index=False)
    log.info("geo signals: %d raw shocks, %d confirmed; days with contracts: %d",
             sig["shock_raw"].sum(), sig["confirmed"].sum(), (sig["n_contracts"] > 0).sum())
    return sig


if __name__ == "__main__":
    build()
