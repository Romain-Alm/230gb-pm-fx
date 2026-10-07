"""Market data: FX spot and 1-month forwards/NDFs, 10-year yields, risk series.

The raw export (Bloomberg or Refinitiv) is mapped to internal series through
`config/market_series.yaml`, so the format of the export only matters in one place.
Every input file in `data/raw/market/` is read into one long table
`date, ticker, field, value`; each internal series names its ticker, field and quoting
convention.

Conventions after standardisation (all at the common snapshot, see config):
  spot[c], fwd[c]   USD price of one unit of currency c (USDJPY etc. are inverted)
  s, f              logs of the above
  carry[c]          (s - f) x 12, annualised forward-implied carry of a long position in c
  rx[c] (row t+1)   s(t+1) - s(t) + carry(t) / 252, daily excess return of a long 1-month
                    forward position in c (spec 6.4)
  half_spread[c]    (ask - bid) / (2 mid) of the forward (spot if no forward quotes); a causal
                    rolling median (`costs.half_spread_median_days`) removes crossed, locked and
                    one-day wide indicative quotes
QC: observations carrying a flag listed in `market_qc.blank_flags` (file `paths.raw_market_qc`) are
removed before use; nothing is filled from another source (DECISIONS D28).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import yaml

from src.common import ROOT, get_logger, load_config, rpath

log = get_logger("market")
PPY = 252


def read_raw(cfg: dict | None = None) -> pd.DataFrame:
    """Concatenate every CSV/Parquet in data/raw/market into date, ticker, field, value."""
    cfg = cfg or load_config()
    raw_dir = rpath("raw_market", cfg)
    frames = []
    for p in sorted(raw_dir.glob("*")):
        if p.suffix.lower() == ".csv":
            frames.append(pd.read_csv(p))
        elif p.suffix.lower() == ".parquet":
            frames.append(pd.read_parquet(p))
    if not frames:
        raise FileNotFoundError(f"no market data in {raw_dir}; see progress/DATA_REQUEST.md")
    df = pd.concat(frames, ignore_index=True)
    df.columns = [c.lower() for c in df.columns]
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df = df[["date", "ticker", "field", "value"]].dropna(subset=["value"])
    return _blank_flagged(df, cfg)


def _blank_flagged(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """Drop every field of a (date, ticker) carrying a QC flag selected in the config."""
    qc = cfg.get("market_qc", {})
    rel = cfg["paths"].get("raw_market_qc")
    if not rel or not qc.get("blank_flags") or not (ROOT / rel).exists():
        return df
    q = pd.read_csv(ROOT / rel)
    q = q[q["flag"].isin(qc["blank_flags"]) & ~q["ticker"].isin(qc.get("keep_tickers", []))]
    q["date"] = pd.to_datetime(q["date"]).dt.normalize()
    key = pd.MultiIndex.from_frame(q[["date", "ticker"]].drop_duplicates())
    drop = pd.MultiIndex.from_frame(df[["date", "ticker"]]).isin(key)
    log.info("QC: %d values removed (%d flagged date-ticker pairs)", int(drop.sum()), len(key))
    return df[~drop]


def series_map(cfg: dict | None = None, path=None) -> dict:
    """Raw-data mapping; `paths.market_series` in the config selects the file (default
    config/market_series.yaml, the Bloomberg mapping)."""
    rel = (cfg or {}).get("paths", {}).get("market_series", "config/market_series.yaml")
    with open(path or ROOT / rel, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _pick(raw: pd.DataFrame, ticker: str, field: str) -> pd.Series:
    s = raw[(raw["ticker"] == ticker) & (raw["field"] == field)].set_index("date")["value"]
    return s[~s.index.duplicated(keep="last")].sort_index().astype(float)


@dataclass
class FXPanel:
    spot: pd.DataFrame
    fwd: pd.DataFrame
    carry: pd.DataFrame
    rx: pd.DataFrame
    half_spread: pd.DataFrame
    stale: pd.DataFrame


def fx_panel(raw: pd.DataFrame, mapping: dict, ccys: list[str], days: pd.DatetimeIndex,
             spread_median_days: int = 1) -> FXPanel:
    """Build the standardised FX panel for currencies `ccys` on trading days `days`."""
    spot, fwd, hs = {}, {}, {}
    dflt = {"spot_field": "PX_LAST", "bid_field": "PX_BID", "ask_field": "PX_ASK", **mapping.get("defaults", {})}
    for c in ccys:
        m = {**dflt, **mapping["fx"][c]}
        inv = bool(m.get("invert", False))
        sp = _pick(raw, m["spot"], m.get("mid_field", m["spot_field"]))
        bid_t = m.get("fwd_outright", m["spot"])
        bid, ask = _pick(raw, bid_t, m["bid_field"]), _pick(raw, bid_t, m["ask_field"])
        if "fwd_outright" in m:
            fw = _pick(raw, m["fwd_outright"], m.get("mid_field", m["spot_field"]))
            if fw.empty:                        # outrights delivered as bid/ask only
                fw = ((bid + ask) / 2).dropna()
        else:
            pts = _pick(raw, m["fwd_points"], m.get("mid_field", m["spot_field"])) / float(m["points_scale"])
            fw = sp.reindex(pts.index) + pts
        if m.get("fwd_valid_from"):
            fw = fw.loc[m["fwd_valid_from"]:]
            bid, ask = bid.loc[m["fwd_valid_from"]:], ask.loc[m["fwd_valid_from"]:]
        if inv:
            sp, fw = 1.0 / sp, 1.0 / fw
        spot[c], fwd[c] = sp, fw
        mid = (bid + ask) / 2
        hs[c] = ((ask - bid) / (2 * mid)).abs()
    spot = pd.DataFrame(spot).reindex(days)
    fwd = pd.DataFrame(fwd).reindex(days)
    stale = spot.isna()
    spot, fwd = spot.ffill(), fwd.ffill()
    s, f = np.log(spot), np.log(fwd)
    carry = (s - f) * 12.0
    rx = s.diff() + carry.shift(1) / PPY
    rx[stale] = np.nan          # no return formed from a stale value (spec 3)
    half_spread = pd.DataFrame(hs)
    if spread_median_days > 1:
        half_spread = half_spread.rolling(spread_median_days, min_periods=1).median()
    half_spread = half_spread.reindex(days).ffill()
    return FXPanel(spot, fwd, carry, rx, half_spread, stale)


def exec_lags(mapping: dict, ccys: list[str]) -> dict[str, int]:
    """Trading days between the 16:00 London signal snapshot and the first usable close:
    0 for closes after the snapshot (New York close), 1 for closes before it (Asian hours)."""
    return {c: int(mapping["fx"][c].get("close", "ny") == "asia") for c in ccys}


def simple_series(raw: pd.DataFrame, mapping: dict, block: str, days: pd.DatetimeIndex) -> pd.DataFrame:
    out = {k: _pick(raw, v["ticker"], v.get("field", "PX_LAST")) for k, v in mapping[block].items()}
    return pd.DataFrame(out).reindex(days).ffill()


def trading_days(cfg: dict | None = None, start: str | None = None) -> pd.DatetimeIndex:
    cfg = cfg or load_config()
    return pd.bdate_range(start or cfg["sample"]["start"], cfg["sample"]["end"])
