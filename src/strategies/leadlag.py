"""Exploratory intraday lead-lag (DECISIONS D26). Not pre-registered; reported as exploratory.

(1) FX events: the top 1% hourly absolute moves of the G10 dollar basket since 2024
    (mechanical selection). For each, the hourly changes of the US MONETARY, US FISCAL and
    GLOBAL GEOPOLITICS indices from -6h to +6h, multiplied by the sign of the dollar move,
    so a positive mean means the index moved in the same direction as the dollar
    (hawkish or fiscal news with a stronger dollar; escalation with a stronger dollar).
(2) PM events: the top 1% hourly absolute changes of each PM index. For each, the hourly
    dollar-basket returns from -6h to +6h, multiplied by the sign of the PM move.
Means with 95% confidence intervals (normal approximation, standard error across events).
Hour 0 is the event hour; negative hours come before it. Question: which market moves first.

Dollar basket: hourly log value of USD against the G10 basket = -mean over currencies of the
log USD price of the currency (Dukascopy hourly, candle end time).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.common import get_logger, load_config, rpath
from src.strategies.weekend_test import load_intraday

log = get_logger("leadlag")
CELLS = [("US", "MONETARY"), ("US", "FISCAL_POLITICAL"), ("GLOBAL", "GEOPOLITICS")]
WINDOW = range(-6, 7)


def dollar_hourly(px: pd.DataFrame) -> pd.Series:
    g10 = [c for c in ("EUR", "JPY", "GBP", "CHF", "AUD", "NZD", "CAD", "NOK", "SEK") if c in px]
    lp = np.log(px[g10]).resample("h").last()
    ret = -lp.diff().mean(axis=1, skipna=False)          # all quotes needed for a basket return
    return ret.dropna()


def event_study(events: pd.Series, target: pd.Series, label: str) -> pd.DataFrame:
    """events: signed event moves indexed by hour; target: hourly series to look at."""
    target = target.reindex(target.index.union(events.index)).fillna(0.0)
    rows = []
    for k in WINDOW:
        vals = np.array([np.sign(m) * target.get(t + pd.Timedelta(hours=k), np.nan) for t, m in events.items()])
        vals = vals[~np.isnan(vals)]
        se = vals.std(ddof=1) / np.sqrt(len(vals)) if len(vals) > 1 else np.nan
        rows.append({"study": label, "hour": k, "mean": vals.mean() if len(vals) else np.nan,
                     "ci_low": vals.mean() - 1.96 * se, "ci_high": vals.mean() + 1.96 * se, "n_events": len(vals)})
    return pd.DataFrame(rows)


def run(cfg: dict | None = None) -> pd.DataFrame:
    cfg = cfg or load_config()
    out_dir = rpath("results", cfg) / "leadlag"
    out_dir.mkdir(parents=True, exist_ok=True)
    proc = rpath("processed", cfg)
    usd = dollar_hourly(load_intraday(cfg)).loc[cfg["sample"]["start"]:]
    hi = pd.read_parquet(proc / "hourly_index.parquet")
    hi["hour"] = pd.to_datetime(hi["hour"], utc=True)
    tables = []
    fx_events = usd[usd.abs() >= usd.abs().quantile(0.99)]
    for z, t in CELLS:
        s = hi[(hi.zone == z) & (hi.theme == t)].set_index("hour")["d"].sort_index()
        tables.append(event_study(fx_events, s, f"FX top 1% -> PM {z}/{t}"))
        pm_events = s[s.abs() >= s.abs().quantile(0.99)]
        tables.append(event_study(pm_events, usd, f"PM {z}/{t} top 1% -> FX dollar basket"))
    out = pd.concat(tables, ignore_index=True)
    out.to_csv(out_dir / "event_study.csv", index=False)
    log.info("lead-lag event studies: %d FX events; written to %s", len(fx_events), out_dir)
    return out


if __name__ == "__main__":
    run()
