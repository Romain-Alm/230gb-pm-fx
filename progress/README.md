# Progress: 230GB project (prediction markets x FX)

Overall dashboard, updated at each step.

**Every number**: `results/RESULTS.md` (definitive run on the delivered market data, D28). The preliminary run on free data stays in `results/preliminary_free/RESULTS.md`. Both files are generated automatically from the results (`src/report/summary_md.py`).
- Day-by-day log: `log_2026-10-03.md`.
- Approved plan: `PLAN.md`.
- Coverage decision: `GATE_coverage.md`.
- Market data request: `DATA_REQUEST.md`.

Presentation: **Thursday 8 October 2026, 3 pm**. The HTML page comes afterwards.

## Status by step

| # | Step | Status | Output |
|---|---|---|---|
| 1 | Skeleton, venv, config, `DECISIONS.md` (D1 to D15) | done | `config/config.yaml` |
| 2 | PM metadata and macro pre-filter | done | `data/processed/pm_markets.parquet` |
| 3 | Daily panel of PM prices (16:00 London) | done | `pm_daily.parquet` |
| 4 | Rule-based classification (no LLM) | done (rules v1) | `contracts_classified.parquet` |
| 5 | Validation sheet (200 events) | **ready, to be labelled by the team** | `ai_log/classification/validation_sheet_1.csv` to `_4.csv` |
| 6 | Coverage table and gate | done, decisions taken (D13 to D15) | `results/coverage*.csv`, heatmap |
| 7 | Common units, contract-day panel, theme indices | done | `contract_days.parquet`, `theme_index*.parquet` |
| 8 | Geopolitical shocks and false-shock filter | done (19 confirmed shocks) | `geo_signals.parquet` |
| 9 | Weekend changes (weekend gap test, PM side) | done (142 weekends) | `weekend_changes.parquet` |
| 10 | Backtest engine, costs, metrics | done and tested | `src/backtest/` |
| 11 | Strategy A: variants A1, A2, A3, fiscal regime, \|t\| > 3 gated variant, diagnostics | done | `strategy_a.py`, `run_a.py`, `diagnostics.py` |
| 12 | Strategy B: carry, escalation component (D16), shocks, VIX benchmark, 27-cell grid | done | `strategy_b.py`, `run_b.py` |
| 13 | Weekend gap test | done | `weekend_test.py` |
| 14 | Robustness: placebos (a), (b), (c), leave-one-event-out, grids, sub-periods | done | `src/backtest/robustness.py` |
| 15 | Risk: betas, downside beta, episodes, labelled drawdowns, concentration, A vs B, leverage, liquidity | done | `src/risk/` |
| 16 | Figures, slide figures, README, `run_all.py` | done | `src/report/`, `results/figures/slides/`, `README.md` |
| 17 | **Preliminary** results on free data (FRED, ECB; D22) | done | `results/preliminary_free/` |
| 17b | Definitive results (Bloomberg, WRDS, official yields; D28) | done on the evening of 3 October | `results/`, `results/RESULTS.md` |
| 17c | Hourly weekend test (D24) and lead-lag (D26), Dukascopy | done: null result for D24; FX first or at the same time for D26 | `results/weekend/`, `results/leadlag/` |
| 18 | Conclusions on A and B, diagnostic of B's gap (D29), a posteriori additions and checks (D30, D31) | done; final freeze | `results/RESULTS.md`, notebook 02 section 9 |
| 19 | Summary notebooks (executed) | done | `notebooks/01_prediction_market_layer.ipynb`, `notebooks/02_strategies_tests_results.ipynb` |
| 20 | Export for the HTML page (D21) | done | `results/site_data/` |
| 21 | Submission package: confidential inputs excluded, README, pinned environment | done, not pushed yet | `.gitignore`, `README.md`, `requirements.txt` |

**Tests**: 58 of 58 pass (`.venv/Scripts/python.exe -m pytest tests/`); 34 are skipped without the confidential inputs.

**Rerun the definitive results**: `.venv/Scripts/python.exe run_all.py --stage strategies`, then `--stage robustness`, `--stage risk` and `--stage figures` (about 25 minutes, mostly the placebos). The market data are in `data/raw/market/` (a copy of the final file of the delivery) and the full delivery in `data/raw/delivery/`; neither is versioned (Bloomberg licence).

## Team decisions (3 October)
- **D14**: Strategy A in three variants, all reported.
- **D15**: time-varying fiscal regime (rolling correlation between the 10-year yield and the currency), spec 6.1 and 6.4 amended.
- **D16**: B's "level" component replaced by a stationary "escalation" component; spec 4.6, 7.3 and 7.4 amended; the literal version is kept as a variant labelled "misspecified".
- **D17 to D22** (after the review): A and B separated; hazard rates for deadline markets; √g scaling; spec header note; data for the HTML page; preliminary run on free data.
- **D23 to D27**: B's universe by the IRR rule; hourly weekend test and lead-lag; static / timing decomposition; fiscal regime finding.
- **D28 to D31** and the final freeze: market data integration, diagnostic of B, a posteriori additions, checks.

## Open items

1. **Validation**: label `ai_log/classification/validation_sheet_1.csv` to `_4.csv` (guide: `ai_log/classification/LABELLING_GUIDE.md`); do not open `validation_key.csv` before finishing.
2. **HTML page**: every series is in `results/site_data/`.
3. **AI conversations used for design and review**: `ai_log/design_conversations.md`, to be filled from the exports.

## Constraints respected

- Nothing is changed outside `GB/`.
- No LLM API call.
- No interaction with any trading account.
- The Kairos data are read-only; nothing from Kairos is included in the repository.
