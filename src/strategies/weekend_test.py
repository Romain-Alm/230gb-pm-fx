"""Weekend gap test (spec 6.6): FX is closed, prediction markets are not.

Sample: every weekend since 2024 (no hand-picked list).
Signal: weekend change of each theme cell between Friday 17:00 and Sunday 17:00 New York
(`src/pm/weekend.py`), mapped to pairs with the same theory signs and spillovers as
Strategy A (A1 cells by default).
Target: FX gap from the Friday 17:00 New York close to the first liquid price after the
reopening, Monday 07:00 London (robustness: Sunday 18:00 New York), as the log change of
the USD price of the currency.
Regression: pooled across pairs with pair fixed effects and Driscoll-Kraay errors.
Optional trading version: position at the reopening on the weekend signal, closed at the
Monday 16:00 London snapshot (tests continuation after the reopening).

Intraday input: hourly mid quotes in `data/raw/intraday/*.parquet` (config paths.raw_intraday) with columns
timestamp (UTC), ccy (G10 code), mid (USD price of the currency, already inverted).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.common import get_logger, load_config, rpath
from src.strategies import diagnostics as D
from src.strategies import strategy_a as A

log = get_logger("weekend_test")


def load_intraday(cfg: dict) -> pd.DataFrame:
    files = sorted(rpath("raw_intraday", cfg).glob("*.parquet"))
    if not files:
        raise FileNotFoundError("no intraday FX in data/raw/intraday (see progress/DATA_REQUEST.md)")
    df = pd.concat(pd.read_parquet(f) for f in files)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return df.pivot_table(index="timestamp", columns="ccy", values="mid").sort_index()


def _price_at(px: pd.DataFrame, ts: pd.Timestamp, before: bool) -> pd.Series:
    """Last quote at or before ts (before=True) or first quote at or after ts."""
    if before:
        s = px.loc[:ts]
        return s.iloc[-1] if len(s) else pd.Series(np.nan, index=px.columns)
    s = px.loc[ts:]
    return s.iloc[0] if len(s) else pd.Series(np.nan, index=px.columns)


def gaps(px: pd.DataFrame, fridays: pd.DatetimeIndex, reopen: str = "london") -> pd.DataFrame:
    out = {}
    for f in fridays:
        t_close = pd.Timestamp(f.date()).tz_localize("America/New_York") + pd.Timedelta(hours=17)
        if reopen == "london":
            t_open = (pd.Timestamp((f + pd.Timedelta(days=3)).date()).tz_localize("Europe/London")
                      + pd.Timedelta(hours=7))
        else:
            t_open = (pd.Timestamp((f + pd.Timedelta(days=2)).date()).tz_localize("America/New_York")
                      + pd.Timedelta(hours=18))
        a = _price_at(px, t_close.tz_convert("UTC"), before=True)
        b = _price_at(px, t_open.tz_convert("UTC"), before=False)
        out[f] = np.log(b) - np.log(a)
    return pd.DataFrame(out).T


def daily_window_gaps(spot: pd.DataFrame, fridays: pd.DatetimeIndex) -> pd.DataFrame:
    """Fallback without intraday data: log change of the daily fix from Friday to the next
    Monday (e.g. FRED H.10 noon New York). The window contains the weekend plus Friday
    afternoon and Monday morning, so it is noisier than the hourly gap."""
    out = {}
    for f in fridays:
        mon = f + pd.Timedelta(days=3)
        if f in spot.index and mon in spot.index:
            out[f] = np.log(spot.loc[mon]) - np.log(spot.loc[f])
    return pd.DataFrame(out).T


def weekend_components(wk: pd.DataFrame, fridays: pd.DatetimeIndex, cells: set) -> dict:
    """Pair components from weekend cell changes (same signs as Strategy A; the fiscal
    sign uses the monetary-dominance baseline because the regime is a daily object)."""
    sig = {(z, t): g.set_index("friday")["d_vw"].reindex(fridays).fillna(0.0)
           for (z, t), g in wk.groupby(["zone", "theme"])}
    comps = A.pair_components(sig, fridays, cells, regime=None)
    return {k: v for k, v in comps.items() if not k.startswith("_")}


def run(cfg: dict | None = None) -> pd.DataFrame:
    cfg = cfg or load_config()
    proc = rpath("processed", cfg)
    out_dir = rpath("results", cfg) / "weekend"
    out_dir.mkdir(parents=True, exist_ok=True)
    wk = pd.read_parquet(proc / "weekend_changes.parquet")
    wk["friday"] = pd.to_datetime(wk["friday"])
    fridays = pd.DatetimeIndex(sorted(wk["friday"].unique()))
    try:
        px = load_intraday(cfg)
        targets = {"london": lambda: gaps(px, fridays, "london"), "ny": lambda: gaps(px, fridays, "ny")}
    except FileNotFoundError:
        from src.data import market
        raw, mp = market.read_raw(cfg), market.series_map(cfg)
        spot = market.fx_panel(raw, mp, list(A.PAIRS), pd.bdate_range("2023-12-01", cfg["sample"]["end"])).spot
        spot = spot.where(~market.fx_panel(raw, mp, list(A.PAIRS), spot.index).stale)
        targets = {"daily_window_NOT_A_GAP_TEST": lambda: daily_window_gaps(spot, fridays)}
        log.warning("no intraday FX: weekend test uses the Friday-to-Monday daily window")
    cov = pd.read_csv(rpath("results", cfg) / "coverage_cells.csv")
    kept = set(zip(cov.loc[cov["keep"], "zone"], cov.loc[cov["keep"], "theme"]))
    tables = []
    available = set(zip(wk["zone"], wk["theme"]))
    # D24 (pre-registered): A1 cells plus GLOBAL GEOPOLITICS on its pre-specified spillover
    # currencies (JPY, CHF). The other variants are reported for completeness.
    variants = {"A1+GEO": A.variant_cells("A1", available, kept) | ({("GLOBAL", "GEOPOLITICS")} & available)}
    variants.update({v: A.variant_cells(v, available, kept) for v in ("A1", "A1+S", "A2", "A2+S")})
    for variant, cells in variants.items():
        comps = weekend_components(wk, fridays, cells)
        comps = {k: v for k, v in comps.items() if v.abs().to_numpy().sum() > 0}
        for reopen, make in targets.items():
            g = make().reindex(columns=list(A.PAIRS))
            frames = []
            for p in A.PAIRS:
                d = pd.DataFrame({"y": g[p]})
                for k, v in comps.items():
                    d[k] = v[p]
                d["pair"] = p
                frames.append(d)
            df = pd.concat(frames).dropna()
            df.index.name = "date"
            df = df.reset_index().set_index(["pair", "date"])
            res = D.pooled(df, list(comps))
            tables.append(D.coef_table(res, 0, f"{variant}_weekend_gap_{reopen}"))
    out = pd.concat(tables)
    out.to_csv(out_dir / "weekend_gap_regressions.csv", index=False)
    log.info("weekend gap regressions:\n%s", out[["model", "regressor", "coef", "t", "n_obs"]])
    return out


if __name__ == "__main__":
    run()
