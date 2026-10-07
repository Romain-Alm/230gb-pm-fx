# Data schema

This file records the actual schemas of the raw files, as inspected on 2026-10-03, and the
conventions the pipeline relies on. All timestamps are stored in UTC and converted explicitly.
DuckDB connections are pinned to UTC (`SET TimeZone='UTC'`), because the host default is
America/Los_Angeles.

## Prediction markets: Probalytics (Kairos data estate, read-only)

The root is `KAIROS_DATA_ROOT`, by default `D:/haas-mfe-g9-cg/kairos-data`. It covers
Polymarket and Kalshi.

### Markets metadata

Files:
- `historical/probalytics/raw/markets/markets.parquet`: frozen archive, 13.96 M markets, indexed up to 2026-07-21.
- `historical/probalytics/raw_export_20260924/markets/markets.parquet`: 21.07 M markets, up to 2026-09-25.

| Column | Type | Notes |
|---|---|---|
| `id` | UUID | Probalytics market id |
| `platform` | VARCHAR | `POLYMARKET` or `KALSHI` |
| `platform_id` | VARCHAR | Polymarket condition id (`0x...`) or Kalshi market ticker |
| `slug`, `url`, `title`, `description` | VARCHAR | `title` is the market question; `description` holds the resolution rules |
| `category`, `tags` | VARCHAR, VARCHAR[] | **Empty on every row**, so they are not used |
| `market_type` | VARCHAR | BINARY, SCALAR, PERPETUAL |
| `outcomes` | STRUCT(id, platform_id, name, index)[] | Yes/No for binaries |
| `created_at`, `opened_at`, `closes_at`, `resolves_at`, `end_date` | TIMESTAMPTZ | `closes_at` is set at listing |
| `resolution_winning_outcome_id`, `resolution_outcome_payouts`, `resolution_resolved_at` | | Outcome after resolution (not used for signals) |
| `status` | VARCHAR | RESOLVED, ACTIVE, PENDING, CLOSED, PAUSED |

Derived keys:
- **Polymarket event:** `regexp_extract(url, '/event/([^/?]+)', 1)`. Example: `fed-decision-in-january`.
- **Kalshi:**
  - the event is the ticker without its last `-` segment (`KXFEDDECISION-26JUL`);
  - the series is the first segment (`KXFEDDECISION`);
  - series categories come from `live/market-universe/metadata/kalshi_series_categories.json`.

### Trades tape (one Parquet file per venue and day)

Files:
- Frozen archive: `derived/backtest/probalytics/trades/venue={polymarket,kalshi}/date=YYYY-MM-DD/probalytics.parquet`, 2021-06-30 to 2026-07-21.
- Live export: `derived/backtest/probalytics_live/trades/venue=.../date=.../`, same schema, 2026-07-21 to 2026-09-24. After 2026-09-24 it is near-empty.

| Column | Type | Notes |
|---|---|---|
| `condition_id` | VARCHAR | Equals `markets.platform_id` |
| `token_id`, `outcome` | VARCHAR | Kalshi No side: `TICKER\|no` |
| `price` | DOUBLE | Price of the traded outcome token, 0 to 1 |
| `size` | DOUBLE | Shares or contracts |
| `amount_usd` | DOUBLE | **Unreliable**: negative values on both venues. Volume uses `abs(price * size)` instead |
| `timestamp_ms` | BIGINT | UTC epoch milliseconds (Polymarket: block time, whole seconds) |
| `is_yes_side` | BOOLEAN | Yes probability = `price` if true, `1 - price` otherwise |
| `transaction_hash` | VARCHAR | Polymarket fills against several makers share one hash |

Switching between the archive and the live tape uses a single cutoff, `2026-07-21 16:00:00 UTC`: archive rows before it, live rows from it on. Continuity was checked on the candidate markets.

## Processed files (`data/processed`, generated)

| File | Content |
|---|---|
| `pm_markets.parquet` | Macro candidate markets (wide prefilter) with event and series keys |
| `pm_daily.parquet` | Sparse market x snapshot-day panel: `px_last`, `px_vwap_1h`, `last_ts`, `volume_usd`, `n_trades` |
| `contracts_classified.parquet` | Theme, zones, direction, partition bucket values, and the rule behind each label |
| `contract_days.parquet` | Dense contract x zone x day panel: value, staleness, `vol7d`, `vol1d`, `ttr_days`, `eligible` |
| `contract_changes.parquet` | Standardised signed daily changes per contract |
| `theme_index.parquet` | Daily theme indices per (zone, theme) cell, volume-weighted and equal-weighted |

### Snapshot convention

A trade at London local time before 16:00 belongs to that day's snapshot; a trade at or after 16:00 belongs to the next day's. DST is handled by converting each trade to Europe/London time.

## Market data (to be added)

The Bloomberg FX, forward/NDF and risk-series exports go to `data/raw/market/` (not committed if licensed). Their format is documented here once received.
