"""Hourly theme indices for the exploratory intraday lead-lag study (DECISIONS D26).

Cells: US MONETARY, US FISCAL_POLITICAL, GLOBAL GEOPOLITICS. A contract contributes on the
calendar days when it is eligible (same inclusion rules as the daily index). Its hourly value
is the last trade of each UTC hour (labelled by the END of the hour, like the FX candles), forward-filled within the day (binaries in probability or
implied hazard rate, D18; partitions as expected value over buckets). The hourly change is
signed, scaled by the contract's latest daily volatility divided by sqrt(24), winsorised at
+/- 5 and aggregated with the trailing 7-day volume weights.

Output: data/processed/hourly_index.parquet with columns hour (UTC), zone, theme, d, n_contracts
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.common import connect, get_logger, kpath, load_config, rpath, sql_path

log = get_logger("hourly")
CELLS = [("US", "MONETARY"), ("US", "FISCAL_POLITICAL"), ("GLOBAL", "GEOPOLITICS")]
ARCHIVE_CUTOFF_UTC = "2026-07-21 16:00:00+00"


def build(cfg: dict | None = None) -> pd.DataFrame:
    cfg = cfg or load_config()
    proc = rpath("processed", cfg)
    wins = cfg["theme_index"]["winsor_sd"]
    floor = cfg["pm_inclusion"]["min_days_to_resolution"]
    con = connect()
    cd = pd.read_parquet(proc / "contract_days.parquet",
                         columns=["contract_id", "platform", "event_key", "theme", "zone", "unit", "sign",
                                  "day", "eligible", "vol7d", "ttr_days"])
    cd = cd[cd["eligible"] & cd.set_index(["zone", "theme"]).index.isin(CELLS)].copy()
    cd["day"] = pd.to_datetime(cd["day"]).astype("datetime64[ns]")
    ch = pd.read_parquet(proc / "contract_changes.parquet", columns=["contract_id", "day", "sd"])
    ch["day"] = pd.to_datetime(ch["day"]).astype("datetime64[ns]")
    cd = pd.merge_asof(cd.sort_values("day"), ch.sort_values("day"), on="day", by="contract_id")
    lab = pd.read_parquet(proc / "contracts_classified.parquet",
                          columns=["platform", "platform_id", "event_key", "partition", "bucket_value"])
    lab["contract_id"] = np.where(lab["partition"], lab["platform"] + ":" + lab["event_key"] + ":EV",
                                  lab["platform"] + ":" + lab["platform_id"])
    legs = lab[lab["contract_id"].isin(cd["contract_id"].unique())]
    con.register("legs", legs[["platform", "platform_id"]].drop_duplicates())
    arch, live = kpath("pm_trades_tape", cfg), kpath("pm_trades_tape_live", cfg)
    start, end = cfg["sample"]["start"], cfg["sample"]["end"]
    parts = []
    for venue in ("polymarket", "kalshi"):
        for root, cond in ((arch, f"timestamp_ms < epoch_ms(TIMESTAMPTZ '{ARCHIVE_CUTOFF_UTC}')"),
                           (live, f"timestamp_ms >= epoch_ms(TIMESTAMPTZ '{ARCHIVE_CUTOFF_UTC}')")):
            parts.append(f"""SELECT '{venue}' AS platform, condition_id AS platform_id, timestamp_ms,
                                CASE WHEN is_yes_side THEN price ELSE 1 - price END AS px
                         FROM read_parquet('{sql_path(root)}/venue={venue}/date=*/*.parquet', hive_partitioning=true)
                         WHERE date BETWEEN DATE '{start}' AND DATE '{end}' AND {cond} AND price > 0 AND price < 1""")
    hp = con.execute(f"""
        SELECT t.platform, t.platform_id, date_trunc('hour', to_timestamp(t.timestamp_ms / 1000.0)) AS hour,
               arg_max(t.px, t.timestamp_ms) AS px
        FROM ({" UNION ALL ".join(parts)}) t SEMI JOIN legs l USING (platform, platform_id)
        GROUP BY ALL""").df()
    # Label each hourly bucket by its END time, like the FX candles: bucket [h, h+1) -> h+1.
    hp["hour"] = pd.to_datetime(hp["hour"], utc=True) + pd.Timedelta(hours=1)
    hp["day"] = hp["hour"].dt.tz_convert(None).dt.normalize().astype("datetime64[ns]")
    log.info("hourly leg prices: %d rows, %d markets", len(hp), hp["platform_id"].nunique())

    # Contract hourly values (forward-filled within each calendar day of eligibility).
    hp = hp.merge(legs[["platform", "platform_id", "contract_id", "partition", "bucket_value"]],
                  on=["platform", "platform_id"])
    rows = []
    meta = cd.set_index(["contract_id", "day"])
    for cid, g in hp.groupby("contract_id"):
        days = cd.loc[cd["contract_id"] == cid, "day"].unique()
        g = g[g["day"].isin(days)]
        if g.empty:
            continue
        if g["partition"].iloc[0]:
            piv = g.pivot_table(index="hour", columns="platform_id", values="px", aggfunc="last").sort_index()
            bv = g.drop_duplicates("platform_id").set_index("platform_id")["bucket_value"]
            piv = piv.groupby(piv.index.normalize()).ffill()
            val = (piv * bv[piv.columns]).sum(axis=1) / piv.sum(axis=1)
        else:
            val = g.set_index("hour")["px"].sort_index()
        v = val.to_frame("value")
        v["day"] = v.index.tz_convert(None).normalize().astype("datetime64[ns]")
        v["d"] = v.groupby("day")["value"].diff()
        v = v.dropna(subset=["d"]).reset_index()
        v["contract_id"] = cid
        rows.append(v)
    hv = pd.concat(rows, ignore_index=True)
    hv = hv.merge(cd[["contract_id", "day", "zone", "theme", "unit", "sign", "vol7d", "sd", "ttr_days"]],
                  on=["contract_id", "day"])
    hz = hv["unit"] == "hazard"
    if hz.any():   # hazard units for deadline contracts (D18); value above is a probability
        tau = hv.loc[hz, "ttr_days"].clip(lower=floor) / 365.25
        p1 = (hv.loc[hz, "value"] - hv.loc[hz, "d"]).clip(0.001, 0.999)
        p2 = hv.loc[hz, "value"].clip(0.001, 0.999)
        hv.loc[hz, "d"] = (-np.log(1 - p2) + np.log(1 - p1)) / tau
    hv["z"] = (hv["sign"] * hv["d"] / (hv["sd"] / np.sqrt(24))).clip(-wins, wins)
    hv = hv[hv["z"].notna()]
    agg = (hv.assign(wz=hv["z"] * hv["vol7d"]).groupby(["zone", "theme", "hour"])
             .agg(sw=("wz", "sum"), w=("vol7d", "sum"), n_contracts=("contract_id", "nunique")).reset_index())
    agg["d"] = agg["sw"] / agg["w"]
    out = agg[["hour", "zone", "theme", "d", "n_contracts"]]
    out.to_parquet(proc / "hourly_index.parquet", index=False)
    log.info("hourly index: %s", out.groupby(["zone", "theme"]).size().to_dict())
    return out


if __name__ == "__main__":
    build()
