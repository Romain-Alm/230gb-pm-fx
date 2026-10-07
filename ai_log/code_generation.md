# AI use log

The assignment requires that AI prompts, AI-generated code and other AI-generated material
that materially contributes to the project be documented. This log covers the code and
documents produced with Claude Code. Design and review conversations held outside Claude Code
are listed in `design_conversations.md`. `README.md` (section "AI use") summarises both.

## Tool

Claude Code (Anthropic, model Claude Opus 5.5), run interactively by the team in the project
folder, from 2026-10-03. **No LLM API is called by the pipeline**: every classification label is
produced by deterministic rules (DECISIONS D1), so no result depends on a model output at run
time. The team set the constraints at the start: no LLM API calls, no change outside the project
folder, no interaction with any trading account, read-only access to the Kairos data.

## What was AI-generated, by phase

All code below was written by Claude Code from the specification (`PROJECT_SPEC.md`,
`ASSIGNMENT.md`) and the team's decisions, then reviewed by the team. The tests in `tests/` were
written at the same time and run after every change.

### 1. Plan and prediction-market layer (2026-10-03)

| Material | Files | Decisions | Human role |
|---|---|---|---|
| Project plan and scope cuts | `progress/PLAN.md`, `DECISIONS.md` | D1 to D12 | Team chose the scope, data sources and the primary Strategy A rule |
| Data loaders and snapshot alignment | `src/data/pm_markets.py`, `src/data/pm_panel.py`, `src/common.py` | D3, D6, D7, D9, D10 | Reviewed; data tests in `tests/test_pm.py` |
| Classification rules (themes, zones, directions, buckets) | `src/pm/classify.py`, `data/manual/party_fiscal_stance.csv` | D1 | Checked on a hand-labelled random sample (`ai_log/classification/`) |
| Contract panel, inclusion rules, theme indices, coverage | `src/pm/contracts.py`, `src/pm/indices.py`, `src/pm/coverage.py` | D11, D12, D13, D18, D19 | Reviewed against spec 4.1 to 4.5; coverage decisions taken by the team (D13 to D15) |
| Geopolitical index and shocks, weekend changes | `src/pm/shocks.py`, `src/pm/weekend.py` | D16 | Team decided the escalation component (D16) |

### 2. Strategies and backtest engine (2026-10-03)

| Material | Files | Decisions | Human role |
|---|---|---|---|
| Backtest engine (timing, volatility target, caps, no-trade band, costs), metrics | `src/backtest/engine.py`, `src/backtest/metrics.py` | spec 8, 10.1 | Reviewed; engine tests |
| Strategy A (variants, fiscal regime, gated rule, diagnostics) | `src/strategies/strategy_a.py`, `src/strategies/run_a.py`, `src/strategies/diagnostics.py`, `data/manual/fiscal_regime.csv` | D2, D14, D15, D17, D25 | Team chose the variants and the regime definition |
| Strategy B (carry, escalation timing, VIX benchmark, grid) | `src/strategies/strategy_b.py`, `src/strategies/run_b.py`, `data/manual/em_exclusions.csv` | D16, D17, D23 | Team fixed the universe rule (D23) before seeing variant results |
| Preliminary run on free data | `src/data/download_free.py`, `src/data/free_market.py`, `run_preliminary_free.py` | D22 | Team authorised the downloads and supplied a FRED key (kept outside the code) |
| Pipeline entry point | `run_all.py` | | Reviewed |

### 3. Robustness, risk and intraday tests (2026-10-03)

| Material | Files | Decisions | Human role |
|---|---|---|---|
| Placebos, leave-one-event-out, grids, sub-periods, Sharpe t and bootstrap intervals | `src/backtest/robustness.py`, `src/backtest/metrics.py` | spec 10.2, scope freeze | Team asked for the bootstrap intervals |
| Risk: betas, downside beta, episodes, conditional performance, drawdowns, concentration, A vs B | `src/risk/risk.py`, `src/risk/run_risk.py` | spec 10.3, 10.4 | Reviewed |
| Hourly indices, weekend gap test, lead-lag event study | `src/pm/hourly.py`, `src/strategies/weekend_test.py`, `src/strategies/leadlag.py` | D24, D26, D27 | Team pre-registered D24 and labelled D26 exploratory |

### 4. Definitive run on the market data delivery (2026-10-03)

| Material | Files | Decisions | Human role |
|---|---|---|---|
| Loader for the delivered data (tickers, outrights, QC flags, spread smoothing, per-currency execution lag) | `src/data/market.py`, `config/market_series.yaml`, `config/config.yaml` | D28 | Team supplied the data and answered the data team's questions through D28 |
| Diagnostic of the Strategy B overlay gain | `key_month_check` in `src/strategies/run_b.py` | D29 | Labelled a posteriori |

### 5. Team review of the definitive results (2026-10-03)

| Material | Files | Decisions | Human role |
|---|---|---|---|
| B2 oil-shock tilt and Brent benchmark | `tilt_weights`, `brent_shocks` in `src/strategies/strategy_b.py`; `oil_tilt` in `run_b.py`; oil flags in `src/pm/shocks.py` | partial lifting of the scope freeze (spec 7.5) | Team specified the items and their labels |
| A1 weekly, gated 20-day rule, 0.5x cost scenario | `src/strategies/run_a.py` | D30 | Team specified the rule; horizon flagged as chosen after the diagnostic |
| Robustness of the overlay with at least 3 events per day | `min_events_filter` in `src/pm/shocks.py` | D31 | Team specified |
| Placebos of the a posteriori additions | `posthoc_a`, `posthoc_b` in `src/backtest/robustness.py` | reporting | Team asked for them |
| D30 sanity checks (phase, positions, decomposition, effective sample) | `src/strategies/d30_checks.py` | final freeze | Team specified the four checks |

### 6. Reporting and documentation (2026-10-03 to 2026-10-06)

| Material | Files | Human role |
|---|---|---|
| Results summary with reading guide and glossary | `src/report/summary_md.py`, `results/RESULTS.md` | Team review of every version |
| Analysis figures, slide figures, data for the web page | `src/report/figures_pm.py`, `src/report/figures_strategies.py`, `src/report/figures_slides.py`, `src/report/site_data.py` | Team chose the slide figures |
| Leverage and exposure report, liquidity conditioning | `src/risk/leverage.py`, `src/risk/run_risk.py` | Team asked for them (assignment: leverage, liquidity risk) |
| Notebooks | `notebooks/build_notebooks.py`, `notebooks/nb01_cells.py`, `notebooks/nb02_cells.py` | Reviewed |
| Market data request, progress notes | `progress/DATA_REQUEST.md`, `progress/*.md` | Team set the audience and the content |
| Labelling guide and split validation sheets | `ai_log/classification/LABELLING_GUIDE.md`, `validation_sheet_1.csv` to `_4.csv`, `load_labels` in `src/pm/validation.py` | The labels themselves are written by the team, without AI |
| Replication package: README, pinned requirements | `README.md`, `requirements.txt` | Reviewed |

`DECISIONS.md` entries were drafted by Claude Code from the team's decisions; the decisions
themselves (scope, rules, labels, freezes) were taken by the team.

## Reused code (not AI-generated in this project, not included in the repository)

- `src/pm/vendor/geo_registry.py` and `people_generated.py`: the geographic entity resolver of the
  Kairos cross-venue arbitrage project, copied verbatim and used by `src/pm/classify.py`.
- `src/pm/vendor/classifier_v2.py`: the Kairos main repository's rule classifier, kept as a
  reference for the theme rules (not imported).

Kairos is a separate project of the team (using other projects is allowed by the assignment). Its
code is confidential and is not included in the submitted repository (see `README.md`).

## Prompts

The project brief was the two specification files (`PROJECT_SPEC.md`, `ASSIGNMENT.md`), with
this instruction (2026-10-03): "Read the two md files, give an opinion, make a plan, and let's
start". Later steering came from the team in the same session: the constraints listed above, the
answers to the coverage gate (D13 to D16), the review blocks that led to D17 to D31 and the
freezes, and the reporting requests. Each of these is recorded as a dated entry in `DECISIONS.md`.
