"""Prediction-market metadata: event keys and a wide macro candidate set.

Reads the frozen Probalytics markets archive and the 2026-09-24 export (read-only),
derives event and series keys, and keeps markets alive during the sample whose title
or event slug matches a wide macro vocabulary. The prefilter is recall-oriented;
precision comes from `src.pm.classify`.

Output: data/processed/pm_markets.parquet
"""
from __future__ import annotations

import json

from src.common import connect, get_logger, kpath, load_config, rpath, sql_path

log = get_logger("pm_markets")

# Kalshi series categories (venue metadata) that can carry macro events.
KALSHI_KEEP_CATEGORIES = ("Economics", "Politics", "Elections", "World")

# Wide macro vocabulary (RE2 syntax, case-insensitive). Recall first.
MACRO_TERMS = [
    # monetary
    r"\bfed\b", r"fomc", r"federal reserve", r"fed funds", r"interest rates?",
    r"rate (cut|hike)s?", r"(cut|hike|raise|lower)s? (interest )?rates", r"\bbps\b",
    r"basis points?", r"powell", r"warsh", r"hassett", r"central bank", r"\becb\b",
    r"lagarde", r"bank of (japan|england|canada|korea|mexico)", r"\bboj\b", r"\bueda\b",
    r"\bboe\b", r"swiss national bank", r"\bsnb\b", r"riksbank", r"norges bank",
    r"reserve bank", r"\brba\b", r"\brbnz\b", r"banxico", r"copom", r"selic", r"\brbi\b",
    r"\bpboc\b", r"monetary policy", r"policy rate", r"yield curve control",
    # inflation
    r"\bcpi\b", r"inflation", r"\bpce\b", r"\bppi\b", r"consumer price",
    # fiscal / political
    r"election", r"elected", r"prime minister", r"chancellor", r"president",
    r"parliament", r"dissol", r"no[- ]confidence", r"confidence vote", r"impeach",
    r"resign", r"shut ?down", r"debt (ceiling|limit|brake)", r"budget", r"deficit",
    r"fiscal", r"\btax", r"reconciliation", r"big beautiful bill", r"coalition",
    r"\bldp\b", r"takaichi", r"ishiba", r"koizumi", r"macron", r"le pen", r"bardella",
    r"bayrou", r"barnier", r"lecornu", r"starmer", r"reeves", r"farage", r"reform uk",
    r"\bmerz\b", r"\bafd\b", r"scholz", r"meloni", r"carney", r"poilievre", r"albanese",
    r"trudeau", r"midterm", r"popular vote", r"electoral college", r"\bsenate\b",
    r"\bhouse\b",
    # trade
    r"tariff", r"trade (deal|war|agreement|talks)", r"export control", r"embargo",
    r"de minimis", r"usmca", r"section (232|301)",
    # geopolitics
    r"\bwar\b", r"cease-?fire", r"truce", r"peace (deal|agreement|talks|treaty|plan)",
    r"invade", r"invasion", r"military", r"\bstrikes?\b", r"airstrike", r"\bbomb",
    r"missile", r"nuclear", r"attack", r"troops", r"blockade", r"annex", r"sanction",
    r"hostage", r"hamas", r"hezbollah", r"houthi", r"\biran", r"israel", r"gaza",
    r"russia", r"ukrain", r"putin", r"zelensk", r"taiwan", r"north korea", r"kim jong",
    r"hormuz", r"red sea", r"\bnato\b", r"khamenei", r"maduro", r"venezuela", r"regime",
    r"\bcoup\b", r"martial law", r"conflict", r"drone", r"escalat",
]

# Obvious non-macro families (sports, crypto/asset prices, entertainment, weather,
# speech-mention markets). Applied to Polymarket titles and to Kalshi series
# without a venue category.
EXCLUDE_TERMS = [
    r"\bvs\.?\b", r"\bnba\b", r"\bnfl\b", r"\bmlb\b", r"\bnhl\b", r"\bufc\b",
    r"premier league", r"champions league", r"world cup", r"super bowl", r"grand slam",
    r"\bf1\b", r"formula 1", r"\bgolf", r"olympic", r"up or down", r"bitcoin", r"\bbtc\b",
    r"ethereum", r"\beth\b", r"solana", r"\bxrp\b", r"crypto", r"\btoken", r"airdrop",
    r"price of", r"temperature", r"weather", r"hurricane", r"box office", r"oscar",
    r"grammy", r"album", r"\bsong", r"movie", r"\bsays?\b", r"mention", r"tweet",
    r"\bposts?\b", r"spotify", r"youtube", r"tiktok",
]


def _re(terms: list[str]) -> str:
    return "(?i)(" + "|".join(terms) + ")"


def build(cfg: dict | None = None) -> None:
    cfg = cfg or load_config()
    out = rpath("processed", cfg) / "pm_markets.parquet"
    start, end = cfg["sample"]["start"], cfg["sample"]["end"]
    con = connect()

    series_cat = json.loads(kpath("kalshi_series_categories", cfg).read_text(encoding="utf-8"))
    con.execute("CREATE TABLE series_cat(series VARCHAR, kalshi_category VARCHAR, series_title VARCHAR)")
    con.executemany("INSERT INTO series_cat VALUES (?, ?, ?)",
                    [(k, v.get("category"), v.get("title")) for k, v in series_cat.items()])

    m_raw = sql_path(kpath("pm_markets_raw", cfg))
    m_exp = sql_path(kpath("pm_markets_export", cfg))
    macro, excl = _re(MACRO_TERMS), _re(EXCLUDE_TERMS)
    keep_cats = ", ".join(f"'{c}'" for c in KALSHI_KEEP_CATEGORIES)

    con.execute(f"""
    CREATE TABLE m AS
    WITH u AS (
        SELECT *, 1 AS src FROM read_parquet('{m_exp}')
        UNION ALL BY NAME
        SELECT *, 2 AS src FROM read_parquet('{m_raw}')
    ), d AS (
        SELECT * FROM u
        QUALIFY row_number() OVER (PARTITION BY platform, platform_id ORDER BY src) = 1
    )
    SELECT
        lower(CAST(platform AS VARCHAR)) AS platform,
        platform_id,
        CAST(id AS VARCHAR) AS market_uuid,
        CASE WHEN lower(CAST(platform AS VARCHAR)) = 'polymarket'
             THEN regexp_extract(url, '/event/([^/?]+)', 1)
             ELSE regexp_replace(platform_id, '-[^-]*$', '') END AS event_key,
        CASE WHEN lower(CAST(platform AS VARCHAR)) = 'kalshi'
             THEN split_part(platform_id, '-', 1) END AS series,
        slug, url, title, description,
        CAST(market_type AS VARCHAR) AS market_type,
        [o.name FOR o IN outcomes] AS outcome_names,
        list_filter(outcomes, o -> o.id = resolution_winning_outcome_id)[1].name AS winning_outcome,
        created_at, opened_at, closes_at, resolves_at, end_date, resolution_resolved_at,
        CAST(status AS VARCHAR) AS status
    FROM d
    WHERE created_at <= TIMESTAMPTZ '{end} 23:59:59+00'
      AND coalesce(resolution_resolved_at, resolves_at, closes_at, end_date,
                   TIMESTAMPTZ '2100-01-01 00:00:00+00') >= TIMESTAMPTZ '{start} 00:00:00+00'
      AND NOT (lower(CAST(platform AS VARCHAR)) = 'kalshi' AND platform_id LIKE 'KXMVE%')
    """)
    n_all = con.execute("SELECT platform, count(*) FROM m GROUP BY 1").fetchall()
    log.info("markets alive in sample: %s", n_all)

    con.execute(f"""
    COPY (
        SELECT m.*, s.kalshi_category, s.series_title,
               replace(m.event_key, '-', ' ') AS event_text
        FROM m LEFT JOIN series_cat s ON m.series = s.series
        WHERE (
            m.platform = 'kalshi' AND (
                s.kalshi_category IN ({keep_cats})
                OR (s.kalshi_category IS NULL AND regexp_matches(m.title, '{macro}')
                    AND NOT regexp_matches(m.title, '{excl}'))
            )
        ) OR (
            m.platform = 'polymarket'
            AND (regexp_matches(m.title, '{macro}')
                 OR regexp_matches(replace(m.event_key, '-', ' '), '{macro}'))
            AND NOT regexp_matches(m.title, '{excl}')
        )
    ) TO '{sql_path(out)}' (FORMAT PARQUET, COMPRESSION ZSTD)
    """)
    stats = con.execute(f"""
        SELECT platform, count(*) n, count(DISTINCT event_key) events
        FROM read_parquet('{sql_path(out)}') GROUP BY 1""").fetchall()
    log.info("macro candidates written to %s: %s", out, stats)


if __name__ == "__main__":
    build()
