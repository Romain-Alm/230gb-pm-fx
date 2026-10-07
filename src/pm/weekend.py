"""Weekend theme-index changes while FX is closed (spec 6.6).

For every weekend in the sample (no selection), and for every contract eligible at the
Friday snapshot, the contract value is taken at
  T1 = Friday 17:00 New York (FX close)  and  T2 = Sunday 17:00 New York (FX reopening),
as the last trade strictly before each time (forward-filled from the Friday snapshot
when there is no trade in between). The signed change is standardised by the contract's
own volatility known at the Friday snapshot and aggregated by cell exactly as the daily
indices (volume weights = Friday trailing 7-day volume).

Output: data/processed/weekend_changes.parquet with columns
  friday, zone, theme, d_vw, d_ew, n_contracts, n_moved
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.common import connect, get_logger, kpath, load_config, rpath, sql_path

log = get_logger("weekend")
ARCHIVE_CUTOFF_UTC = "2026-07-21 16:00:00+00"


def _trades_sql(cfg) -> str:
    arch, live = kpath("pm_trades_tape", cfg), kpath("pm_trades_tape_live", cfg)
    start, end = cfg["sample"]["start"], cfg["sample"]["end"]
    parts = []
    for venue in ("polymarket", "kalshi"):
        for root, cond in ((arch, f"timestamp_ms < epoch_ms(TIMESTAMPTZ '{ARCHIVE_CUTOFF_UTC}')"),
                           (live, f"timestamp_ms >= epoch_ms(TIMESTAMPTZ '{ARCHIVE_CUTOFF_UTC}')")):
            parts.append(f"""
                SELECT '{venue}' AS platform, condition_id AS platform_id, timestamp_ms,
                       CASE WHEN is_yes_side THEN price ELSE 1 - price END AS px
                FROM read_parquet('{sql_path(root)}/venue={venue}/date=*/*.parquet', hive_partitioning=true)
                WHERE dayofweek(date) IN (5, 6, 0, 1) AND date BETWEEN DATE '{start}' AND DATE '{end}'
                  AND {cond} AND price > 0 AND price < 1""")
    return " UNION ALL ".join(parts)


def build(cfg: dict | None = None, panel_file: str = "contract_days.parquet",
          out_file: str = "weekend_changes.parquet") -> pd.DataFrame:
    cfg = cfg or load_config()
    proc = rpath("processed", cfg)
    wins = cfg["theme_index"]["winsor_sd"]
    con = connect()
    lab = sql_path(proc / "contracts_classified.parquet")
    cd = sql_path(proc / panel_file)
    ch = sql_path(proc / panel_file.replace("contract_days", "contract_changes"))
    if not (proc / panel_file.replace("contract_days", "contract_changes")).exists():
        ch = sql_path(proc / "contract_changes.parquet")

    # Contracts eligible at each Friday snapshot, with their latest volatility estimate.
    con.execute(f"""
    CREATE TABLE fri AS
    SELECT c.contract_id, c.platform, c.event_key, c.theme, c.zone, c.oil_relevant, c.sign,
           c.unit, c.day AS friday, c.vol7d, c.ttr_days, x.sd
    FROM read_parquet('{cd}') c
    ASOF LEFT JOIN (SELECT contract_id, day, sd FROM read_parquet('{ch}')) x
      ON x.contract_id = c.contract_id AND x.day <= c.day
    WHERE c.eligible AND dayofweek(c.day) = 5
    """)
    # Market legs of each contract (one leg for binaries, all buckets for partitions).
    con.execute(f"""
    CREATE TABLE legs AS
    SELECT platform, platform_id, CASE WHEN partition THEN platform || ':' || event_key || ':EV'
                                      ELSE platform || ':' || platform_id END AS contract_id,
           coalesce(bucket_value, 1.0) AS bucket_value, partition
    FROM read_parquet('{lab}')
    WHERE (platform || ':' || platform_id) IN (SELECT contract_id FROM fri)
       OR (platform || ':' || event_key || ':EV') IN (SELECT contract_id FROM fri)
    """)
    con.execute(f"""
    CREATE TABLE tr AS
    SELECT t.* FROM ({_trades_sql(cfg)}) t
    SEMI JOIN legs l ON l.platform = t.platform AND l.platform_id = t.platform_id
    """)
    con.execute(f"""
    CREATE TABLE lw AS
    WITH tm AS (
        SELECT DISTINCT friday,
               epoch_ms(timezone('America/New_York', CAST(friday AS DATE) + TIME '17:00:00')) AS t1,
               epoch_ms(timezone('America/New_York', CAST(friday + 2 AS DATE) + TIME '17:00:00')) AS t2
        FROM fri
    )
    SELECT DISTINCT l.platform, l.platform_id, l.contract_id, l.bucket_value, l.partition,
           tm.friday, tm.t1, tm.t2
    FROM legs l JOIN fri f ON f.contract_id = l.contract_id JOIN tm ON tm.friday = f.friday
    """)
    # Leg prices: Friday snapshot (daily panel), last trade before T1, last trade before T2.
    con.execute(f"""
    CREATE TABLE px AS
    SELECT lw.*, d.px_last AS px_fri, a.px AS px_a1, a.timestamp_ms AS ts_a1,
           b.px AS px_b2, b.timestamp_ms AS ts_b2
    FROM lw
    ASOF LEFT JOIN (SELECT platform, platform_id, snap_date, px_last
                    FROM read_parquet('{sql_path(proc / "pm_daily.parquet")}')) d
      ON d.platform = lw.platform AND d.platform_id = lw.platform_id AND d.snap_date <= lw.friday
    ASOF LEFT JOIN tr a
      ON a.platform = lw.platform AND a.platform_id = lw.platform_id AND a.timestamp_ms < lw.t1
    ASOF LEFT JOIN tr b
      ON b.platform = lw.platform AND b.platform_id = lw.platform_id AND b.timestamp_ms < lw.t2
    """)
    con.execute("""
    CREATE OR REPLACE TABLE px AS
    SELECT *,
           CASE WHEN ts_a1 >= t1 - 86400000 THEN px_a1 ELSE px_fri END AS px_t1,
           CASE WHEN ts_b2 >= t1 THEN px_b2 END AS px_wk
    FROM px
    """)
    con.execute("""
    CREATE TABLE val AS
    SELECT contract_id, friday,
           sum(px_t1 * bucket_value) / nullif(sum(px_t1), 0) AS v1_part,
           sum(coalesce(px_wk, px_t1) * bucket_value) / nullif(sum(coalesce(px_wk, px_t1)), 0) AS v2_part,
           any_value(px_t1) AS v1_bin, any_value(coalesce(px_wk, px_t1)) AS v2_bin,
           bool_or(px_wk IS NOT NULL) AS moved, any_value(partition) AS partition
    FROM px GROUP BY 1, 2
    """)
    rows = con.execute(f"""
        SELECT f.*, v.partition, v1_part, v2_part, v1_bin, v2_bin, v.moved
        FROM fri f JOIN val v USING (contract_id, friday)
    """).df()
    # Same units as the daily contract values (D18): deadline contracts as implied hazard
    # rates, with the time to deadline at Friday 17:00 and Sunday 17:00 New York.
    floor = cfg["pm_inclusion"]["min_days_to_resolution"]
    hz = rows["unit"] == "hazard"
    tau1 = rows["ttr_days"].clip(lower=floor) / 365.25
    tau2 = (rows["ttr_days"] - 2).clip(lower=floor) / 365.25
    lam = lambda p, tau: -np.log(1 - p.clip(0.001, 0.999)) / tau
    v1 = np.where(rows["partition"], rows["v1_part"], np.where(hz, lam(rows["v1_bin"], tau1), rows["v1_bin"]))
    v2 = np.where(rows["partition"], rows["v2_part"], np.where(hz, lam(rows["v2_bin"], tau2), rows["v2_bin"]))
    rows["dv"] = v2 - v1
    rows["z"] = (rows["sign"] * rows["dv"] / rows["sd"]).clip(-wins, wins)
    rows = rows[rows["z"].notna()]

    def agg(df, zone, theme):
        g = df.assign(wz=df["z"] * df["vol7d"]).groupby("friday")
        return pd.DataFrame({"zone": zone, "theme": theme,
                             "d_vw": g["wz"].sum() / g["vol7d"].sum(), "d_ew": g["z"].mean(),
                             "n_contracts": g["contract_id"].nunique(),
                             "n_moved": g["moved"].sum()}).reset_index()

    parts = [agg(g, z, t) for (z, t), g in rows.groupby(["zone", "theme"])]
    geo = rows[(rows["theme"] == "GEOPOLITICS") & (rows["zone"] == "GLOBAL")]
    parts.append(agg(geo[geo["oil_relevant"].fillna(False)], "GLOBAL", "GEO_OIL"))
    comp = pd.concat([geo, rows[(rows["theme"] == "TRADE_TARIFFS") & (rows["zone"] == "US")]])
    parts.append(agg(comp.drop_duplicates(["contract_id", "friday"]), "GLOBAL", "GEO_TRADE"))
    out = pd.concat(parts, ignore_index=True)
    out.to_parquet(proc / out_file, index=False)
    log.info("weekend changes: %d weekends, %d cell-weekends", out["friday"].nunique(), len(out))
    return out


if __name__ == "__main__":
    build()
