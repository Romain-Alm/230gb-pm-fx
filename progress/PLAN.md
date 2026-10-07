# Plan: MFE 230GB final project (prediction markets x FX)

Plan approved on 3 October 2026, kept as written. What was actually done, and every deviation, is in `DECISIONS.md` and `log_2026-10-03.md`.

> **Data access.** The paths below point to the Kairos data estate. These data are confidential: access cannot be given, and neither the data nor the Kairos code are included in this repository (see `README.md`, "Data").

## Context

The course asks for two distinct strategies (A on G10/OECD, B on EM), a central alternative data source, complete metrics, at least one OOS or robustness test, and an economic risk analysis. The presentation is on Thursday 8 October 2026 at 3 pm. `project_spec_230GB.md` fixes the design; `assignment_230GB.md` links each requirement to the spec. Today is Saturday 3 October, so about 4.5 working days remain.

Priority: robust signals, the strategies, portfolio construction and evaluation. The HTML page comes after Thursday. The team supplies the FX data (Bloomberg). Contract classification is deterministic: it builds on the Arb component, with no LLM call.

## Assessment in brief

- **The spec is very good on what is graded.** Ex ante economic logic, frozen inclusion rules, timing traps, placebos, risk linked to the course concepts. The architecture is kept; the scope is reduced.
- **The PM data are better than expected.**
  - The trades tape gives a daily panel of ~14k macro markets (8.7k Polymarket, 5.3k Kalshi) in ~5 s.
  - Both venues are present, so the "disagreement across platforms" asked for by the instructor is feasible.
  - The live export extends the data to 2026-09-27: the 2026 OOS goes from 7 to 9 months.
- **Limits of the PM data.**
  - Polymarket is thin before mid-2024.
  - Kalshi has non-US central banks (`KXCBDECISION*`) only from November 2025.
  - The category and tag fields are empty everywhere.
  - Expected consequence: non-US MONETARY cells will be poor in 2024-2025. The best covered will probably be US MONETARY/INFLATION, FISCAL_POLITICAL (FR, UK, JP, DE elections), GEOPOLITICS and TRADE_TARIFFS. The coverage table will decide.
- **Main risk: Strategy A.** Daily prediction with a |t|>3 filter over ~18 months is likely to select nothing. An earlier internal study also rejected "prediction markets lead futures" at the intraday horizon.
  - Decision: the primary rule follows the **theory sign**, with no estimation.
  - The regression-gated version remains a variant, and the regressions serve as diagnostics.
  - The **weekend gap test** is our cleanest identification: FX is closed, prediction markets are open. It is the core of the evidence for A.
- **Strategy B is the most promising and the closest to the course** (carry crash risk, downside beta). Two cheap but decisive additions:
  - the base EM carry over a long history (2010+ if the Bloomberg export allows), to document the crash-risk premise; the timing only starts in 2024;
  - a VIX-timed carry benchmark, because "is it just VIX?" will be the grader's first question.

## Deviations from the spec (to be logged in DECISIONS.md from day 1)

1. The classification is deterministic (rules), not LLM-based. Reproducible and free. AI is used only through the code written with Claude Code, documented in `ai_log/`.
2. Strategy A: the primary rule follows the theory sign; the |t|>3 rule frozen on 2024-2025 becomes a variant, reported even if empty.
3. The OOS runs from 2026-01-01 to 2026-09-27, thanks to the `probalytics_live` tape. Swap-ledger discrepancies are below 1% and are noted.
4. The weekend gap test uses Dukascopy intraday data (hourly, free, scriptable), because Bloomberg keeps only about 140 days of intraday bars.
5. Deferred: bond leg (6.5), constant-horizon interpolation of implied rates (we take the nearest eligible meeting plus the "number of cuts" markets), extensions 7.5, section 9 (except the VIX-timed carry), HTML page.
6. Volume is computed from `amount_usd`, deduplicated and filtered of negative values (Kalshi anomaly of June 2026).

## Location and environment

- The repository is `D:\haas-mfe-g9-cg\Kairos_Project\Perso\Piero&Romain\GB\230gb-pm-fx\`. It follows the structure of spec 11.1, without `site/` for now.
- The `.venv` belongs to the project (Python 3.13), with a `requirements.txt`: pandas, numpy, duckdb, pyarrow, statsmodels, linearmodels, scipy, matplotlib, pyyaml, pytest. The shared venv is not touched.
- The entry point is `run_all.py`, without a Makefile: the `&` in the path causes problems.
- `config/config.yaml` is the only configuration. It holds the path of kairos-data (overridable by `KAIROS_DATA_ROOT`), the snapshot time (16:00 Europe/London by default, adjustable if FX is at the NY close) and every threshold of the spec.
- A single DuckDB connection helper sets `SET TimeZone='UTC'`, because the host defaults to America/Los_Angeles.

## Code and data reused

- **PM prices**: `kairos-data\derived\backtest\probalytics\trades\venue={polymarket,kalshi}\date=*\probalytics.parquet` (2021 to 2026-07-21) and `...\probalytics_live\trades\...` (2026-07-21 to 2026-09-27).
  - Yes probability: `is_yes_side ? price : 1-price`.
  - Key: `condition_id` = `markets.platform_id`.
- **Market metadata**: `historical\probalytics\raw\markets\markets.parquet`, union with `raw_export_20260924\markets\markets.parquet` for markets created after July.
  - Polymarket event key: `regexp_extract(url,'/event/([^/?]+)',1)`.
  - Kalshi: the series is the first segment of the ticker, the event is the ticker without its last segment.
- **Zone**: `Kairos_Project\Arb\Cross_Venue\geo_registry.py` (`resolve(event_title, question, tags)`, which returns countries, institutions and central bankers, people, chokepoints), plus `people_generated.py`. Both are copied into `src/pm/vendor/` with a provenance header.
- **Theme**: `kairos-main\infra\packages\market_replay\universe\classifier_v2.py` (`classify_payload`). Its sub-categories monetary_policy, inflation, fiscal_trade, elections, government, armed_conflict, diplomacy and sanctions_security are used. It is also copied into `vendor/`.
- **US cross-check**: `kairos-data\strategies\macro_information_flow\census_v1\macro_census.duckdb` (15k US contracts already labelled by family), to check our US classification.
- **Kalshi series mapping**: `live\market-universe\metadata\kalshi_series_categories.json`.

## Steps

### Day 1, Saturday 3: foundations, PM data, classification

1. **Repository skeleton**, venv, config, `DECISIONS.md`, `data/SCHEMA.md` (actual schemas of the tape and the markets, price conventions, UTC).
2. **`src/data/pm_markets.py`**: metadata, event/series keys, broad macro pre-filter (regex plus a list of Kalshi series).
3. **`src/data/pm_panel.py`**, which writes to `data/processed/`:
   - the daily snapshot: last trade strictly before 16:00 London, with DST conversion per date;
   - the stale flag if no trade for more than 6 h;
   - the trailing 7-day volume;
   - hourly bars (for shock persistence);
   - a no-duplicate check at the 2026-07-21 junction.
4. **`src/pm/classify.py`**, a classification at the event level (not the market level):
   - **zone**: `geo_registry.resolve`, then mapping to US / EA (+DE/FR/IT/ES) / JP / UK / CH / AU / NZ / CA / NO / SE / CN / EM-ISO / GLOBAL;
   - **theme**: hand-written table of Kalshi series, then `classifier_v2`, then keywords to separate fiscal and tariffs; otherwise OTHER;
   - **direction**: regex per theme (hike/cut, escalation/ceasefire, tariff imposed/lifted, government fall/dissolution), plus `data/manual/party_fiscal_stance.csv` (sources) for elections; NONE if ambiguous;
   - **unit**: bracket detection (Kalshi strikes, "between X and Y", "N cuts", "X bps").
5. **Validation file**: `ai_log/classification/validation_sheet.csv`, 200 events drawn at random and stratified, blind. **The team labels them (about 1 hour for two).** Accuracy is measured per field, and the rules are corrected only on this sample.

### Day 2, Sunday 4: coverage (GATE), indices, engine

6. **Coverage table**: `results/coverage.csv` plus a zone x theme x quarter heatmap, with the rule "at least 60% of days covered" over the training period.
   - **15-minute check with the team** to freeze zones and themes, and the **table of theory signs** (in particular US TRADE_TARIFFS and the fiscal regime). Everything is logged in `DECISIONS.md` before any backtest.
7. **`src/pm/units.py`**:
   - expected value of brackets (renormalisation, bucket midpoints, open buckets at a configured distance);
   - central-bank meetings: expected change in bp;
   - expected number of cuts.
8. **`src/pm/indices.py`** (spec 4.5, steps 1 to 6):
   - daily change if both snapshots are non-stale;
   - standardisation by an EWMA-60 volatility computed up to t-1, winsorisation at 5σ;
   - volume-weighted (and equal-weighted) aggregation in each cell, then cumulation into the index;
   - resolution surprise stored separately.
   - Output in a generic `(date, series_id, value)` format, so that the section 9 benchmarks can be plugged in later.
9. **`src/pm/shocks.py`**:
   - EWMA level with a 20-day half-life, shock at z>2;
   - false-shock filter: persistence of at least 4 h (hourly bars), volume threshold, and same sign on the other venue if it covers the event.
10. **`src/backtest/`**, built on synthetic data while waiting for FX:
    - `engine.py`: positions at t from signals known up to t, return from t to t+1, volatility target with 60-day covariance, 3x leverage cap, 30% cap per pair, no-trade band, monthly or daily rebalancing;
    - `costs.py`: bid/ask half-spread, fallback table in bp, costs doubled when VIX is above its 90th percentile, roll cost;
    - `metrics.py`: every metric of spec 10.1.
11. **`src/data/fx.py`** as soon as the Bloomberg export arrives:
    - log-spot, carry = s - f annualised (forward points or NDF outright), rx = Δs + carry/252;
    - calendars and stale flags.
12. **`src/data/dukascopy.py`**: hourly G10 intraday 2024+ for the weekend test.

### Day 3, Monday 5: strategies

13. **Strategy B** (`src/strategies/strategy_b.py`), first because it is the simplest and the most solid:
    - EM universe screen (`data/manual/em_exclusions.csv`, IRR classification and capital controls, with reasons);
    - carry from forwards/NDFs;
    - month-end: long top 3, short bottom 3, inverse-volatility weights, 10% volatility target;
    - timing w(t): monthly level on an expanding z-score, a shock cutting to 0.25, linear re-risk over 10 days;
    - full 3x3x3 grid (27 cells, all shown);
    - benchmarks: raw carry and VIX-timed carry (same rule);
    - drawdown decomposition into geopolitical and other episodes (August 2024 explicitly).
14. **Strategy A** (`src/strategies/strategy_a.py`):
    - relative signals x_k(i, USD), plus the spillover map 6.3 frozen in the config;
    - **primary rule**: Σ_k theory_sign_k × z(x_k), equal risk across themes, divided by σ̂², then volatility target, caps and no-trade band; dollar-neutral and with-dollar versions;
    - **diagnostics**: pooled panel with pair fixed effects, Driscoll-Kraay errors, contemporaneous and predictive (1, 5 and 20 days, Newey-West); theme x pair t-stat heatmap against the expected sign; fiscal interaction with debt/GDP and a yield-cap dummy (simple version); pooled versus specific Wald test;
    - **spec variant**: |t|>3 filter on 2024-2025, frozen for 2026, plus an expanding-window version;
    - **weekend gap test**: every weekend since 2024, from Friday 17:00 NY to Monday 07:00 London (robustness: Sunday 18:00 NY), pooled regression; optional tradable version.

### Day 4, Tuesday 6: robustness and risk

15. **Robustness**:
    - 2026 OOS and expanding window, sub-periods 2024/2025/2026;
    - full grids;
    - placebos: (a) dates shuffled within the month, (b) randomly drawn OTHER contracts, (c) reversed sign;
    - leave-one-event-out;
    - volume versus equal weights;
    - costs at 0.5x / 1x / 2x / 3x, and break-even cost.
16. **Risk** (`src/risk/`):
    - betas on SPX, MSCI World, ΔVIX, Brent, DXY and carry factors;
    - Lettau, Maggiori and Weber downside beta (before and after timing for B);
    - episodes: August 2024, April 2025 tariffs, Israel-Iran June 2025, 2026 Iran war;
    - conditional performance (VIX terciles, Brent shocks, strong or weak dollar months, shock days);
    - top 10 drawdowns with the dominant theme;
    - concentration (HHI by currency, theme, event, month), liquidity, country risk for B;
    - **A/B correlation** of returns and drawdowns.
17. **Figures** in PNG/SVG in `results/figures/`, and tables in `results/`.

### Day 5, Wednesday 7: presentation material

18. **Results summary**: one page per strategy (idea, signal, rule, key numbers, losses, risk, limitations), figures ready for the slides.
19. **Documentation**: `README.md` (reproduce with one command), `ai_log/code_generation.md`, complete `DECISIONS.md`.
20. **Thursday morning**: buffer and rehearsal. The HTML page comes afterwards.

## What the team provides

- **FX export** in long format `date, ticker, field, value` (CSV or Parquet), or the raw BDH sheet: the loader is adapted. The snapshot time must be stated (BFIX/WMR 16:00 London preferably; if it is a NY close, the PM snapshot is aligned on it).
  - **G10**: spot, 1M forward points, bid/ask.
  - **EM**: spot and 1M NDF/forward outright bid/ask for the 18 candidates of spec 7.2, plus NDF fixings if possible.
  - **Risk series**: VIX, Brent, MSCI World TR, SPX TR, DXY or BBDXY, a G10/EM carry index if available.
  - **History**: from 2010 for EM (crash-risk premise); at least from 2023-06 (volatility warm-up).
- **The 200 validation lines to label** (Saturday evening or Sunday).
- **15 minutes on Sunday** to freeze the coverage table and the sign table.

## Verification

- **`pytest`** covers the tests of spec 12:
  - no look-ahead (random dates);
  - US/EU DST gap weeks (March and October-November 2024, 2025, 2026);
  - inclusion uses only information available at t;
  - index continuity at a contract roll;
  - bracket expected value equal to a hand-computed example;
  - backtest timing from t to t+1;
  - cost round trip on one pair.
- **Visual checks** of the indices on known episodes (50 bp Fed cut in September 2024, 2 April 2025 tariffs, 13 June 2025 strike on Iran, French government crises). They are used only to find bugs, never to tune parameters.
- **Base carry**: August 2024 drawdown visible, comparison with a Bloomberg carry index if available.
- **`python run_all.py`** rebuilds every table and figure from an empty `data/processed`; the runtime is measured.
