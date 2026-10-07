"""Daily prediction-market price panel at the common 16:00 London snapshot.

Each trade is assigned to the first snapshot strictly after it: a trade at London
local time < 16:00 belongs to that day's snapshot, otherwise to the next day's.
DST is handled by converting every trade to Europe/London local time.

Per (market, snapshot day) we keep the last Yes price, the volume-weighted Yes price
over the last hour before the snapshot, the last trade time, USD volume and trade
count, plus the last Yes price at least `shock_persist_hours` before the snapshot
(`px_early`, used by the false-shock filter) and the volume traded after that time. The panel is sparse (days with trades only); forward-filling and staleness
are applied by the index builder using `last_ts`.

Sources (read-only): the frozen trades tape up to the archive cutoff and the live
tape after it, so no trade is counted twice.

Output: data/processed/pm_daily.parquet
"""
from __future__ import annotations

from src.common import connect, get_logger, kpath, load_config, rpath, sql_path

log = get_logger("pm_panel")

# Frozen archive fills end at 2026-07-21T16:04Z; the live tape takes over after this.
ARCHIVE_CUTOFF_UTC = "2026-07-21 16:00:00+00"


def build(cfg: dict | None = None, market_file: str = "pm_markets.parquet",
          out_file: str = "pm_daily.parquet") -> None:
    cfg = cfg or load_config()
    proc = rpath("processed", cfg)
    tz, snap = cfg["snapshot"]["timezone"], cfg["snapshot"]["time"]
    persist_h = int(cfg["smoothing"]["shock_persist_hours"])
    start, end = cfg["sample"]["start"], cfg["sample"]["end"]
    con = connect()

    con.execute(f"""CREATE TABLE ids AS SELECT DISTINCT platform, platform_id
                    FROM read_parquet('{sql_path(proc / market_file)}')""")
    log.info("markets requested: %s", con.execute("SELECT platform, count(*) FROM ids GROUP BY 1").fetchall())

    arch, live = kpath("pm_trades_tape", cfg), kpath("pm_trades_tape_live", cfg)
    parts = []
    for venue in ("polymarket", "kalshi"):
        parts.append(f"""
            SELECT '{venue}' AS platform, condition_id, price, size, is_yes_side, timestamp_ms
            FROM read_parquet('{sql_path(arch)}/venue={venue}/date=*/*.parquet', hive_partitioning=true)
            WHERE date BETWEEN DATE '{start}' - INTERVAL 1 DAY AND DATE '2026-07-21'
              AND timestamp_ms < epoch_ms(TIMESTAMPTZ '{ARCHIVE_CUTOFF_UTC}')""")
        parts.append(f"""
            SELECT '{venue}' AS platform, condition_id, price, size, is_yes_side, timestamp_ms
            FROM read_parquet('{sql_path(live)}/venue={venue}/date=*/*.parquet', hive_partitioning=true)
            WHERE date BETWEEN DATE '2026-07-21' AND DATE '{end}'
              AND timestamp_ms >= epoch_ms(TIMESTAMPTZ '{ARCHIVE_CUTOFF_UTC}')""")
    trades = " UNION ALL ".join(parts)

    out = proc / out_file
    con.execute(f"""
    COPY (
        WITH t AS (
            SELECT tr.platform, tr.condition_id AS platform_id, tr.timestamp_ms,
                   CASE WHEN tr.is_yes_side THEN tr.price ELSE 1 - tr.price END AS px_yes,
                   abs(tr.price * tr.size) AS usd,
                   timezone('{tz}', to_timestamp(tr.timestamp_ms / 1000.0)) AS local_ts
            FROM ({trades}) tr
            SEMI JOIN ids ON tr.platform = ids.platform AND tr.condition_id = ids.platform_id
            WHERE tr.price > 0 AND tr.price < 1
        ), s AS (
            SELECT *,
                   CASE WHEN CAST(local_ts AS TIME) < TIME '{snap}:00'
                        THEN CAST(local_ts AS DATE)
                        ELSE CAST(local_ts AS DATE) + 1 END AS snap_date,
                   CAST(local_ts AS TIME) >= TIME '{snap}:00' - INTERVAL 1 HOUR
                     AND CAST(local_ts AS TIME) < TIME '{snap}:00' AS last_hour
            FROM t
        ), s2 AS (
            -- 'early' trades are at least `persist_h` hours before the snapshot (shock filter)
            SELECT *, NOT (CAST(local_ts AS DATE) = snap_date
                           AND CAST(local_ts AS TIME) >= TIME '{snap}:00' - INTERVAL {persist_h} HOUR) AS early
            FROM s
        )
        SELECT platform, platform_id, snap_date,
               arg_max(px_yes, timestamp_ms) AS px_last,
               sum(px_yes * usd) FILTER (WHERE last_hour) / nullif(sum(usd) FILTER (WHERE last_hour), 0) AS px_vwap_1h,
               to_timestamp(max(timestamp_ms) / 1000.0) AS last_ts,
               arg_max(px_yes, timestamp_ms) FILTER (WHERE early) AS px_early,
               to_timestamp(max(timestamp_ms) FILTER (WHERE early) / 1000.0) AS early_ts,
               sum(usd) AS volume_usd,
               sum(usd) FILTER (WHERE NOT early) AS volume_late_usd,
               count(*) AS n_trades
        FROM s2
        WHERE snap_date BETWEEN DATE '{start}' AND DATE '{end}'
        GROUP BY ALL
        ORDER BY platform, platform_id, snap_date
    ) TO '{sql_path(out)}' (FORMAT PARQUET, COMPRESSION ZSTD)
    """)
    stats = con.execute(f"""SELECT platform, count(*) n_rows, count(DISTINCT platform_id) n_markets,
                                   min(snap_date), max(snap_date), round(sum(volume_usd)/1e9, 2) usd_bn
                            FROM read_parquet('{sql_path(out)}') GROUP BY 1""").fetchall()
    log.info("daily panel written to %s: %s", out, stats)


if __name__ == "__main__":
    build()
