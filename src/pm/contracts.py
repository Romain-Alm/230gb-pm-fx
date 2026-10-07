"""Dense contract-day panel with the ex-ante inclusion rules (spec 4.1) and common units.

A "contract" is either
  - a signed binary market (direction +1 / -1), value = Yes probability, or
  - a partition event (mutually exclusive buckets), value = implied expected value in
    the event unit (bp for policy decisions / cut counts / rate levels, pp for inflation,
    pct for tariff rates), computed from the buckets' latest prices renormalised to one.
    Its sign is +1: bucket values are already oriented (spec 4.4 / 4.5 step 1).

For every contract and every calendar day of its life inside the sample we record the
value known at the 16:00 London snapshot (last trade strictly before it), the time of
that trade, staleness (no trade for more than `stale_hours`), trailing 7-day USD
volume (snapshot days t-6..t, i.e. only past trades), days to scheduled close, and the
eligibility flag. Every input is observable before the snapshot of day t: market
creation and scheduled close times are set at listing, prices and volumes come from
trades strictly before the snapshot.

Output: data/processed/contract_days.parquet (one row per contract x zone x day)
"""
from __future__ import annotations

import numpy as np

from src.common import connect, get_logger, load_config, rpath, sql_path

log = get_logger("contracts")


# Deadline ("by date") binary markets (DECISIONS D18): fixed title patterns.
DEADLINE_RE = (r"(?i)\b(by|before)\s+(the\s+)?(end\s+of\s+)?(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|"
               r"nov|dec|q[1-4]|\d{1,2}[/-]|20\d\d|year|month|week|monday|tuesday|wednesday|"
               r"thursday|friday|saturday|sunday|tomorrow|election|inauguration)"
               r"|\bin\s+(20\d\d|this\s+(year|month|week))\b|\bthis\s+(year|month|week)\s*\?")


def build(cfg: dict | None = None, min_volume: float | None = None,
          out_file: str = "contract_days.parquet", placebo_seed: int | None = None,
          placebo_n: int = 3000, hazard: bool = True) -> None:
    """placebo_seed: if set, build the placebo panel of spec 10.2(b) instead: `placebo_n`
    binary markets drawn at random among those classified OTHER, each with a random sign,
    all in a single cell (zone PLACEBO, theme PLACEBO).
    hazard: deadline binaries are valued as implied hazard rates (D18); False gives the
    probability-based panel used by the D12 robustness variant."""
    cfg = cfg or load_config()
    proc = rpath("processed", cfg)
    inc = cfg["pm_inclusion"]
    min_volume = inc["min_volume_7d_usd"] if min_volume is None else min_volume
    tz, snap, stale_h = cfg["snapshot"]["timezone"], cfg["snapshot"]["time"], cfg["snapshot"]["stale_hours"]
    start, end = cfg["sample"]["start"], cfg["sample"]["end"]
    con = connect()
    lab, daily = sql_path(proc / "contracts_classified.parquet"), sql_path(proc / "pm_daily.parquet")

    if placebo_seed is None:
        # Usable markets: theme with a defined direction or a partition bucket, located in a zone.
        con.execute(f"""
        CREATE TABLE mk AS
        SELECT platform, platform_id, event_key, theme, zones, ea_country, geo_region, oil_relevant,
               direction, partition, unit, bucket_value, title,
               created_at, coalesce(closes_at, resolves_at) AS close_ts
        FROM read_parquet('{lab}')
        WHERE theme <> 'OTHER' AND len(zones) > 0 AND (direction <> 0 OR partition)
        """)
    else:
        other = con.execute(f"""
            SELECT platform, platform_id FROM read_parquet('{lab}')
            WHERE theme = 'OTHER' ORDER BY platform, platform_id""").df()
        rng = np.random.default_rng(placebo_seed)
        pick = other.iloc[rng.permutation(len(other))[:placebo_n]].copy()
        pick["direction"] = rng.choice([-1, 1], size=len(pick))
        con.register("pick", pick)
        con.execute(f"""
        CREATE TABLE mk AS
        SELECT l.platform, l.platform_id, l.event_key, 'PLACEBO' AS theme, ['PLACEBO'] AS zones,
               NULL::VARCHAR AS ea_country, NULL::VARCHAR AS geo_region, false AS oil_relevant,
               p.direction, false AS partition, NULL::VARCHAR AS unit, NULL::DOUBLE AS bucket_value,
               l.title, l.created_at, coalesce(l.closes_at, l.resolves_at) AS close_ts
        FROM read_parquet('{lab}') l JOIN pick p USING (platform, platform_id)
        """)
    con.execute(f"""ALTER TABLE mk ADD COLUMN deadline BOOLEAN""")
    con.execute(f"""UPDATE mk SET deadline = {'true' if hazard else 'false'}
                    AND NOT partition AND regexp_matches(coalesce(title, ''), '{DEADLINE_RE}')""")
    log.info("usable markets: %s", con.execute("SELECT theme, count(*) FROM mk GROUP BY 1 ORDER BY 1").fetchall())
    log.info("deadline (hazard-rate) markets: %s", con.execute("SELECT count(*) FILTER (WHERE deadline), count(*) FROM mk").fetchall())

    # Market-day grid with forward-filled last price, staleness and trailing volume.
    con.execute(f"""
    CREATE TABLE md AS
    WITH grid AS (
        SELECT mk.platform, mk.platform_id, CAST(d.day AS DATE) AS day
        FROM mk, LATERAL generate_series(
            greatest(CAST(timezone('{tz}', mk.created_at) AS DATE), DATE '{start}'),
            least(CAST(timezone('{tz}', mk.close_ts) AS DATE), DATE '{end}'),
            INTERVAL 1 DAY) AS d(day)
    ), j AS (
        SELECT g.*, p.px_last, p.last_ts, p.px_early, coalesce(p.volume_usd, 0) AS vol,
               coalesce(p.volume_late_usd, 0) AS vol_late
        FROM grid g LEFT JOIN read_parquet('{daily}') p
          ON p.platform = g.platform AND p.platform_id = g.platform_id AND p.snap_date = g.day
    ), f AS (
        SELECT platform, platform_id, day, px_early, vol, vol_late,
               last_value(px_last IGNORE NULLS) OVER w AS px,
               last_value(last_ts IGNORE NULLS) OVER w AS last_ts,
               sum(vol) OVER (PARTITION BY platform, platform_id ORDER BY day
                              RANGE BETWEEN INTERVAL 6 DAY PRECEDING AND CURRENT ROW) AS vol7d
        FROM j
        WINDOW w AS (PARTITION BY platform, platform_id ORDER BY day ROWS UNBOUNDED PRECEDING)
    )
    SELECT platform, platform_id, day, px, last_ts, vol7d, vol AS vol1d, vol_late,
           -- last price at least `persist_h` hours before the snapshot
           coalesce(px_early, lag(px) OVER (PARTITION BY platform, platform_id ORDER BY day)) AS px_early,
           timezone('{tz}', CAST(day AS DATE) + TIME '{snap}:00') AS snap_ts
    FROM f
    """)

    # Binary contracts. Time to deadline in years, floored at the inclusion limit (D18).
    TAU = (f"(greatest(date_diff('second', md.snap_ts, mk.close_ts) / 86400.0, "
           f"{inc['min_days_to_resolution']}) / 365.25)")
    con.execute(f"""
    CREATE TABLE cd_bin AS
    SELECT mk.platform || ':' || mk.platform_id AS contract_id, mk.platform, mk.event_key,
           mk.theme, mk.zones, mk.ea_country, mk.geo_region, mk.oil_relevant,
           CAST(mk.direction AS INTEGER) AS sign,
           CASE WHEN mk.deadline THEN 'hazard' ELSE 'prob' END AS unit, md.day,
           CASE WHEN mk.deadline   -- implied hazard rate, per year (D18)
                THEN -ln(1 - least(greatest(md.px, 0.001), 0.999)) / {TAU}
                ELSE md.px END AS value,
           CASE WHEN mk.deadline
                THEN -ln(1 - least(greatest(md.px_early, 0.001), 0.999)) / {TAU}
                ELSE md.px_early END AS value_early,
           md.px, md.last_ts, md.snap_ts, md.vol7d, md.vol1d, md.vol_late,
           date_diff('second', md.snap_ts, mk.close_ts) / 86400.0 AS ttr_days,
           1 AS n_buckets
    FROM mk JOIN md USING (platform, platform_id)
    WHERE NOT mk.partition
    """)
    # Partition contracts: expected value over buckets with a price, renormalised.
    con.execute(f"""
    CREATE TABLE cd_part AS
    SELECT mk.platform || ':' || mk.event_key || ':EV' AS contract_id, mk.platform, mk.event_key,
           any_value(mk.theme) AS theme, any_value(mk.zones) AS zones,
           any_value(mk.ea_country) AS ea_country, any_value(mk.geo_region) AS geo_region,
           any_value(mk.oil_relevant) AS oil_relevant, 1 AS sign, any_value(mk.unit) AS unit,
           md.day,
           sum(md.px * mk.bucket_value) FILTER (WHERE md.px IS NOT NULL)
             / nullif(sum(md.px) FILTER (WHERE md.px IS NOT NULL), 0) AS value,
           sum(md.px_early * mk.bucket_value) FILTER (WHERE md.px_early IS NOT NULL)
             / nullif(sum(md.px_early) FILTER (WHERE md.px_early IS NOT NULL), 0) AS value_early,
           sum(md.px) FILTER (WHERE md.px IS NOT NULL) AS px,
           max(md.last_ts) AS last_ts, any_value(md.snap_ts) AS snap_ts, sum(md.vol7d) AS vol7d,
           sum(md.vol1d) AS vol1d, sum(md.vol_late) AS vol_late,
           date_diff('second', any_value(md.snap_ts), max(mk.close_ts)) / 86400.0 AS ttr_days,
           count(md.px) AS n_buckets
    FROM mk JOIN md USING (platform, platform_id)
    WHERE mk.partition
    GROUP BY mk.platform, mk.event_key, md.day
    """)

    out = proc / out_file
    con.execute(f"""
    COPY (
        WITH u AS (SELECT * FROM cd_bin UNION ALL BY NAME SELECT * FROM cd_part)
        SELECT u.* EXCLUDE (zones), z.zone,
               (u.last_ts IS NULL OR date_diff('second', u.last_ts, u.snap_ts) > {stale_h} * 3600) AS stale,
               coalesce((u.value IS NOT NULL
                AND u.vol7d >= {min_volume}
                AND u.ttr_days BETWEEN {inc['min_days_to_resolution']} AND {inc['max_days_to_resolution']}
                AND (u.unit NOT IN ('prob', 'hazard') OR u.px BETWEEN {inc['min_prob']} AND {inc['max_prob']})
                AND (u.unit IN ('prob', 'hazard') OR (u.n_buckets >= 2 AND u.px BETWEEN 0.5 AND 1.5))
               ), false) AS eligible
        FROM u, LATERAL unnest(u.zones) AS z(zone)
        ORDER BY contract_id, zone, day
    ) TO '{sql_path(out)}' (FORMAT PARQUET, COMPRESSION ZSTD)
    """)
    s = con.execute(f"""SELECT theme, count(DISTINCT contract_id) n_contracts, count(*) n_rows,
                               sum(CAST(eligible AS INTEGER)) n_eligible_rows
                        FROM read_parquet('{sql_path(out)}') GROUP BY 1 ORDER BY 1""").df()
    log.info("contract-day panel written to %s\n%s", out, s.to_string())


if __name__ == "__main__":
    build()
