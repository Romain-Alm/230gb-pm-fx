"""Continuous theme indices from contract-level changes (spec 4.5 steps 2 to 5).

For each contract (binary or partition EV), on each snapshot day t where it is eligible
and fresh (non-stale):
  1. change = value(t) - value at its previous fresh snapshot (at most 7 days earlier;
     DECISIONS D11), divided by sqrt(g) when it spans g > 1 days (D19), multiplied by the
     contract sign. Deadline markets are valued as implied hazard rates (D18, see
     `src.pm.contracts`);
  2. standardised by its own volatility: EWMA (span 60) of past squared daily-scaled changes, using
     changes strictly before t; until 5 past changes exist, a causal fallback is used
     (expanding median absolute change of all contracts with the same unit, before t,
     scaled by 1.4826);
  3. winsorised at +/- 5;
  4. aggregated within each cell with volume weights (trailing 7-day volume) or equal
     weights;
  5. the index level is the cumulative sum of the aggregated daily changes.

Cells: every (zone, theme) pair present, plus two composites used by the strategies:
  GLOBAL / GEO_OIL    geopolitics contracts tagged oil-relevant (Middle East, Russia-Ukraine)
  GLOBAL / GEO_TRADE  geopolitics (GLOBAL) and US trade-restriction contracts (spec 7.3)

Output: data/processed/theme_index.parquet with columns
  zone, theme, day, d_vw, d_ew, n_contracts, vol7d, index_vw, index_ew
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.common import get_logger, load_config, rpath

log = get_logger("indices")
MAX_GAP_DAYS = 7
MIN_OBS = 5


def contract_changes(cd: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Standardised signed changes per contract-day (one row per contract and day)."""
    span, wins = cfg["theme_index"]["vol_ewma_span_days"], cfg["theme_index"]["winsor_sd"]
    c = (cd.drop_duplicates(["contract_id", "day"])
           .loc[lambda d: ~d["stale"] & d["value"].notna()]
           .sort_values(["contract_id", "day"]).copy())
    c["day"] = pd.to_datetime(c["day"])
    g = c.groupby("contract_id", sort=False)
    c["prev_value"] = g["value"].shift(1)
    c["prev_day"] = g["day"].shift(1)
    c["gap"] = (c["day"] - c["prev_day"]).dt.days
    # Daily-scaled change (D19): a change spanning g days is divided by sqrt(g).
    c["dv"] = ((c["value"] - c["prev_value"]) / np.sqrt(c["gap"])).where(c["gap"] <= MAX_GAP_DAYS)
    c = c[c["dv"].notna()].copy()
    # Own-volatility estimate from past changes only.
    g = c.groupby("contract_id", sort=False)
    c["n_past"] = g.cumcount()
    c["var_own"] = g["dv"].transform(lambda s: (s ** 2).ewm(span=span, adjust=True).mean().shift(1))
    # Causal fallback: expanding median |dv| by unit over all contracts, strictly before day t.
    daily_med = (c.groupby(["unit", "day"])["dv"].apply(lambda s: list(s.abs())).reset_index())
    fb = []
    for unit, d in daily_med.groupby("unit"):
        d = d.sort_values("day")
        acc, vals = [], []
        for lst in d["dv"]:
            vals.append(np.median(acc) * 1.4826 if acc else np.nan)
            acc.extend(lst)
        fb.append(pd.DataFrame({"unit": unit, "day": d["day"].values, "sd_fallback": vals}))
    c = c.merge(pd.concat(fb), on=["unit", "day"], how="left")
    sd = np.sqrt(c["var_own"])
    c["sd"] = np.where((c["n_past"] >= MIN_OBS) & (sd > 0), sd, c["sd_fallback"])
    c["z"] = (c["sign"] * c["dv"] / c["sd"]).clip(-wins, wins)
    # Same change measured with the price at least `shock_persist_hours` before the snapshot.
    if "value_early" in c:
        c["z_early"] = (c["sign"] * (c["value_early"] - c["prev_value"]) / np.sqrt(c["gap"])
                        / c["sd"]).clip(-wins, wins)
    else:
        c["z_early"] = np.nan
    return c[["contract_id", "day", "z", "z_early", "dv", "sd", "value", "unit", "sign"]]


def aggregate(rows: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
    rows = rows[rows["eligible"] & rows["z"].notna()]
    rows = rows.assign(wz=rows["z"] * rows["vol7d"])
    a = rows.groupby(keys + ["day"]).agg(sum_wz=("wz", "sum"), vol7d=("vol7d", "sum"),
                                         d_ew=("z", "mean"), n_contracts=("contract_id", "nunique"))
    a["d_vw"] = a["sum_wz"] / a["vol7d"]
    return a.drop(columns="sum_wz").reset_index()


def load_rows(cfg: dict, panel_file: str = "contract_days.parquet") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Contract-day rows with their standardised change, and the change table."""
    proc = rpath("processed", cfg)
    cd = pd.read_parquet(proc / panel_file)
    cd["day"] = pd.to_datetime(cd["day"])
    ch = contract_changes(cd, cfg)
    rows = cd.merge(ch[["contract_id", "day", "z"]], on=["contract_id", "day"], how="inner")
    return rows, ch


def dense_index(rows: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Aggregate rows into the (zone, theme) cells plus the GEO_OIL and GEO_TRADE composites,
    on a dense daily calendar (zero change on days without contributions)."""
    base = aggregate(rows, ["zone", "theme"])
    geo = rows[(rows["theme"] == "GEOPOLITICS") & (rows["zone"] == "GLOBAL")]
    oil = aggregate(geo[geo["oil_relevant"].fillna(False)].assign(zone="GLOBAL", theme="GEO_OIL"),
                    ["zone", "theme"])
    trade_us = rows[(rows["theme"] == "TRADE_TARIFFS") & (rows["zone"] == "US")]
    comp = pd.concat([geo, trade_us]).drop_duplicates(["contract_id", "day"])
    geotrade = aggregate(comp.assign(zone="GLOBAL", theme="GEO_TRADE"), ["zone", "theme"])
    out = pd.concat([base, oil, geotrade], ignore_index=True)
    days = pd.date_range(cfg["sample"]["start"], cfg["sample"]["end"], freq="D")
    dense = []
    for (z, t), g in out.groupby(["zone", "theme"]):
        g = g.set_index("day").reindex(days)
        g.index.name = "day"
        g[["zone", "theme"]] = z, t
        g[["d_vw", "d_ew"]] = g[["d_vw", "d_ew"]].fillna(0.0)
        g[["n_contracts", "vol7d"]] = g[["n_contracts", "vol7d"]].fillna(0)
        g["index_vw"] = g["d_vw"].cumsum()
        g["index_ew"] = g["d_ew"].cumsum()
        dense.append(g.reset_index())
    return pd.concat(dense, ignore_index=True)


def build(cfg: dict | None = None, panel_file: str = "contract_days.parquet",
          out_file: str = "theme_index.parquet") -> pd.DataFrame:
    cfg = cfg or load_config()
    proc = rpath("processed", cfg)
    rows, ch = load_rows(cfg, panel_file)
    log.info("contract-days with a standardised change: %d", len(rows))
    idx = dense_index(rows, cfg)
    idx.to_parquet(proc / out_file, index=False)
    ch.to_parquet(proc / out_file.replace("theme_index", "contract_changes"), index=False)
    summary = idx.groupby(["zone", "theme"]).agg(days_active=("n_contracts", lambda s: (s > 0).sum()),
                                                 mean_n=("n_contracts", "mean"))
    log.info("theme indices written (%d cells):\n%s", len(summary),
             summary.sort_values("days_active", ascending=False).head(30).to_string())
    return idx


if __name__ == "__main__":
    build()
