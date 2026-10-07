# Quantitative results: prediction markets x FX (MFE 230GB)

Generated on 2026-10-07 by `src/report/summary_md.py` from the result files. Every number comes from the CSV/Parquet files listed in each section; nothing is typed by hand.

> **Definitive run (DECISIONS D28).** FX spot, 1-month forwards and 1-month NDFs: Bloomberg (default close, no 16:00 London fix); MSCI World net TR, S&P 500 TR, DXY, Brent: Bloomberg; VIX: Cboe via WRDS; 10-year yields: official sources (US Treasury, Bundesbank, Bank of England, MOF Japan). Signals are taken at the 16:00 London snapshot and executed at the next close: the same day's New York close for the G10 and Latin America, the next day's Asian close for KRW. Costs: half of the delivered forward bid/ask spread, causal rolling median over 20 days.

Sample: 2024-01-01 to 2026-09-24; in-sample 2024-2025, out-of-sample from 2026-01-01. Signals at the 16:00 London snapshot, close-to-close returns (Bloomberg), statistics annualised over 252 days. Returns and volatility are in percent.

## 0. Reading guide

- **Project**: two currency strategies built on prediction markets (Polymarket, Kalshi). A trades the G10 against the dollar; B is an EM carry with a geopolitical overlay. Course MFE 230GB, presentation on October 8, 2026.
- **Status of the results**: every line has a status (glossary below). "Pre-registered" = rule fixed before any backtest. "A posteriori" = added after seeing the definitive results: to be presented as such. Identifiers D1 to D31 refer to `DECISIONS.md`.
- **Periods**: "2024-2025" = in-sample (estimation period of the gated rules); "2026 (OOS)" = out-of-sample, from 2026-01-01 to 2026-09-24; "2024-2026" = full sample.
- **Units**: annualised Sharpe (252 days); Sharpe t = Sharpe x square root of the number of years; 90% CI by block bootstrap (blocks of 20 days, 1000 draws); annualised returns and volatilities in percent; "points" = sum of daily returns in percentage points.
- **Sources**: tables in `results/strategy_a/`, `results/strategy_b/`, `results/robustness/`, `results/risk/`, `results/weekend/`, `results/leadlag/`; figures in `results/figures/`; data for a web page in `results/site_data/`; step-by-step explanations in `notebooks/02_strategies_tests_results.ipynb`.
- **Scope frozen** (final freeze of 2026-10-03, `DECISIONS.md`): no rule or variant will be added.
- **Slide figures**: `results/figures/slides/` (1920 x 1080, PNG and SVG, no in-figure title; data in `results/site_data/slide_*.csv`).
- **Pending**: (1) hand validation of the classification: label the four files `ai_log/classification/validation_sheet_1.csv` to `_4.csv` (50 rows each; guide: `LABELLING_GUIDE.md`), then run `.venv/Scripts/python.exe -m src.pm.validation score` (accuracy per field: theme, zone, direction; shown automatically in section 1); (2) HTML page (data ready in `results/site_data/`); (3) list of the AI conversations used for design and review (`ai_log/design_conversations.md`, to be filled from the exports).


**Glossary of strategies**:


| name | description | status |
|---|---|---|
| A1_theory_with_dollar | A: US signal (MONETARY, FISCAL) with theory-given signs, G10 basket against USD, daily rebalancing | primary, pre-registered (D2, D14) |
| A1_theory_dollar_neutral | A1 without the dollar leg: zero by construction (same signal on every pair) | pre-registered |
| A2_theory_with_dollar / _dollar_neutral | A with every G10 cell at the USD 10k threshold, each active when it has contracts | variant declared before any backtest (D14) |
| A1+S, A2+S | A1 or A2 plus geopolitics, tariffs and spillovers (the contracts of B's index) | variants declared before any backtest (D14, D17) |
| A3, A3+S | cells that pass the spec's coverage rule; identical to A1 and A1+S | declared (D14) |
| *_gated_frozen | spec rule: 1-day regression on 2024-2025, themes with t > 3 and the right sign, frozen coefficients | spec 6.5 (ex ante rule) |
| *_D12 | indices in demeaned probabilities instead of hazard rates | declared variant (D12, D18) |
| *_gross | same strategy, before costs | information |
| A1_theory_with_dollar_weekly | A1 rebalanced on the last trading day of each week | a posteriori (freeze lifted, 2026-10-03) |
| A1_gated20_frozen, A2_gated20_frozen | gated rule at 20 days, estimated on 2024-2025, frozen, rebalanced every 20 days | a posteriori, horizon chosen after the full-sample diagnostic (D30) |
| *_cost0.5x | costs at 0.5x the Bloomberg composite half-spread | a posteriori scenario; the primary result stays at 1x |
| base_carry | B: EM carry, IRR 12-13 universe (BRL, MXN, COP, CLP, ZAR, KRW), top versus bottom tercile, monthly | pre-registered (spec 7.2, D23) |
| pm_timed | base carry with the PM geopolitical overlay (monthly escalation, cut on a confirmed shock) | pre-registered (spec 7.4, D16); to be read with D29 |
| vix_timed | same overlay driven by VIX | ex ante benchmark |
| pm_timed_level_misspecified | literal spec rule (index level), misspecified | reported for transparency (D16) |
| pm_timed_prob_index_D12 | overlay computed on the probability-based index | declared variant (D12) |
| *__coarse12, *__previous, *_cap20 | other EM universes and a 20% cap per currency | declared variants (D23) |
| pm_timed_without_event | overlay rebuilt without the event that triggers the cut of the best month | a posteriori diagnostic (D29) |
| b2_oil_tilt | B2: an "oil" shock does not cut the carry, it adds an exporters-versus-importers tilt | mechanism from spec 7.5; details fixed a posteriori |
| b2_brent_tilt | B2 triggered by a Brent rise of more than 2 standard deviations | a posteriori benchmark |
| pm_timed_min3events | overlay with at least 3 distinct events per index day | a posteriori robustness (D31) |

## Summary

**1. Prediction markets move with currencies, not before them.** 
Contemporaneous, US MONETARY: t = 4.0; predictive at 1 day: t = 0.7 (MONETARY) and 0.9 (FISCAL). 
Pre-registered weekend gap test (D24): maximum |t| 1.3, null result. 
Hourly lead-lag (D26): the dollar moves first or at the same time (section 7b).


**2. Strategy A: real content before costs, eaten by costs.** A1 net 0.43 (gross 0.88, CI [-0.24, 1.67]); A2 net 0.81 (gross 1.43, t 2.4). The spec's gated rule does not trade. A posteriori: weekly 0.75; costs at 0.5x: A1 0.65, A2 1.12; gated rule at 20 days (D30, horizon chosen after the fact): 1.51, of which 2.46 in 2026 (beats 99% of placebos (a)). D30 fails the checks of section 4: averaged over the 20 possible rebalancing start dates, its 2026 Sharpe is only 0.22, and the effective-sample regression is not significant. It is an exploratory lead, not a result.


**3. Strategy B: the carry works, the PM geopolitical overlay adds nothing.** Base carry 1.25 (t 2.1); with the PM overlay 1.30, drawdown -8.0% versus -14.0%. But the whole gap comes from 2024-06: without the event `will-china-invade-taiwan-in-2024` (1 contract), the overlay falls to 1.00 (D29). With at least 3 events per day (D31): 0.89. Oil tilt B2: 1.37, Brent-triggered: 1.41; B2's lead comes from the same month (section 5). VIX timing: 1.12. 18 of the 19 confirmed shocks are classified as "oil": B2 almost always tilts instead of cutting.


**4. Risk.** The 2024-2026 carry is long BRL, MXN and COP against KRW and CLP. It has a positive Brent beta (t = 4.5) and no equity beta; the Brent beta comes mostly from the short legs (KRW and CLP fall when oil rises) and from COP, BRL and MXN having a Brent beta close to zero over the period (figure `slide_b_composition`). Middle East escalation helps it instead of crashing it, hence the failure of the overlay. Crash risk shows in the long history (section 5). A and B are distinct (daily correlation A1 / B: -0.04).


## Key numbers

- Cells that pass the coverage rule: 3 (US/MONETARY, GLOBAL/GEOPOLITICS, US/FISCAL_POLITICAL).

- **A1 (dollar leg)**, net Sharpe: 0.49 in 2024-2025, 0.28 in 2026; gross over 2024-2026: 0.88; annual turnover 133.

- **A2 (relaxed coverage)**, net Sharpe: 0.71 in 2024-2025, 1.08 in 2026; spec gated rule: no theme passes |t| > 3.

- **A, a posteriori additions** (partial lifting of the freeze, see `DECISIONS.md`): weekly A1, net Sharpe 0.75 (turnover 63); gated rule at 20 days (D30, horizon chosen after the full-sample diagnostic): A1 net 1.51 over 2024-2026 and 2.46 in 2026; costs at 0.5x: A1 0.65, A2 1.12.

- **B, EM carry (IRR 12-13 universe) with a PM geopolitical overlay**, net Sharpe 2024-2026: base carry 1.25; with the PM overlay 1.30; without the event `will-china-invade-taiwan-in-2024` that triggers the cut of 2024-06 (D29): 1.00, drawdown -13.1%.

- **B, the three versions**, net Sharpe 2024-2026: base carry 1.25, PM-timed 1.30, VIX-timed 1.12; maximum drawdown: -14.0%, -8.0%, -11.6%.

- **A1, decomposition (D25)**: the timing part carries most of the gross P&L (see section 4).

- **Downside beta** (equities): base carry 0.00, PM-timed 0.04, VIX-timed -0.05.

- **Correlation A1 / B** (daily returns): -0.04.



## 1. Prediction-market data

| platform | markets with trades | market-days | volume (USD bn) |
|---|---|---|---|
| kalshi | 50,281 | 906,321 | 2.28 |
| polymarket | 29,922 | 967,232 | 8.88 |


**Classification (rules, D1)**: candidate macro markets with trades, by theme. "Usable" = defined direction or partition bucket.


| theme | markets | events | usable |
|---|---|---|---|
| OTHER | 50,499 | 10,162 | 0 |
| FISCAL_POLITICAL | 16,902 | 4,076 | 1,616 |
| GEOPOLITICS | 5,301 | 1,629 | 3,504 |
| INFLATION | 3,860 | 559 | 3,170 |
| MONETARY | 2,818 | 541 | 2,211 |
| TRADE_TARIFFS | 823 | 275 | 775 |


Contracts in the panel: 9,103; by unit: prob 5,818, hazard 2,974, bp 197, pp 98, pct 16 (hazard = deadline markets valued as hazard rates, D18).


**Hand validation**: 200 events to label (`ai_log/classification/validation_sheet_1.csv` to `_4.csv`), score not computed yet.


## 2. Coverage table (rule: at least 60% of weekdays covered in 2024-2025)


| zone | theme | coverage 2024-25 | coverage 2026 | contracts | events | volume (USD m) | kept |
|---|---|---|---|---|---|---|---|
| US | MONETARY | 93.9% | 100.0% | 110 | 87 | 561.43 | yes |
| GLOBAL | GEOPOLITICS | 76.7% | 100.0% | 649 | 339 | 555.53 | yes |
| US | FISCAL_POLITICAL | 68.5% | 100.0% | 265 | 123 | 1,187 | yes |
| US | GEOPOLITICS | 52.6% | 100.0% | 298 | 105 | 249.51 | no |
| CN | GEOPOLITICS | 33.1% | 100.0% | 9 | 9 | 19.23 | no |
| US | TRADE_TARIFFS | 30.8% | 24.1% | 59 | 43 | 8.43 | no |
| US | INFLATION | 25.0% | 27.7% | 64 | 39 | 9.01 | no |
| KR | FISCAL_POLITICAL | 22.6% | 0.0% | 17 | 11 | 25.71 | no |
| CN | TRADE_TARIFFS | 19.9% | 4.2% | 14 | 14 | 2.45 | no |
| EA | FISCAL_POLITICAL | 7.6% | 17.8% | 11 | 8 | 2.36 | no |
| UK | FISCAL_POLITICAL | 7.6% | 55.0% | 22 | 11 | 10.44 | no |
| MX | TRADE_TARIFFS | 6.1% | 0.0% | 7 | 7 | 0.50 | no |
| CA | TRADE_TARIFFS | 5.0% | 0.0% | 6 | 6 | 0.39 | no |
| KR | TRADE_TARIFFS | 4.2% | 0.0% | 1 | 1 | 0.22 | no |
| JP | MONETARY | 3.1% | 19.4% | 7 | 7 | 1.21 | no |


Same table at the USD 10k threshold (robustness), first 10 cells:


| zone | theme | coverage 2024-25 | coverage 2026 | kept |
|---|---|---|---|---|
| US | MONETARY | 99.8% | 100.0% | yes |
| GLOBAL | GEOPOLITICS | 96.9% | 100.0% | yes |
| US | FISCAL_POLITICAL | 91.4% | 100.0% | yes |
| CN | GEOPOLITICS | 74.6% | 100.0% | yes |
| US | GEOPOLITICS | 64.2% | 100.0% | yes |
| US | TRADE_TARIFFS | 53.0% | 63.9% | no |
| US | INFLATION | 53.0% | 85.9% | no |
| CN | TRADE_TARIFFS | 36.7% | 31.9% | no |
| KR | FISCAL_POLITICAL | 34.4% | 24.1% | no |
| UK | FISCAL_POLITICAL | 31.4% | 74.9% | no |


## 3. Theme indices and shocks

| cell | active days | average contracts per day | average drift (sd per day) | t of the drift | 5 largest moves |
|---|---|---|---|---|---|
| US/MONETARY | 938 | 5.13 | 0.06 | 2.12 | 2024-08-02 (-5.0), 2025-07-31 (+4.5), 2025-08-01 (-4.9), 2025-11-21 (-4.8), 2026-06-18 (+4.5) |
| US/FISCAL_POLITICAL | 753 | 7.83 | 0.06 | 1.44 | 2025-01-06 (+5.0), 2025-03-09 (+5.0), 2025-04-30 (-5.0), 2025-09-28 (-5.0), 2026-01-25 (+4.8) |
| GLOBAL/GEOPOLITICS | 815 | 13.45 | 0.03 | 0.71 | 2024-05-24 (+5.0), 2024-06-02 (+4.3), 2024-09-17 (+4.1), 2024-09-19 (+4.5), 2024-09-30 (+5.0) |
| GLOBAL/GEO_TRADE | 815 | 14.19 | 0.03 | 0.80 | 2024-05-24 (+5.0), 2024-06-02 (+4.3), 2024-09-17 (+4.1), 2024-09-19 (+4.5), 2024-09-30 (+5.0) |


Moves of ±5.0 are winsorised. In 2024 the geopolitical cell often rests on one or two contracts, so its largest moves of that period carry little information.


Comparison (D18): without hazard rates, the drift of US MONETARY would be 0.079 sd per day (t = 2.9).


**B's geopolitical index**: 23 raw shocks, 19 confirmed. Month-ends with an escalation z-score ≥ 1: 12% (≥ 2: 9%); with the original misspecified version (level, D16): 45%.


| date | change (sd) | change 4 h before | contracts | volume (USD) |
|---|---|---|---|---|
| 2024-09-19 | 4.54 | 1.62 | 1 | 69,034 |
| 2024-09-30 | 5.00 | 5.00 | 1 | 80,637 |
| 2024-12-30 | 2.46 | 2.11 | 3 | 143,627 |
| 2025-03-12 | 2.63 | 2.26 | 8 | 1,930,671 |
| 2025-04-20 | 1.62 | 1.60 | 13 | 650,656 |
| 2025-05-15 | 2.13 | 1.45 | 14 | 402,897 |
| 2025-06-01 | 1.81 | 1.66 | 12 | 401,037 |
| 2025-06-11 | 1.88 | 1.55 | 11 | 487,427 |
| 2025-06-12 | 3.03 | 3.10 | 10 | 855,561 |
| 2025-06-13 | 3.34 | 3.39 | 8 | 953,016 |
| 2025-06-17 | 3.16 | 3.02 | 17 | 2,270,836 |
| 2025-06-26 | 2.77 | 2.98 | 17 | 1,413,088 |
| 2025-07-25 | 2.66 | 1.73 | 6 | 784,454 |
| 2025-10-01 | 2.61 | 2.71 | 13 | 450,738 |
| 2026-01-13 | 2.81 | 1.71 | 31 | 3,182,144 |
| 2026-02-18 | 2.94 | 1.95 | 24 | 1,880,987 |
| 2026-02-27 | 1.72 | 1.56 | 39 | 5,756,240 |
| 2026-04-02 | 1.84 | 1.86 | 34 | 3,283,704 |
| 2026-09-20 | 1.88 | 1.73 | 17 | 827,194 |


**Weekend changes** (Friday 17:00 to Sunday 17:00 New York):


| cell | weekends | 4 largest (Friday, sd) |
|---|---|---|
| GLOBAL/GEOPOLITICS | 118 | 2026-02-27 (+4.6), 2024-10-04 (+4.1), 2025-06-20 (+4.0), 2024-05-24 (-3.7) |
| US/FISCAL_POLITICAL | 107 | 2025-09-19 (+4.9), 2026-01-23 (+4.1), 2024-07-12 (+2.9), 2024-11-01 (-2.7) |
| US/MONETARY | 136 | 2024-09-06 (-1.9), 2026-07-24 (-1.6), 2026-06-19 (-1.2), 2026-02-06 (-1.0) |


## 4. Strategy A (G10)


Theory-signed rule (D2), net of costs except "_gross". A3 = A1 and A3+S = A1+S by construction (D14, D17); the dollar-neutral versions of A1 and A3 are zero (same signal on every pair). "gated" = the spec rule (|t| > 3 on 2024-2025, frozen coefficients).


| strategy | period | Sharpe | Sharpe t | 90% CI of the Sharpe (bootstrap) | annual return | annual vol | max drawdown | positive days | skew | annual turnover | annual cost |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A1_theory_with_dollar | 2024-2025 | 0.49 | 0.70 | [-0.47, 1.56] | 5.0% | 10.4% | -13.5% | 48.6% | -0.09 | 115.37 | 4.2% |
| A1_theory_with_dollar | 2024-2026 | 0.43 | 0.72 | [-0.70, 1.22] | 4.5% | 10.5% | -14.1% | 49.0% | -0.13 | 132.57 | 4.7% |
| A1_theory_with_dollar | 2026 (OOS) | 0.28 | 0.24 | [-2.91, 1.89] | 3.0% | 10.8% | -14.1% | 50.3% | -0.22 | 179.65 | 6.1% |
| A1_theory_with_dollar_gross | 2024-2025 | 0.89 | 1.29 | [-0.07, 1.96] | 9.2% | 10.3% | -11.7% | 49.3% | -0.03 |  |  |
| A1_theory_with_dollar_gross | 2024-2026 | 0.88 | 1.48 | [-0.24, 1.67] | 9.2% | 10.4% | -11.7% | 50.3% | -0.07 |  |  |
| A1_theory_with_dollar_gross | 2026 (OOS) | 0.85 | 0.74 | [-2.25, 2.49] | 9.1% | 10.7% | -11.6% | 52.9% | -0.19 |  |  |
| A2_theory_with_dollar | 2024-2025 | 0.71 | 1.02 | [-0.17, 1.68] | 7.2% | 10.2% | -11.9% | 49.1% | 0.14 | 173.18 | 6.2% |
| A2_theory_with_dollar | 2024-2026 | 0.81 | 1.36 | [-0.25, 1.60] | 8.2% | 10.2% | -11.9% | 50.1% | -0.0013 | 188.28 | 6.3% |
| A2_theory_with_dollar | 2026 (OOS) | 1.08 | 0.94 | [-1.87, 2.29] | 11.1% | 10.3% | -11.8% | 52.9% | -0.39 | 229.62 | 6.7% |
| A2_theory_with_dollar_gross | 2024-2025 | 1.31 | 1.89 | [0.47, 2.35] | 13.4% | 10.2% | -10.1% | 51.1% | 0.19 |  |  |
| A2_theory_with_dollar_gross | 2024-2026 | 1.43 | 2.41 | [0.37, 2.25] | 14.6% | 10.2% | -10.1% | 52.2% | 0.04 |  |  |
| A2_theory_with_dollar_gross | 2026 (OOS) | 1.75 | 1.53 | [-1.19, 2.88] | 17.8% | 10.2% | -9.4% | 55.5% | -0.38 |  |  |
| A2_theory_dollar_neutral | 2024-2025 | -1.14 | -1.65 | [-2.66, 0.52] | -6.0% | 5.3% | -16.9% | 34.2% | 0.15 | 200.33 | 6.5% |
| A2_theory_dollar_neutral | 2024-2026 | -0.95 | -1.60 | [-2.22, 0.30] | -5.3% | 5.6% | -21.9% | 38.2% | -0.0006 | 230.88 | 7.1% |
| A2_theory_dollar_neutral | 2026 (OOS) | -0.53 | -0.46 | [-2.43, 1.39] | -3.4% | 6.4% | -8.2% | 49.2% | -0.25 | 314.56 | 8.6% |
| A1+S_theory_with_dollar | 2024-2025 | -0.11 | -0.16 | [-1.18, 0.96] | -1.1% | 9.9% | -17.8% | 48.0% | 0.04 | 175.89 | 6.7% |
| A1+S_theory_with_dollar | 2024-2026 | -0.21 | -0.35 | [-1.35, 0.55] | -2.1% | 9.9% | -17.8% | 47.9% | -0.02 | 202.55 | 7.6% |
| A1+S_theory_with_dollar | 2026 (OOS) | -0.48 | -0.42 | [-3.16, 1.10] | -4.7% | 9.8% | -12.8% | 47.6% | -0.19 | 275.54 | 9.9% |
| A1+S_theory_dollar_neutral | 2024-2025 | -0.14 | -0.20 | [-1.49, 1.02] | -0.9% | 6.4% | -10.9% | 37.1% | 2.06 | 184.48 | 8.0% |
| A1+S_theory_dollar_neutral | 2024-2026 | -0.71 | -1.20 | [-1.88, 0.38] | -4.5% | 6.3% | -19.7% | 40.3% | 1.51 | 218.46 | 8.9% |
| A1+S_theory_dollar_neutral | 2026 (OOS) | -2.48 | -2.16 | [-3.81, -0.85] | -14.3% | 5.7% | -10.6% | 49.2% | -0.64 | 311.50 | 11.4% |
| A2+S_theory_with_dollar | 2024-2025 | -0.16 | -0.22 | [-1.11, 0.89] | -1.5% | 9.9% | -19.3% | 46.7% | 0.27 | 215.64 | 7.5% |
| A2+S_theory_with_dollar | 2024-2026 | 0.23 | 0.39 | [-0.89, 1.10] | 2.3% | 9.9% | -19.3% | 48.5% | 0.30 | 223.63 | 7.6% |
| A2+S_theory_with_dollar | 2026 (OOS) | 1.28 | 1.11 | [-1.42, 2.95] | 12.7% | 9.9% | -10.4% | 53.4% | 0.40 | 245.54 | 7.8% |
| A2+S_theory_dollar_neutral | 2024-2025 | -1.51 | -2.18 | [-2.48, -0.59] | -10.4% | 6.8% | -20.8% | 40.3% | 1.45 | 288.63 | 10.4% |
| A2+S_theory_dollar_neutral | 2024-2026 | -1.67 | -2.81 | [-2.56, -0.83] | -11.1% | 6.7% | -29.0% | 41.2% | 1.15 | 300.93 | 10.5% |
| A2+S_theory_dollar_neutral | 2026 (OOS) | -2.16 | -1.88 | [-3.43, -0.01] | -13.2% | 6.1% | -10.5% | 43.5% | -0.02 | 334.63 | 10.6% |
| A1_theory_with_dollar_D12 | 2024-2025 | -0.48 | -0.69 | [-1.66, 0.69] | -5.0% | 10.4% | -21.8% | 45.7% | -0.52 |  |  |
| A1_theory_with_dollar_D12 | 2024-2026 | -0.47 | -0.79 | [-1.56, 0.43] | -4.9% | 10.5% | -21.8% | 45.8% | -0.38 |  |  |
| A1_theory_with_dollar_D12 | 2026 (OOS) | -0.44 | -0.38 | [-2.48, 1.21] | -4.8% | 10.8% | -13.4% | 46.1% | -0.02 |  |  |
| A1_gated_frozen | 2024-2025 |  |  |  | 0.0% | 0.0% | 0.0% | 0.0% | 0.00 |  |  |
| A1_gated_frozen | 2024-2026 |  |  |  | 0.0% | 0.0% | 0.0% | 0.0% | 0.00 |  |  |
| A1_gated_frozen | 2026 (OOS) |  |  |  | 0.0% | 0.0% | 0.0% | 0.0% | 0.00 |  |  |
| A2_gated_frozen | 2024-2025 |  |  |  | 0.0% | 0.0% | 0.0% | 0.0% | 0.00 |  |  |
| A2_gated_frozen | 2024-2026 |  |  |  | 0.0% | 0.0% | 0.0% | 0.0% | 0.00 |  |  |
| A2_gated_frozen | 2026 (OOS) |  |  |  | 0.0% | 0.0% | 0.0% | 0.0% | 0.00 |  |  |


**Estimation of the gated rule (2024-2025)**: no theme has t > 3 with the right sign, so the rule does not trade.


| variant | component | coef | t | n_obs | passes the gate |
|---|---|---|---|---|---|
| A1 | MONETARY | -0.0000 | -0.19 | 4,665 | no |
| A1 | FISCAL_POLITICAL | 0.0002 | 1.60 | 4,665 | no |
| A2 | MONETARY | 0.0001 | 0.39 | 4,665 | no |
| A2 | INFLATION | -0.0002 | -0.84 | 4,665 | no |
| A2 | FISCAL_POLITICAL | 0.0002 | 1.68 | 4,665 | no |


**A posteriori additions (partial lifting of the scope freeze, 2026-10-03; nothing is pre-registered)**:
- `A1_theory_with_dollar_weekly`: A1 rebalanced on the last trading day of each week.
- `*_gated20_frozen` (D30): gated rule at the 20-day horizon. **The horizon was chosen after seeing the 20-day diagnostic on the full sample.** Estimation on 2024-2025 only (targets ending inside the training window, Driscoll-Kraay with a 20-day bandwidth), components with the right sign and t > 3, frozen coefficients, rebalancing every 20 trading days, test on 2026.
- `*_cost0.5x`: costs at 0.5x the Bloomberg composite half-spread (the primary result stays at 1x).


| strategy | period | Sharpe | Sharpe t | 90% CI of the Sharpe (bootstrap) | annual return | annual vol | max drawdown | positive days | skew | annual turnover | annual cost |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A1_theory_with_dollar_weekly | 2024-2025 | 0.87 | 1.25 | [-0.31, 1.81] | 8.8% | 10.1% | -9.1% | 49.5% | -0.06 | 57.05 | 2.1% |
| A1_theory_with_dollar_weekly | 2024-2026 | 0.75 | 1.26 | [-0.31, 1.59] | 7.7% | 10.3% | -11.2% | 50.8% | -0.09 | 62.76 | 2.2% |
| A1_theory_with_dollar_weekly | 2026 (OOS) | 0.44 | 0.38 | [-1.91, 1.90] | 4.8% | 10.9% | -11.2% | 54.5% | -0.15 | 78.37 | 2.7% |
| A1_theory_with_dollar_weekly_gross | 2024-2025 | 1.08 | 1.55 | [-0.13, 2.02] | 10.9% | 10.1% | -8.3% | 49.9% | -0.03 |  |  |
| A1_theory_with_dollar_weekly_gross | 2024-2026 | 0.97 | 1.63 | [-0.08, 1.84] | 10.0% | 10.3% | -10.3% | 51.5% | -0.05 |  |  |
| A1_theory_with_dollar_weekly_gross | 2026 (OOS) | 0.69 | 0.60 | [-1.64, 2.15] | 7.4% | 10.8% | -10.3% | 56.0% | -0.09 |  |  |
| A1_gated20_frozen | 2024-2025 | 1.16 | 1.68 | [0.26, 2.01] | 12.5% | 10.7% | -6.4% | 49.7% | 0.34 | 22.27 | 0.8% |
| A1_gated20_frozen | 2024-2026 | 1.51 | 2.54 | [0.64, 2.21] | 16.2% | 10.7% | -6.4% | 51.7% | 0.21 | 23.51 | 0.9% |
| A1_gated20_frozen | 2026 (OOS) | 2.46 | 2.14 | [0.74, 3.76] | 26.3% | 10.7% | -5.2% | 57.1% | -0.15 | 26.90 | 0.9% |
| A1_gated20_frozen_gross | 2024-2025 | 1.24 | 1.79 | [0.33, 2.10] | 13.3% | 10.7% | -6.3% | 49.9% | 0.33 |  |  |
| A1_gated20_frozen_gross | 2024-2026 | 1.59 | 2.68 | [0.71, 2.30] | 17.1% | 10.7% | -6.3% | 51.8% | 0.20 |  |  |
| A1_gated20_frozen_gross | 2026 (OOS) | 2.54 | 2.21 | [0.83, 3.86] | 27.3% | 10.7% | -5.1% | 57.1% | -0.16 |  |  |
| A2_gated20_frozen | 2024-2025 |  |  |  | 0.0% | 0.0% | 0.0% | 0.0% | 0.00 | 0.00 | 0.0% |
| A2_gated20_frozen | 2024-2026 |  |  |  | 0.0% | 0.0% | 0.0% | 0.0% | 0.00 | 0.00 | 0.0% |
| A2_gated20_frozen | 2026 (OOS) |  |  |  | 0.0% | 0.0% | 0.0% | 0.0% | 0.00 | 0.00 | 0.0% |
| A1_theory_with_dollar_cost0.5x | 2024-2025 | 0.69 | 0.99 | [-0.27, 1.77] | 7.1% | 10.3% | -12.6% | 48.9% | -0.06 | 115.37 | 2.1% |
| A1_theory_with_dollar_cost0.5x | 2024-2026 | 0.65 | 1.10 | [-0.48, 1.44] | 6.8% | 10.4% | -12.8% | 49.6% | -0.10 | 132.57 | 2.3% |
| A1_theory_with_dollar_cost0.5x | 2026 (OOS) | 0.56 | 0.49 | [-2.59, 2.20] | 6.0% | 10.7% | -12.8% | 51.3% | -0.20 | 179.65 | 3.0% |
| A2_theory_with_dollar_cost0.5x | 2024-2025 | 1.01 | 1.46 | [0.16, 2.00] | 10.3% | 10.2% | -11.1% | 50.5% | 0.16 | 173.18 | 3.1% |
| A2_theory_with_dollar_cost0.5x | 2024-2026 | 1.12 | 1.88 | [0.05, 1.93] | 11.4% | 10.2% | -11.1% | 51.5% | 0.02 | 188.28 | 3.2% |
| A2_theory_with_dollar_cost0.5x | 2026 (OOS) | 1.41 | 1.23 | [-1.53, 2.59] | 14.4% | 10.2% | -10.6% | 54.5% | -0.38 | 229.62 | 3.4% |
| A1_theory_with_dollar_weekly_cost0.5x | 2024-2025 | 0.97 | 1.40 | [-0.21, 1.93] | 9.9% | 10.1% | -8.7% | 49.5% | -0.04 | 57.05 | 1.0% |
| A1_theory_with_dollar_weekly_cost0.5x | 2024-2026 | 0.86 | 1.45 | [-0.20, 1.72] | 8.9% | 10.3% | -10.7% | 50.8% | -0.07 | 62.76 | 1.1% |
| A1_theory_with_dollar_weekly_cost0.5x | 2026 (OOS) | 0.56 | 0.49 | [-1.78, 2.01] | 6.1% | 10.8% | -10.7% | 54.5% | -0.12 | 78.37 | 1.3% |
| A1_gated20_frozen_cost0.5x | 2024-2025 | 1.20 | 1.73 | [0.30, 2.05] | 12.9% | 10.7% | -6.4% | 49.9% | 0.33 | 22.27 | 0.4% |
| A1_gated20_frozen_cost0.5x | 2024-2026 | 1.55 | 2.61 | [0.68, 2.26] | 16.6% | 10.7% | -6.4% | 51.8% | 0.20 | 23.51 | 0.4% |
| A1_gated20_frozen_cost0.5x | 2026 (OOS) | 2.50 | 2.18 | [0.79, 3.81] | 26.8% | 10.7% | -5.1% | 57.1% | -0.16 | 26.90 | 0.5% |


**Estimation of the 20-day gated rule (D30, 2024-2025)**:


| variant | component | coef | t | n_obs | passes the gate |
|---|---|---|---|---|---|
| A1 | MONETARY | -0.0006 | -0.35 | 4,158 | no |
| A1 | FISCAL_POLITICAL | 0.0036 | 3.15 | 4,158 | yes |
| A2 | MONETARY | -0.0000 | -0.02 | 4,158 | no |
| A2 | INFLATION | -0.0039 | -2.15 | 4,158 | no |
| A2 | FISCAL_POLITICAL | 0.0031 | 2.83 | 4,158 | no |


**Checks of D30 (final review; no rule changed)**

*1. Phase robustness.* The published rule rebalances on trading days 0, 20, 40… of the sample. Same frozen rule, for the 20 possible start dates:


| period | net Sharpe, published phase | mean of the 20 phases | min | max | phases with Sharpe > 0 | rank of the published phase |
|---|---|---|---|---|---|---|
| 2024-2026 | 1.51 | 0.42 | -0.54 | 1.51 | 17 / 20 | 1 / 20 |
| 2024-2025 | 1.16 | 0.52 | -0.16 | 1.16 | 19 / 20 | 1 / 20 |
| 2026 (OOS) | 2.46 | 0.22 | -2.07 | 2.46 | 12 / 20 | 1 / 20 |


B2 and its Brent version do not rebalance on a fixed cycle: the base carry is rebuilt at each calendar month-end and the overlay is daily. The phase test therefore does not apply.


*2. Positions* (published phase; USD position = minus the sum of the pair weights, > 0 = long USD):


| period | days | long USD | short USD | flat | sign changes | rebalances |
|---|---|---|---|---|---|---|
| 2024-2025 | 523 | 54% | 43% | 4% | 11 | 27 |
| 2026 | 191 | 49% | 51% | 0% | 5 | 9 |


Monthly P&L in 2026 (sum of daily returns):


| month | net | gross | USD position at month-end |
|---|---|---|---|
| 2026-01 | +3.0% | +3.2% | long USD (+2.01) |
| 2026-02 | +1.3% | +1.4% | short USD (-1.48) |
| 2026-03 | -4.1% | -4.1% | short USD (-1.42) |
| 2026-04 | +2.6% | +2.7% | long USD (+1.69) |
| 2026-05 | +1.5% | +1.5% | long USD (+1.69) |
| 2026-06 | +6.1% | +6.1% | long USD (+2.03) |
| 2026-07 | +2.7% | +2.8% | short USD (-2.13) |
| 2026-08 | +1.1% | +1.1% | short USD (-2.05) |
| 2026-09 | +5.8% | +5.9% | long USD (+2.02) |


*3. Static / timing decomposition* (method of D25, gross P&L), and two ex post benchmarks that use 2026 information: the 2026 average position held all year, and the 2026 average direction (short USD) held at full size:


| part | period | Sharpe | annual return | annual vol |
|---|---|---|---|---|
| total | 2024-2025 | 1.24 | 13.3% | 10.7% |
| total | 2026 | 2.54 | 27.3% | 10.7% |
| static | 2024-2025 | 0.09 | 0.2% | 1.7% |
| static | 2026 | 0.75 | 1.2% | 1.6% |
| timing | 2024-2025 | 1.21 | 13.2% | 10.8% |
| timing | 2026 | 2.41 | 26.1% | 10.8% |
| ex_post_2026_average_position | 2026 | -1.89 | -0.2% | 0.1% |
| ex_post_2026_average_direction | 2026 | -0.49 | -3.2% | 6.5% |


*4. Effective sample*: a single series (G10 dollar basket), non-overlapping 20-day returns, OLS with small-sample t. "Published phase" = start on day 0; the other columns summarise the 20 phases.


| period | n (published phase) | t (published phase) | mean t (20 phases) | t min | t max | phases with t > 2 |
|---|---|---|---|---|---|---|
| 2024-2025 | 23 | 1.34 | 1.36 | 0.57 | 2.17 | 1 / 20 |
| 2026 | 8 | 0.72 | 0.78 | -0.35 | 2.84 | 1 / 20 |


*Reading.* In 2026 the published phase ranks 1 of 20 possible start dates; the average over phases (0.22 in 2026) gives a more credible order of magnitude. The published start (day 0) was not chosen, but the published number owes much to phase luck. The P&L comes from timing (alternately long and short USD), not from a dollar direction held through the year. On the effective sample (one observation every 20 days) the relation is not significant. D30 is to be presented as an exploratory lead, not as a result.


**Leverage and exposure** (gross exposure = sum of absolute weights, in multiples of capital; net USD exposure = minus the sum of the weights, > 0 = long USD; caps measured on the daily targets, before the no-trade band):


| strategy | period | mean gross | median gross | gross 95th percentile | max gross | mean |net USD| | days long USD | realised vol (target 10%) | 3x cap binds | 30% per-pair cap binds |
|---|---|---|---|---|---|---|---|---|---|---|
| A1_theory_with_dollar | 2024-2025 | 1.69 | 1.73 | 2.25 | 3.17 | 1.69 | 60.2% | 10.4% | 0.8% | 13.9% |
| A1_theory_with_dollar | 2026 | 1.84 | 1.88 | 2.38 | 2.47 | 1.84 | 60.2% | 10.8% | 0.0% | 30.4% |
| A1_theory_with_dollar | 2024-2026 | 1.73 | 1.78 | 2.28 | 3.17 | 1.73 | 60.2% | 10.5% | 0.6% | 18.4% |
| A2_theory_with_dollar | 2024-2025 | 1.79 | 1.81 | 2.65 | 3.16 | 1.64 | 62.3% | 10.2% | 3.8% | 27.0% |
| A2_theory_with_dollar | 2026 | 2.09 | 2.03 | 3.00 | 3.15 | 1.63 | 64.9% | 10.3% | 13.1% | 45.5% |
| A2_theory_with_dollar | 2024-2026 | 1.87 | 1.86 | 3.00 | 3.16 | 1.64 | 63.0% | 10.2% | 6.3% | 32.1% |
| A1_theory_with_dollar_weekly | 2024-2025 | 1.67 | 1.70 | 2.24 | 2.38 | 1.67 | 55.3% | 10.1% | 0.0% | 13.0% |
| A1_theory_with_dollar_weekly | 2026 | 1.84 | 1.87 | 2.40 | 2.47 | 1.84 | 68.6% | 10.9% | 0.0% | 33.3% |
| A1_theory_with_dollar_weekly | 2024-2026 | 1.71 | 1.75 | 2.26 | 2.47 | 1.71 | 58.8% | 10.3% | 0.0% | 18.7% |



- `A1_theory_with_dollar`: to target 10% volatility, gross exposure averages 1.73 times capital (95th percentile 2.28, maximum 3.17); realised volatility 10.5%; the 3x gross cap binds on 0.6% of decision days and the 30% per-pair cap on 18.4%; the whole exposure is a dollar position (same signal on every pair).

- `A2_theory_with_dollar`: to target 10% volatility, gross exposure averages 1.87 times capital (95th percentile 3.00, maximum 3.16); realised volatility 10.2%; the 3x gross cap binds on 6.3% of decision days and the 30% per-pair cap on 32.1%.

- `A1_theory_with_dollar_weekly`: to target 10% volatility, gross exposure averages 1.71 times capital (95th percentile 2.26, maximum 2.47); realised volatility 10.3%; the 3x gross cap binds on 0.0% of decision days and the 30% per-pair cap on 18.7%; the whole exposure is a dollar position (same signal on every pair).


**Diagnostics** (pooled panel regressions, pair fixed effects, Driscoll-Kraay; theory predicts positive coefficients; horizon 0 = contemporaneous):


| model | horizon (days) | component | coef | t | n_obs |
|---|---|---|---|---|---|
| A1_predictive | 1 | MONETARY | 0.0001 | 0.75 | 6,371 |
| A1_predictive | 1 | FISCAL_POLITICAL | 0.0001 | 0.93 | 6,371 |
| A1_predictive | 5 | MONETARY | 0.0005 | 1.02 | 6,151 |
| A1_predictive | 5 | FISCAL_POLITICAL | 0.0009 | 1.92 | 6,151 |
| A1_predictive | 20 | MONETARY | -0.0008 | -0.46 | 5,624 |
| A1_predictive | 20 | FISCAL_POLITICAL | 0.0036 | 3.35 | 5,624 |
| A1_contemporaneous | 0 | MONETARY | 0.0009 | 4.02 | 6,371 |
| A1_contemporaneous | 0 | FISCAL_POLITICAL | 0.0001 | 0.33 | 6,371 |
| A1_fiscal_regime | 1 | _fiscal_raw | 0.0001 | 0.95 | 6,371 |
| A1_fiscal_regime | 1 | _fiscal_x_regime | -0.0015 | -0.57 | 6,371 |
| A2_predictive | 1 | MONETARY | 0.0001 | 1.20 | 6,371 |
| A2_predictive | 1 | INFLATION | -0.0001 | -0.42 | 6,371 |
| A2_predictive | 1 | FISCAL_POLITICAL | 0.0001 | 1.44 | 6,371 |
| A2_predictive | 5 | MONETARY | 0.0006 | 1.34 | 6,151 |
| A2_predictive | 5 | INFLATION | -0.0001 | -0.11 | 6,151 |
| A2_predictive | 5 | FISCAL_POLITICAL | 0.0009 | 2.29 | 6,151 |
| A2_predictive | 20 | MONETARY | 0.0000 | 0.01 | 5,624 |
| A2_predictive | 20 | INFLATION | -0.0024 | -1.38 | 5,624 |
| A2_predictive | 20 | FISCAL_POLITICAL | 0.0030 | 3.21 | 5,624 |
| A2_contemporaneous | 0 | MONETARY | 0.0008 | 3.74 | 6,371 |
| A2_contemporaneous | 0 | INFLATION | 0.0003 | 1.18 | 6,371 |
| A2_contemporaneous | 0 | FISCAL_POLITICAL | 0.0000 | 0.06 | 6,371 |
| A2_fiscal_regime | 1 | _fiscal_raw | 0.0000 | 0.02 | 6,371 |
| A2_fiscal_regime | 1 | _fiscal_x_regime | -0.0002 | -1.29 | 6,371 |
| A2_fiscal_regime | 1 | _fiscal_x_debt | 0.0001 | 0.22 | 6,371 |


Reading: the `_fiscal_x_regime` line cannot be interpreted (regime active on about 1% of days).


**Static / timing decomposition (D25, pre-registered)**: the static part holds the 2024-2025 average position constant; the timing part is the deviation from that average. Gross P&L.


| strategy | part | period | Sharpe | Sharpe t | 90% CI of the Sharpe (bootstrap) | annual return | annual vol |
|---|---|---|---|---|---|---|---|
| A1_theory_with_dollar | total | 2024-2025 | 0.89 | 1.29 | [-0.07, 1.96] | 9.2% | 10.3% |
| A1_theory_with_dollar | total | 2026 (OOS) | 0.85 | 0.74 | [-2.25, 2.49] | 9.1% | 10.7% |
| A1_theory_with_dollar | total | 2024-2026 | 0.88 | 1.48 | [-0.24, 1.67] | 9.2% | 10.4% |
| A1_theory_with_dollar | static | 2024-2025 | 0.21 | 0.30 | [-0.88, 1.23] | 0.5% | 2.4% |
| A1_theory_with_dollar | static | 2026 (OOS) | 0.64 | 0.56 | [-1.60, 2.20] | 1.5% | 2.3% |
| A1_theory_with_dollar | static | 2024-2026 | 0.32 | 0.54 | [-0.74, 1.11] | 0.8% | 2.3% |
| A1_theory_with_dollar | timing | 2024-2025 | 0.85 | 1.22 | [-0.10, 1.89] | 8.7% | 10.3% |
| A1_theory_with_dollar | timing | 2026 (OOS) | 0.72 | 0.63 | [-2.43, 2.62] | 7.6% | 10.6% |
| A1_theory_with_dollar | timing | 2024-2026 | 0.81 | 1.37 | [-0.30, 1.69] | 8.4% | 10.4% |
| A2_theory_with_dollar | total | 2024-2025 | 1.31 | 1.89 | [0.47, 2.35] | 13.4% | 10.2% |
| A2_theory_with_dollar | total | 2026 (OOS) | 1.75 | 1.53 | [-1.19, 2.88] | 17.8% | 10.2% |
| A2_theory_with_dollar | total | 2024-2026 | 1.43 | 2.41 | [0.37, 2.25] | 14.6% | 10.2% |
| A2_theory_with_dollar | static | 2024-2025 | 0.17 | 0.25 | [-0.92, 1.19] | 0.4% | 2.6% |
| A2_theory_with_dollar | static | 2026 (OOS) | 0.62 | 0.54 | [-1.60, 2.15] | 1.6% | 2.6% |
| A2_theory_with_dollar | static | 2024-2026 | 0.29 | 0.48 | [-0.77, 1.07] | 0.8% | 2.6% |
| A2_theory_with_dollar | timing | 2024-2025 | 1.32 | 1.91 | [0.45, 2.40] | 12.9% | 9.8% |
| A2_theory_with_dollar | timing | 2026 (OOS) | 1.68 | 1.46 | [-1.32, 3.02] | 16.2% | 9.7% |
| A2_theory_with_dollar | timing | 2024-2026 | 1.42 | 2.39 | [0.35, 2.32] | 13.8% | 9.7% |


**US fiscal regime (D15)**, share of days in fiscal dominance by year: 2023: 0.0%, 2024: 0.0%, 2025: 4.6%, 2026: 0.0%.


**Finding (D27, exploratory, indicator not retuned)**: the 2025 fiscal-dominance episode was too short for a 60-day rolling correlation; the indicator almost never activates.


**Weekend test (D24, pre-registered)**: main specification = `A1+GEO` (US MONETARY, US FISCAL and GLOBAL GEOPOLITICS on JPY and CHF), gap from Friday 17:00 New York to Monday 07:00 London (`london`), robustness Sunday 18:00 New York (`ny`). The `daily_window_NOT_A_GAP_TEST` rows (Friday noon to Monday noon New York) are **not** a gap test. All weekends since 2024.


| model | component | coef | t | n_obs |
|---|---|---|---|---|
| A1+GEO_weekend_gap_london | MONETARY | 0.0000 | 0.0035 | 1,278 |
| A1+GEO_weekend_gap_london | FISCAL_POLITICAL | 0.0001 | 0.59 | 1,278 |
| A1+GEO_weekend_gap_london | SPILL_GLOBAL_GEOPOLITICS | -0.0002 | -0.62 | 1,278 |
| A1+GEO_weekend_gap_ny | MONETARY | 0.0005 | 1.27 | 1,272 |
| A1+GEO_weekend_gap_ny | FISCAL_POLITICAL | -0.0001 | -0.64 | 1,272 |
| A1+GEO_weekend_gap_ny | SPILL_GLOBAL_GEOPOLITICS | 0.0001 | 0.74 | 1,272 |
| A1_weekend_gap_london | MONETARY | 0.0000 | 0.03 | 1,278 |
| A1_weekend_gap_london | FISCAL_POLITICAL | 0.0001 | 0.52 | 1,278 |
| A1_weekend_gap_ny | MONETARY | 0.0005 | 1.26 | 1,272 |
| A1_weekend_gap_ny | FISCAL_POLITICAL | -0.0001 | -0.60 | 1,272 |
| A1+S_weekend_gap_london | MONETARY | 0.0000 | 0.02 | 1,278 |
| A1+S_weekend_gap_london | FISCAL_POLITICAL | 0.0001 | 0.58 | 1,278 |
| A1+S_weekend_gap_london | SPILL_GLOBAL_GEOPOLITICS | -0.0002 | -0.62 | 1,278 |
| A1+S_weekend_gap_london | SPILL_GLOBAL_GEO_OIL | -0.0000 | -0.06 | 1,278 |
| A1+S_weekend_gap_london | SPILL_CN_TRADE_TARIFFS | 0.0004 | 1.38 | 1,278 |
| A1+S_weekend_gap_ny | MONETARY | 0.0005 | 1.28 | 1,272 |
| A1+S_weekend_gap_ny | FISCAL_POLITICAL | -0.0001 | -0.66 | 1,272 |
| A1+S_weekend_gap_ny | SPILL_GLOBAL_GEOPOLITICS | 0.0001 | 0.74 | 1,272 |
| A1+S_weekend_gap_ny | SPILL_GLOBAL_GEO_OIL | 0.0000 | 0.28 | 1,272 |
| A1+S_weekend_gap_ny | SPILL_CN_TRADE_TARIFFS | 0.0005 | 3.46 | 1,272 |
| A2_weekend_gap_london | MONETARY | -0.0000 | -0.0069 | 1,278 |
| A2_weekend_gap_london | INFLATION | -0.0002 | -1.50 | 1,278 |
| A2_weekend_gap_london | FISCAL_POLITICAL | 0.0001 | 0.40 | 1,278 |
| A2_weekend_gap_ny | MONETARY | 0.0004 | 1.20 | 1,272 |
| A2_weekend_gap_ny | INFLATION | -0.0001 | -1.76 | 1,272 |
| A2_weekend_gap_ny | FISCAL_POLITICAL | -0.0001 | -0.72 | 1,272 |
| A2+S_weekend_gap_london | MONETARY | 0.0001 | 0.15 | 1,278 |
| A2+S_weekend_gap_london | INFLATION | -0.0002 | -1.09 | 1,278 |
| A2+S_weekend_gap_london | FISCAL_POLITICAL | 0.0001 | 0.36 | 1,278 |
| A2+S_weekend_gap_london | TRADE_TARIFFS | -0.0005 | -0.99 | 1,278 |
| A2+S_weekend_gap_london | GEOPOLITICS | 0.0006 | 1.22 | 1,278 |
| A2+S_weekend_gap_london | SPILL_GLOBAL_GEOPOLITICS | -0.0001 | -0.47 | 1,278 |
| A2+S_weekend_gap_london | SPILL_GLOBAL_GEO_OIL | 0.0000 | 0.10 | 1,278 |
| A2+S_weekend_gap_london | SPILL_CN_TRADE_TARIFFS | 0.0002 | 0.56 | 1,278 |
| A2+S_weekend_gap_ny | MONETARY | 0.0005 | 1.39 | 1,272 |
| A2+S_weekend_gap_ny | INFLATION | -0.0001 | -0.89 | 1,272 |
| A2+S_weekend_gap_ny | FISCAL_POLITICAL | -0.0002 | -0.82 | 1,272 |
| A2+S_weekend_gap_ny | TRADE_TARIFFS | -0.0004 | -1.02 | 1,272 |
| A2+S_weekend_gap_ny | GEOPOLITICS | 0.0005 | 1.62 | 1,272 |
| A2+S_weekend_gap_ny | SPILL_GLOBAL_GEOPOLITICS | 0.0002 | 0.86 | 1,272 |
| A2+S_weekend_gap_ny | SPILL_GLOBAL_GEO_OIL | 0.0001 | 0.40 | 1,272 |
| A2+S_weekend_gap_ny | SPILL_CN_TRADE_TARIFFS | 0.0003 | 1.08 | 1,272 |


## 5. Strategy B: EM carry (IRR 12-13 universe) with a PM geopolitical overlay


**Universe (D23, pre-registered)**: Ilzetzki-Reinhart-Rogoff de facto classification, 2019 vintage (limitation: no regime change after 2019 is seen). Primary universe = fine codes 12 (managed floating) and 13 (freely floating); portfolio = top tercile versus bottom tercile of the carry sort.


| currency | IRR code | de facto regime | primary universe | coarse 1-2 variant |
|---|---|---|---|---|
| BRL | 12.00 | managed floating | yes | yes |
| MXN | 13.00 | freely floating | yes | yes |
| COP | 12.00 | managed floating | yes | yes |
| CLP | 12.00 | managed floating | yes | yes |
| PEN | 8.00 | de facto crawling band <= 2% | no | no |
| ZAR | 13.00 | freely floating | yes | yes |
| TRY | 14.00 | freely falling | no | no |
| PLN | 11.00 | moving band <= 2% | no | yes |
| HUF | 8.00 | de facto crawling band <= 2% | no | no |
| CZK | 4.00 | de facto peg | no | no |
| IDR | 8.00 | de facto crawling band <= 2% | no | no |
| INR | 11.00 | moving band <= 2% | no | yes |
| KRW | 12.00 | managed floating | yes | yes |
| TWD |  | not in IRR database | no | no |
| THB | 11.00 | moving band <= 2% | no | yes |
| PHP | 8.00 | de facto crawling band <= 2% | no | no |
| MYR | 11.00 | moving band <= 2% | no | yes |
| CNH | 3.00 | pre-announced horizontal band <= 2% | no | no |



| strategy | period | Sharpe | Sharpe t | 90% CI of the Sharpe (bootstrap) | annual return | annual vol | max drawdown | positive days | skew | annual turnover | annual cost |
|---|---|---|---|---|---|---|---|---|---|---|---|
| base_carry | 2024-2025 | 0.95 | 1.37 | [-0.04, 2.08] | 9.8% | 10.3% | -14.0% | 55.3% | -0.31 | 8.00 | 0.4% |
| base_carry | 2024-2026 | 1.25 | 2.10 | [0.33, 2.31] | 13.0% | 10.4% | -14.0% | 54.9% | -0.24 | 6.62 | 0.4% |
| base_carry | 2026 (OOS) | 2.03 | 1.77 | [0.55, 3.75] | 21.7% | 10.7% | -5.1% | 53.9% | -0.08 | 2.84 | 0.2% |
| base_carry_gross | 2024-2025 | 1.00 | 1.43 | [-0.00, 2.12] | 10.2% | 10.3% | -13.9% | 55.3% | -0.31 |  |  |
| base_carry_gross | 2024-2026 | 1.28 | 2.16 | [0.35, 2.35] | 13.4% | 10.4% | -13.9% | 54.9% | -0.24 |  |  |
| base_carry_gross | 2026 (OOS) | 2.04 | 1.78 | [0.57, 3.76] | 21.9% | 10.7% | -5.0% | 53.9% | -0.08 |  |  |
| pm_timed | 2024-2025 | 0.99 | 1.43 | [-0.10, 2.10] | 8.5% | 8.5% | -8.0% | 48.9% | -0.10 | 22.18 | 1.4% |
| pm_timed | 2024-2026 | 1.30 | 2.19 | [0.42, 2.27] | 11.6% | 8.9% | -8.0% | 50.3% | -0.07 | 21.59 | 1.3% |
| pm_timed | 2026 (OOS) | 2.04 | 1.78 | [0.43, 3.63] | 20.0% | 9.8% | -5.1% | 53.9% | -0.04 | 19.98 | 1.1% |
| pm_timed_gross | 2024-2025 | 1.16 | 1.67 | [0.06, 2.27] | 9.9% | 8.5% | -8.0% | 49.3% | -0.12 |  |  |
| pm_timed_gross | 2024-2026 | 1.45 | 2.45 | [0.53, 2.45] | 12.9% | 8.9% | -8.0% | 50.6% | -0.07 |  |  |
| pm_timed_gross | 2026 (OOS) | 2.16 | 1.88 | [0.51, 3.77] | 21.2% | 9.8% | -5.0% | 53.9% | -0.03 |  |  |
| vix_timed | 2024-2025 | 0.86 | 1.24 | [-0.16, 2.09] | 8.0% | 9.3% | -11.6% | 54.7% | -0.35 | 25.15 | 1.6% |
| vix_timed | 2024-2026 | 1.12 | 1.89 | [0.15, 2.19] | 10.6% | 9.4% | -11.6% | 54.5% | -0.27 | 24.40 | 1.5% |
| vix_timed | 2026 (OOS) | 1.84 | 1.60 | [0.30, 3.55] | 17.6% | 9.6% | -5.1% | 53.9% | -0.07 | 22.36 | 1.3% |
| vix_timed_gross | 2024-2025 | 1.02 | 1.48 | [-0.00, 2.26] | 9.6% | 9.3% | -11.2% | 55.4% | -0.36 |  |  |
| vix_timed_gross | 2024-2026 | 1.28 | 2.16 | [0.30, 2.35] | 12.0% | 9.4% | -11.2% | 55.0% | -0.28 |  |  |
| vix_timed_gross | 2026 (OOS) | 1.97 | 1.72 | [0.44, 3.75] | 18.9% | 9.6% | -5.0% | 53.9% | -0.08 |  |  |
| pm_timed_level_misspecified | 2024-2025 | 1.07 | 1.54 | [0.09, 2.12] | 6.7% | 6.2% | -5.4% | 40.5% | 0.01 | 16.77 | 1.0% |
| pm_timed_level_misspecified | 2024-2026 | 1.39 | 2.34 | [0.60, 2.28] | 10.3% | 7.4% | -5.4% | 44.1% | 0.05 | 17.63 | 1.0% |
| pm_timed_level_misspecified | 2026 (OOS) | 2.04 | 1.78 | [0.43, 3.63] | 20.0% | 9.8% | -5.1% | 53.9% | -0.04 | 19.98 | 1.1% |
| pm_timed_prob_index_D12 | 2024-2025 | 0.74 | 1.07 | [-0.35, 1.79] | 6.0% | 8.1% | -9.3% | 46.7% | -0.01 | 23.47 | 1.5% |
| pm_timed_prob_index_D12 | 2024-2026 | 1.08 | 1.82 | [0.22, 2.05] | 9.2% | 8.5% | -9.3% | 48.7% | -0.0080 | 24.52 | 1.5% |
| pm_timed_prob_index_D12 | 2026 (OOS) | 1.88 | 1.64 | [0.24, 3.48] | 18.1% | 9.6% | -5.1% | 54.5% | -0.05 | 27.37 | 1.6% |


`pm_timed` = base carry with the PM geopolitical overlay. To be read with the D29 diagnostic just below.


**Where does the gap between PM timing and the base carry come from? (D29, a posteriori diagnostic)**

Cumulative gap (PM timing minus base carry, sum of net returns): -4.1 points, of which +6.3 points in the single month 2024-06. The event that raised the escalation index most in the previous 35 days is `will-china-invade-taiwan-in-2024` (1 contract(s)). Same rule, index rebuilt without that event:


| strategy | Sharpe | annual return | max drawdown |
|---|---|---|---|
| base_carry | 1.25 | 13.0% | -14.0% |
| pm_timed | 1.30 | 11.6% | -8.0% |
| pm_timed_without_event | 1.00 | 9.5% | -13.1% |


**A posteriori additions on B (partial lifting of the freeze, 2026-10-03)**:
- `b2_oil_tilt` (B2, spec 7.5): mechanism and direction pre-specified in spec 7.5 (deferred by D5); implementation details fixed after seeing B's oil exposure. A confirmed shock carried more than half by "oil" contracts (Middle East, Russia-Ukraine) does not cut the carry: it adds a tilt long exporters (BRL MXN COP) against importers (KRW), sized by the avoided cut. Other shocks cut as in the primary rule. Confirmed shocks: 19, of which 18 classified as "oil": B2 therefore almost always tilts instead of cutting.
- `b2_brent_tilt`: same rule, oil shock triggered by a daily Brent rise of more than 2 standard deviations (16 days).
- `pm_timed_min3events` (D31, robustness motivated by D29): a day counts in the index, the escalation measure and shock confirmation only if at least 3 distinct events have eligible contracts that day (722 index days versus 815). The primary rule is unchanged.


| strategy | period | Sharpe | Sharpe t | 90% CI of the Sharpe (bootstrap) | annual return | annual vol | max drawdown | positive days | skew | annual turnover | annual cost |
|---|---|---|---|---|---|---|---|---|---|---|---|
| b2_oil_tilt | 2024-2025 | 1.08 | 1.56 | [0.02, 2.13] | 10.4% | 9.6% | -10.7% | 49.1% | -0.20 | 23.51 | 1.6% |
| b2_oil_tilt | 2024-2026 | 1.37 | 2.31 | [0.53, 2.32] | 14.0% | 10.2% | -10.7% | 50.4% | -0.06 | 22.38 | 1.5% |
| b2_oil_tilt | 2026 (OOS) | 2.04 | 1.77 | [0.51, 3.46] | 23.6% | 11.6% | -5.1% | 53.9% | 0.13 | 19.28 | 1.3% |
| b2_oil_tilt_gross | 2024-2025 | 1.25 | 1.80 | [0.18, 2.30] | 12.1% | 9.6% | -10.2% | 49.5% | -0.20 |  |  |
| b2_oil_tilt_gross | 2024-2026 | 1.52 | 2.56 | [0.67, 2.47] | 15.5% | 10.2% | -10.2% | 50.7% | -0.05 |  |  |
| b2_oil_tilt_gross | 2026 (OOS) | 2.15 | 1.87 | [0.58, 3.56] | 24.9% | 11.6% | -5.0% | 53.9% | 0.15 |  |  |
| b2_brent_tilt | 2024-2025 | 1.07 | 1.55 | [0.03, 2.11] | 10.4% | 9.6% | -9.8% | 49.7% | -0.15 | 19.35 | 1.2% |
| b2_brent_tilt | 2024-2026 | 1.41 | 2.38 | [0.54, 2.41] | 14.5% | 10.3% | -9.8% | 50.4% | -0.05 | 19.63 | 1.3% |
| b2_brent_tilt | 2026 (OOS) | 2.20 | 1.91 | [0.52, 3.87] | 25.9% | 11.8% | -5.5% | 52.4% | 0.05 | 20.39 | 1.4% |
| pm_timed_min3events | 2024-2025 | 0.58 | 0.83 | [-0.49, 1.84] | 5.4% | 9.3% | -13.1% | 48.2% | -0.34 | 23.52 | 1.5% |
| pm_timed_min3events | 2024-2026 | 0.89 | 1.50 | [-0.14, 2.01] | 8.3% | 9.3% | -13.1% | 49.7% | -0.25 | 21.68 | 1.4% |
| pm_timed_min3events | 2026 (OOS) | 1.78 | 1.55 | [0.10, 3.32] | 16.3% | 9.2% | -5.1% | 53.9% | -0.02 | 16.64 | 0.9% |


Gap to the base carry (sum of net returns), with and without the month 2024-06 identified by D29 (B2's escalation component is the primary rule's):


| strategy | cumulative gap (points) | of which 2024-06 (points) | excluding 2024-06 (points) |
|---|---|---|---|
| pm_timed | -4.08 | 6.33 | -10.42 |
| b2_oil_tilt | 2.73 | 6.33 | -3.61 |
| b2_brent_tilt | 4.30 | 6.33 | -2.04 |
| pm_timed_min3events | -13.34 | 0.00 | -13.34 |


**Universe variants and 20% cap per currency (D23)**:


| strategy | period | Sharpe | Sharpe t | 90% CI of the Sharpe (bootstrap) | annual return | annual vol | max drawdown | positive days | skew | annual turnover | annual cost |
|---|---|---|---|---|---|---|---|---|---|---|---|
| base_carry__coarse12 | 2024-2025 | 0.24 | 0.34 | [-0.80, 1.42] | 2.5% | 10.6% | -19.3% | 51.8% | -0.27 | 10.26 | 0.9% |
| base_carry__coarse12 | 2024-2026 | 0.51 | 0.86 | [-0.47, 1.60] | 5.5% | 10.7% | -19.3% | 52.5% | -0.26 | 12.20 | 1.0% |
| base_carry__coarse12 | 2026 (OOS) | 1.24 | 1.08 | [-0.37, 3.71] | 13.7% | 11.0% | -6.9% | 54.5% | -0.24 | 17.51 | 1.2% |
| pm_timed__coarse12 | 2024-2025 | 0.35 | 0.51 | [-0.65, 1.44] | 3.2% | 9.1% | -12.5% | 46.3% | -0.28 | 25.15 | 2.1% |
| pm_timed__coarse12 | 2024-2026 | 0.74 | 1.24 | [-0.20, 1.79] | 6.9% | 9.4% | -12.5% | 48.3% | -0.17 | 30.01 | 2.3% |
| pm_timed__coarse12 | 2026 (OOS) | 1.68 | 1.46 | [0.02, 3.95] | 17.0% | 10.1% | -5.3% | 53.9% | 0.03 | 43.32 | 3.1% |
| base_carry__previous | 2024-2025 | 1.46 | 2.11 | [0.34, 2.72] | 15.2% | 10.4% | -10.5% | 58.1% | -0.32 | 17.99 | 1.8% |
| base_carry__previous | 2024-2026 | 2.17 | 3.65 | [1.00, 3.39] | 23.2% | 10.7% | -10.5% | 59.1% | -0.21 | 20.82 | 1.9% |
| base_carry__previous | 2026 (OOS) | 3.96 | 3.45 | [1.68, 6.36] | 45.1% | 11.4% | -6.1% | 61.8% | -0.05 | 28.59 | 2.1% |
| pm_timed__previous | 2024-2025 | 0.79 | 1.14 | [-0.35, 2.10] | 6.9% | 8.7% | -12.9% | 49.7% | -0.43 | 39.55 | 4.5% |
| pm_timed__previous | 2024-2026 | 1.66 | 2.79 | [0.42, 2.93] | 15.1% | 9.1% | -12.9% | 52.5% | -0.27 | 47.76 | 5.0% |
| pm_timed__previous | 2026 (OOS) | 3.74 | 3.26 | [1.68, 6.30] | 37.7% | 10.1% | -5.3% | 60.2% | -0.10 | 70.25 | 6.5% |
| base_carry__primary_cap20 | 2024-2025 | 0.89 | 1.29 | [-0.10, 1.99] | 9.0% | 10.1% | -14.8% | 56.0% | -0.34 | 7.53 | 0.4% |
| base_carry__primary_cap20 | 2024-2026 | 1.19 | 2.00 | [0.29, 2.26] | 12.2% | 10.3% | -14.8% | 55.7% | -0.27 | 6.00 | 0.3% |
| base_carry__primary_cap20 | 2026 (OOS) | 1.96 | 1.71 | [0.57, 3.79] | 20.8% | 10.6% | -4.9% | 55.0% | -0.12 | 1.80 | 0.1% |
| pm_timed__primary_cap20 | 2024-2025 | 0.90 | 1.30 | [-0.22, 1.99] | 7.5% | 8.3% | -8.7% | 49.3% | -0.09 | 21.85 | 1.4% |
| pm_timed__primary_cap20 | 2024-2026 | 1.23 | 2.07 | [0.34, 2.25] | 10.7% | 8.7% | -8.7% | 50.7% | -0.07 | 20.95 | 1.3% |
| pm_timed__primary_cap20 | 2026 (OOS) | 2.00 | 1.74 | [0.47, 3.66] | 19.5% | 9.7% | -4.9% | 54.5% | -0.08 | 18.50 | 1.1% |
| base_carry__previous_cap20 | 2024-2025 | 1.26 | 1.81 | [0.17, 2.47] | 13.2% | 10.5% | -10.5% | 56.8% | -0.32 | 18.20 | 1.8% |
| base_carry__previous_cap20 | 2024-2026 | 1.92 | 3.23 | [0.84, 3.12] | 20.6% | 10.7% | -10.5% | 58.0% | -0.25 | 22.17 | 2.0% |
| base_carry__previous_cap20 | 2026 (OOS) | 3.61 | 3.14 | [1.52, 6.13] | 40.8% | 11.3% | -5.9% | 61.3% | -0.15 | 33.03 | 2.4% |
| pm_timed__previous_cap20 | 2024-2025 | 0.67 | 0.97 | [-0.46, 1.93] | 5.9% | 8.8% | -13.5% | 48.4% | -0.40 | 39.64 | 4.4% |
| pm_timed__previous_cap20 | 2024-2026 | 1.49 | 2.51 | [0.34, 2.70] | 13.8% | 9.3% | -13.5% | 51.7% | -0.22 | 48.38 | 4.8% |
| pm_timed__previous_cap20 | 2026 (OOS) | 3.44 | 3.00 | [1.52, 6.00] | 35.6% | 10.3% | -5.1% | 60.7% | -0.03 | 72.30 | 6.1% |


The 20% cap cannot be met with fewer than three currencies per leg; weights are then equal within the leg instead of inverse to volatility.


**Base EM carry over the long history** (crash-risk premise):


| days | Sharpe | annual return | annual vol | max drawdown | skew | excess_kurtosis |
|---|---|---|---|---|---|---|
| 4,365 | 0.33 | 3.5% | 10.7% | -43.7% | -0.19 | 2.70 |


**Composition of the base carry over 2024-2026**:


| currency | share of exposure | days long | cumulative P&L (sum of returns) |
|---|---|---|---|
| KRW | 28.6% | 0% | 0.08 |
| CLP | 20.7% | 0% | 0.01 |
| COP | 19.2% | 79% | 0.08 |
| BRL | 16.6% | 63% | 0.16 |
| MXN | 14.9% | 58% | 0.04 |
| ZAR | 0.0% | 0% | 0.00 |


**Exposure w(t)** of the PM timing: mean 0.81; days with w < 1: 211 of 714; shock days: 19. VIX timing: mean 0.87, shock days: 25.


**Full grid** (27 cells: shock threshold k, re-risk days, cut level):


| k | re-risk (days) | cut to | Sharpe | annual return | max drawdown |
|---|---|---|---|---|---|
| 1.50 | 5 | 0.00 | 0.96 | 8.3% | -8.5% |
| 1.50 | 5 | 0.25 | 1.10 | 9.7% | -8.7% |
| 1.50 | 5 | 0.50 | 1.23 | 11.0% | -8.9% |
| 1.50 | 10 | 0.00 | 0.96 | 7.8% | -8.0% |
| 1.50 | 10 | 0.25 | 1.12 | 9.3% | -8.0% |
| 1.50 | 10 | 0.50 | 1.25 | 10.8% | -8.5% |
| 1.50 | 20 | 0.00 | 0.95 | 6.9% | -8.0% |
| 1.50 | 20 | 0.25 | 1.14 | 8.6% | -8.0% |
| 1.50 | 20 | 0.50 | 1.28 | 10.3% | -8.2% |
| 2.00 | 5 | 0.00 | 1.23 | 11.2% | -8.5% |
| 2.00 | 5 | 0.25 | 1.29 | 11.8% | -8.7% |
| 2.00 | 5 | 0.50 | 1.35 | 12.4% | -8.9% |
| 2.00 | 10 | 0.00 | 1.24 | 10.8% | -8.0% |
| 2.00 | 10 | 0.25 | 1.30 | 11.6% | -8.0% |
| 2.00 | 10 | 0.50 | 1.36 | 12.3% | -8.5% |
| 2.00 | 20 | 0.00 | 1.18 | 9.7% | -8.0% |
| 2.00 | 20 | 0.25 | 1.28 | 10.8% | -8.0% |
| 2.00 | 20 | 0.50 | 1.35 | 11.8% | -8.2% |
| 2.50 | 5 | 0.00 | 1.34 | 12.4% | -9.3% |
| 2.50 | 5 | 0.25 | 1.37 | 12.7% | -9.3% |
| 2.50 | 5 | 0.50 | 1.38 | 12.9% | -9.3% |
| 2.50 | 10 | 0.00 | 1.36 | 12.3% | -9.3% |
| 2.50 | 10 | 0.25 | 1.38 | 12.6% | -9.3% |
| 2.50 | 10 | 0.50 | 1.40 | 12.9% | -9.3% |
| 2.50 | 20 | 0.00 | 1.25 | 10.9% | -9.3% |
| 2.50 | 20 | 0.25 | 1.31 | 11.6% | -9.3% |
| 2.50 | 20 | 0.50 | 1.36 | 12.3% | -9.3% |


**Cost sensitivity** (PM timing):


| cost multiple | Sharpe | annual return | max drawdown |
|---|---|---|---|
| 0.50 | 1.38 | 12.2% | -8.0% |
| 1.00 | 1.30 | 11.6% | -8.0% |
| 2.00 | 1.15 | 10.2% | -8.4% |
| 3.00 | 1.00 | 8.9% | -8.9% |


**Leverage and exposure** (gross exposure = sum of absolute weights, in multiples of capital; net USD exposure = minus the sum of the weights, > 0 = long USD; B's rule has no gross cap and no per-currency cap; the 20% variant is reported in section 5):


| strategy | period | mean gross | median gross | gross 95th percentile | max gross | mean |net USD| | days long USD | realised vol (target 10%) |
|---|---|---|---|---|---|---|---|---|
| base_carry | 2024-2025 | 2.15 | 2.08 | 2.92 | 3.04 | 0.0039 | 2.3% | 10.3% |
| base_carry | 2026 | 2.06 | 2.05 | 2.29 | 2.29 | 0.0017 | 3.1% | 10.7% |
| base_carry | 2024-2026 | 2.13 | 2.08 | 2.92 | 3.04 | 0.0033 | 2.5% | 10.4% |
| pm_timed | 2024-2025 | 1.70 | 1.90 | 2.92 | 3.04 | 0.02 | 4.2% | 8.5% |
| pm_timed | 2026 | 1.86 | 1.95 | 2.27 | 2.29 | 0.02 | 5.2% | 9.8% |
| pm_timed | 2024-2026 | 1.74 | 1.92 | 2.77 | 3.04 | 0.02 | 4.5% | 8.9% |
| vix_timed | 2024-2025 | 1.91 | 1.99 | 2.92 | 2.97 | 0.02 | 5.0% | 9.3% |
| vix_timed | 2026 | 1.74 | 1.91 | 2.29 | 2.29 | 0.02 | 4.7% | 9.6% |
| vix_timed | 2024-2026 | 1.86 | 1.96 | 2.77 | 2.97 | 0.02 | 4.9% | 9.4% |
| b2_oil_tilt | 2024-2025 | 2.00 | 2.11 | 3.20 | 4.98 | 0.03 | 18.5% | 9.6% |
| b2_oil_tilt | 2026 | 2.20 | 2.17 | 3.21 | 3.63 | 0.03 | 22.0% | 11.6% |
| b2_oil_tilt | 2024-2026 | 2.06 | 2.11 | 3.21 | 4.98 | 0.03 | 19.5% | 10.2% |



- `base_carry`: to target 10% volatility, gross exposure averages 2.13 times capital (95th percentile 2.92, maximum 3.04); realised volatility 10.4%; net dollar exposure close to zero (mean |net USD| 0.00), the long and short legs having the same gross size; with no cap in the rule, gross exposure exceeds 3x on some days (max 3.04).

- `pm_timed`: to target 10% volatility, gross exposure averages 1.74 times capital (95th percentile 2.77, maximum 3.04); realised volatility 8.9%; net dollar exposure close to zero (mean |net USD| 0.02), the long and short legs having the same gross size; with no cap in the rule, gross exposure exceeds 3x on some days (max 3.04).

- `vix_timed`: to target 10% volatility, gross exposure averages 1.86 times capital (95th percentile 2.77, maximum 2.97); realised volatility 9.4%; net dollar exposure close to zero (mean |net USD| 0.02), the long and short legs having the same gross size.

- `b2_oil_tilt`: to target 10% volatility, gross exposure averages 2.06 times capital (95th percentile 3.21, maximum 4.98); realised volatility 10.2%; net dollar exposure close to zero (mean |net USD| 0.03), the long and short legs having the same gross size; with no cap in the rule, gross exposure exceeds 3x on some days (max 4.98).


## 6. Robustness and placebos


**Strategy A, A1 with dollar**: the actual Sharpe beats 92% of the 100 placebo draws (a).


| exercise | n | mean Sharpe | min | max |
|---|---|---|---|---|
| actual | 1 | 0.43 | 0.43 | 0.43 |
| equal_weights | 1 | 0.41 | 0.41 | 0.41 |
| halflife | 4 | 0.15 | -1.21 | 1.06 |
| leave_one_event_out | 10 | 0.42 | 0.23 | 0.63 |
| placebo_a_shuffle | 100 | -0.34 | -1.44 | 0.79 |
| placebo_b_random_contracts | 1 | -0.55 | -0.55 | -0.55 |
| placebo_c_reversed | 1 | -1.34 | -1.34 | -1.34 |


**Strategy A, A2 with dollar**: the actual Sharpe beats 99% of the 100 placebo draws (a).


| exercise | n | mean Sharpe | min | max |
|---|---|---|---|---|
| actual | 1 | 0.81 | 0.81 | 0.81 |
| equal_weights | 1 | 0.93 | 0.93 | 0.93 |
| halflife | 4 | 0.33 | -0.79 | 0.82 |
| leave_one_event_out | 10 | 0.81 | 0.68 | 1.14 |
| placebo_a_shuffle | 100 | -0.22 | -1.30 | 0.85 |
| placebo_b_random_contracts | 1 | -0.30 | -0.30 | -0.30 |
| placebo_c_reversed | 1 | -2.06 | -2.06 | -2.06 |


**Strategy A, A1+S dollar-neutral**: the actual Sharpe beats 100% of the 100 placebo draws (a).


| exercise | n | mean Sharpe | min | max |
|---|---|---|---|---|
| actual | 1 | -0.71 | -0.71 | -0.71 |
| equal_weights | 1 | -0.86 | -0.86 | -0.86 |
| halflife | 4 | -0.68 | -1.74 | -0.01 |
| leave_one_event_out | 10 | -0.70 | -0.71 | -0.57 |
| placebo_a_shuffle | 100 | -3.73 | -4.87 | -2.32 |
| placebo_b_random_contracts | 1 | -1.00 | -1.00 | -1.00 |
| placebo_c_reversed | 1 | -2.19 | -2.19 | -2.19 |


Leave-one-event-out (Strategy A, events removed one at a time):


| event removed | Sharpe | max drawdown |
|---|---|---|
| presidential-election-winner-2024 | 0.30 | -14.7% |
| PRES-2024 | 0.38 | -14.1% |
| who-will-be-inaugurated-as-president | 0.63 | -14.1% |
| presidential-election-popular-vote-winner-2024 | 0.45 | -14.1% |
| fed-decision-in-january | 0.41 | -14.1% |
| fed-decision-in-march-885 | 0.23 | -17.3% |
| fed-decision-in-december | 0.45 | -14.1% |
| fed-decision-in-september-762 | 0.43 | -14.1% |
| fed-decision-in-september | 0.47 | -14.1% |
| fed-decision-in-october | 0.47 | -14.1% |


**Strategy B (PM timing)**: the actual Sharpe beats 93% of the 100 placebo draws (a).


| exercise | n | mean Sharpe | min | max |
|---|---|---|---|---|
| actual | 1 | 1.30 | 1.30 | 1.30 |
| base_carry | 1 | 1.25 | 1.25 | 1.25 |
| equal_weights | 1 | 1.36 | 1.36 | 1.36 |
| leave_one_event_out | 10 | 1.29 | 1.24 | 1.36 |
| placebo_a_shuffle | 100 | 0.99 | 0.66 | 1.53 |
| placebo_b_random_contracts | 1 | 1.10 | 1.10 | 1.10 |
| placebo_c_reversed | 1 | 1.10 | 1.10 | 1.10 |
| volume_threshold | 2 | 1.05 | 0.89 | 1.21 |


Leave-one-event-out (Strategy B (PM timing), events removed one at a time):


| event removed | Sharpe | max drawdown |
|---|---|---|
| us-x-iran-permanent-peace-deal-by | 1.26 | -8.0% |
| us-strikes-iran-by | 1.28 | -8.0% |
| us-x-iran-ceasefire-by | 1.24 | -8.0% |
| will-the-us-invade-iran-before-2027 | 1.30 | -8.0% |
| russia-x-ukraine-ceasefire-in-2025 | 1.33 | -8.0% |
| trump-wins-ends-ukraine-war-in-90-days | 1.36 | -8.0% |
| will-china-invade-taiwan-before-2027 | 1.27 | -8.0% |
| kharg-island-no-longer-under-iranian-control-by-march-31 | 1.30 | -8.0% |
| strait-of-hormuz-traffic-returns-to-normal-by-end-of-june | 1.26 | -8.0% |
| KXHORMUZNORM-26MAR17 | 1.26 | -8.0% |


**Placebos of the a posteriori additions** (same placebos (a), (b), (c); for D30 the frozen component and coefficient are applied to the placebo signals without re-estimation; the Brent benchmark has no PM signal, hence no placebo).


**A1_theory_with_dollar_weekly**: the actual Sharpe beats 86% of the 100 placebo draws (a).


| exercise | n | mean Sharpe | min | max |
|---|---|---|---|---|
| actual | 1 | 0.75 | 0.75 | 0.75 |
| placebo_a_shuffle | 100 | 0.24 | -1.01 | 1.36 |
| placebo_b_random_contracts | 1 | -0.07 | -0.07 | -0.07 |
| placebo_c_reversed | 1 | -1.19 | -1.19 | -1.19 |


**A1_gated20_frozen**: the actual Sharpe beats 99% of the 100 placebo draws (a).


| exercise | n | mean Sharpe | min | max |
|---|---|---|---|---|
| actual | 1 | 1.51 | 1.51 | 1.51 |
| placebo_a_shuffle | 100 | 0.46 | -0.44 | 1.54 |
| placebo_b_random_contracts | 1 | 0.04 | 0.04 | 0.04 |
| placebo_c_reversed | 1 | -1.67 | -1.67 | -1.67 |


**b2_oil_tilt**: the actual Sharpe beats 90% of the 100 placebo draws (a).


| exercise | n | mean Sharpe | min | max |
|---|---|---|---|---|
| actual | 1 | 1.37 | 1.37 | 1.37 |
| placebo_a_shuffle | 100 | 1.15 | 0.83 | 1.61 |
| placebo_b_random_contracts | 1 | 1.10 | 1.10 | 1.10 |
| placebo_c_reversed | 1 | 1.12 | 1.12 | 1.12 |


**pm_timed_min3events**: the actual Sharpe beats 65% of the 100 placebo draws (a).


| exercise | n | mean Sharpe | min | max |
|---|---|---|---|---|
| actual | 1 | 0.89 | 0.89 | 0.89 |
| placebo_a_shuffle | 100 | 0.85 | 0.51 | 1.22 |
| placebo_b_random_contracts | 1 | 1.16 | 1.16 | 1.16 |
| placebo_c_reversed | 1 | 1.11 | 1.11 | 1.11 |


Reading:
- **Weekly A1 and D30** beat the large majority of draws, and collapse with random contracts or the reversed sign. For D30, placebo (a) shuffles dates within the month while the position is held 20 days: it keeps part of the monthly level of the signal (positive mean of the draws), so it is a weaker test than for a daily rule. No placebo addresses the a posteriori choice of the horizon.
- **B2** beats most draws and placebos (b) and (c), but the mean of the draws stays below the base carry, and B2's lead over the carry comes from the month identified by D29 (section 5).
- **3-event overlay (D31)**: random contracts and the reversed sign do better than the actual rule; nothing distinguishes this signal from random timing.


**Sub-periods**:


| strategy (Sharpe by year) | 2024 | 2025 | 2026 |
|---|---|---|---|
| A1_gated20_frozen | 1.23 | 1.09 | 2.46 |
| A1_theory_with_dollar | 0.23 | 0.77 | 0.28 |
| A1_theory_with_dollar_weekly | 0.03 | 1.77 | 0.44 |
| A2_theory_with_dollar | 0.39 | 1.06 | 1.08 |
| b2_brent_tilt | 0.49 | 1.55 | 2.20 |
| b2_oil_tilt | 0.31 | 1.67 | 2.04 |
| base_carry | 0.22 | 1.70 | 2.03 |
| pm_timed | 0.75 | 1.20 | 2.04 |
| pm_timed_min3events | 0.11 | 1.08 | 1.78 |
| vix_timed | 0.33 | 1.39 | 1.84 |


## 7. Risk


**Normal and downside beta** (Lettau, Maggiori, Weber; weekly; market = MSCI World net TR, or EM carry):


| strategy | market | beta | downside_beta | down weeks | mean return in those weeks (bp) |
|---|---|---|---|---|---|
| A1_theory_with_dollar | msci_world | -0.06 | -0.13 | 21 | 25.28 |
| A1_theory_with_dollar | em_carry | -0.08 | 0.0079 | 20 | 37.21 |
| A1+S_theory_with_dollar | msci_world | -0.04 | -0.09 | 21 | 9.94 |
| A1+S_theory_with_dollar | em_carry | -0.08 | 0.04 | 20 | 18.52 |
| A2_theory_with_dollar | msci_world | -0.24 | -0.81 | 21 | 70.83 |
| A2_theory_with_dollar | em_carry | 0.04 | 0.05 | 20 | 2.79 |
| base_carry | msci_world | -0.02 | 0.0003 | 21 | 12.38 |
| pm_timed | msci_world | -0.04 | 0.04 | 21 | 8.16 |
| pm_timed | em_carry | 0.68 | 0.22 | 20 | -162.02 |
| vix_timed | msci_world | -0.02 | -0.05 | 21 | 5.87 |
| vix_timed | em_carry | 0.89 | 0.93 | 20 | -207.37 |


**Weekly betas** (Newey-West t):


| strategy | factor | beta | t | correlation |
|---|---|---|---|---|
| A1_theory_with_dollar | spx | -0.04 | -0.77 | -0.06 |
| A1_theory_with_dollar | msci_world | -0.06 | -1.03 | -0.08 |
| A1_theory_with_dollar | brent | 0.0043 | 0.25 | 0.02 |
| A1_theory_with_dollar | dollar | 0.03 | 0.14 | 0.02 |
| A1_theory_with_dollar | g10_carry | -0.02 | -0.36 | -0.03 |
| A1_theory_with_dollar | em_carry | -0.08 | -0.87 | -0.09 |
| A1_theory_with_dollar | d_vix | 0.0004 | 1.46 | 0.10 |
| A1+S_theory_with_dollar | spx | -0.03 | -0.68 | -0.05 |
| A1+S_theory_with_dollar | msci_world | -0.04 | -0.75 | -0.06 |
| A1+S_theory_with_dollar | brent | -0.02 | -0.83 | -0.06 |
| A1+S_theory_with_dollar | dollar | -0.11 | -0.50 | -0.07 |
| A1+S_theory_with_dollar | g10_carry | -0.05 | -0.76 | -0.06 |
| A1+S_theory_with_dollar | em_carry | -0.08 | -0.87 | -0.09 |
| A1+S_theory_with_dollar | d_vix | 0.0001 | 0.55 | 0.04 |
| A2_theory_with_dollar | spx | -0.22 | -1.98 | -0.28 |
| A2_theory_with_dollar | msci_world | -0.24 | -2.03 | -0.28 |
| A2_theory_with_dollar | brent | 0.01 | 0.50 | 0.04 |
| A2_theory_with_dollar | dollar | 0.20 | 0.77 | 0.11 |
| A2_theory_with_dollar | g10_carry | -0.10 | -0.89 | -0.11 |
| A2_theory_with_dollar | em_carry | 0.04 | 0.38 | 0.03 |
| A2_theory_with_dollar | d_vix | 0.0015 | 2.67 | 0.34 |
| base_carry | spx | -0.01 | -0.19 | -0.02 |
| base_carry | msci_world | -0.02 | -0.37 | -0.03 |
| base_carry | brent | 0.07 | 4.54 | 0.28 |
| base_carry | dollar | 0.26 | 1.97 | 0.15 |
| base_carry | g10_carry | 0.24 | 3.53 | 0.28 |
| base_carry | d_vix | -0.0002 | -0.67 | -0.05 |
| pm_timed | spx | -0.04 | -0.82 | -0.07 |
| pm_timed | msci_world | -0.04 | -0.76 | -0.06 |
| pm_timed | brent | 0.05 | 3.36 | 0.21 |
| pm_timed | dollar | 0.15 | 1.48 | 0.11 |
| pm_timed | g10_carry | 0.17 | 2.78 | 0.24 |
| pm_timed | em_carry | 0.68 | 6.29 | 0.86 |
| pm_timed | d_vix | -0.0002 | -0.66 | -0.05 |
| vix_timed | spx | 0.0006 | 0.01 | 0.0008 |
| vix_timed | msci_world | -0.02 | -0.31 | -0.02 |
| vix_timed | brent | 0.07 | 4.74 | 0.28 |
| vix_timed | dollar | 0.24 | 2.01 | 0.16 |
| vix_timed | g10_carry | 0.18 | 3.34 | 0.22 |
| vix_timed | em_carry | 0.89 | 25.39 | 0.97 |
| vix_timed | d_vix | -0.0001 | -0.30 | -0.02 |


**Stress episodes** (cumulative return over the window):


| episode | A1+S_theory_with_dollar | A1_theory_with_dollar | A2_theory_with_dollar | base_carry | pm_timed | vix_timed |
|---|---|---|---|---|---|---|
| Iran war (Feb-Apr 2026) | -6.6% | -7.5% | 2.9% | 8.0% | 5.9% | 6.9% |
| Israel-Iran war (Jun 2025) | -0.5% | 0.3% | 0.4% | -0.2% | -0.6% | -0.2% |
| Liberation Day tariffs (Apr 2025) | 2.4% | 1.1% | 0.4% | -2.8% | -2.8% | -1.4% |
| Yen carry unwind (Aug 2024) | 2.2% | 2.4% | 2.4% | -1.3% | -1.3% | -1.0% |


**Conditional performance** (Sharpe by state):


| state | A1+S_theory_with_dollar | A1_theory_with_dollar | A2_theory_with_dollar | base_carry | pm_timed | vix_timed |
|---|---|---|---|---|---|---|
| VIX tercile: high tercile | -0.99 | -0.20 | 0.25 | 2.09 | 1.46 | 2.05 |
| VIX tercile: low tercile | -0.95 | -0.40 | 0.45 | 0.57 | 1.76 | 0.58 |
| VIX tercile: middle tercile | 1.28 | 1.84 | 1.69 | 1.03 | 0.69 | 0.81 |
| dollar month: dollar down | -0.40 | 0.19 | -0.05 | 0.39 | 0.14 | 0.22 |
| dollar month: dollar up | 0.0004 | 0.70 | 1.77 | 2.18 | 2.84 | 2.06 |
| geo shock day: no | -0.23 | 0.41 | 0.82 | 1.18 | 1.29 | 1.05 |
| geo shock day: yes | 0.83 | 1.14 | 0.21 | 3.96 | 1.67 | 4.15 |
| large Brent week: no | -0.02 | 0.77 | 0.68 | 0.85 | 1.13 | 0.75 |
| large Brent week: yes | -1.47 | -1.63 | 1.60 | 3.98 | 2.82 | 3.64 |


**Liquidity risk** (reporting): performance by tercile of the average 1-month forward half-spread of each strategy's universe (G10 for A, primary EM universe for B), same causal smoothing as the costs, value known the day before. High tercile = least liquid market.


Sharpe:


| tercile | A1+S_theory_with_dollar | A1_theory_with_dollar | A2_theory_with_dollar | base_carry | pm_timed | vix_timed |
|---|---|---|---|---|---|---|
| low spreads | -0.12 | 0.29 | 0.64 | 2.38 | 2.19 | 2.54 |
| middle spreads | 0.93 | 1.38 | 1.37 | 0.68 | 1.37 | 0.33 |
| high spreads | -1.45 | -0.38 | 0.41 | 0.64 | 0.17 | 0.45 |


Mean annual return:


| tercile | A1+S_theory_with_dollar | A1_theory_with_dollar | A2_theory_with_dollar | base_carry | pm_timed | vix_timed |
|---|---|---|---|---|---|---|
| low spreads | -1.2% | 3.2% | 6.8% | 25.5% | 22.0% | 24.5% |
| middle spreads | 8.8% | 14.2% | 13.9% | 6.9% | 11.3% | 3.2% |
| high spreads | -13.8% | -3.9% | 4.1% | 6.6% | 1.4% | 4.0% |


**5 worst drawdowns: A1_theory_with_dollar** (label = news between peak and trough):


| peak | trough | recovery | depth | duration (days) | context |
|---|---|---|---|---|---|
| 2026-03-03 | 2026-07-30 | ongoing | -14.1% | 205 | US fiscal news, US monetary news, geopolitical shock |
| 2024-02-13 | 2024-07-29 | 2024-11-05 | -13.5% | 266 | US fiscal news, US monetary news |
| 2024-11-05 | 2025-02-28 | 2025-10-31 | -10.5% | 360 | US fiscal news, US monetary news, geopolitical shock |
| 2026-01-26 | 2026-01-29 | 2026-02-05 | -2.9% | 10 | US fiscal news |
| 2025-12-10 | 2025-12-30 | 2026-01-09 | -2.1% | 30 | other |


**5 worst drawdowns: pm_timed** (label = news between peak and trough):


| peak | trough | recovery | depth | duration (days) | context |
|---|---|---|---|---|---|
| 2024-07-22 | 2024-09-10 | 2025-08-06 | -8.0% | 380 | US monetary news |
| 2025-11-12 | 2025-12-30 | 2026-03-12 | -5.4% | 120 | US monetary news |
| 2026-07-23 | 2026-08-31 | ongoing | -5.1% | 63 | US monetary news |
| 2024-04-08 | 2024-04-25 | 2024-07-12 | -3.8% | 95 | US fiscal news |
| 2026-04-29 | 2026-05-13 | 2026-05-22 | -2.8% | 23 | US fiscal news |


**5 worst drawdowns: base_carry** (label = news between peak and trough):


| peak | trough | recovery | depth | duration (days) | context |
|---|---|---|---|---|---|
| 2024-04-08 | 2024-09-30 | 2025-07-02 | -14.0% | 450 | US fiscal news, US monetary news, geopolitical shock |
| 2025-11-12 | 2025-12-30 | 2026-03-03 | -5.4% | 111 | US monetary news |
| 2026-07-23 | 2026-08-31 | ongoing | -5.1% | 63 | US monetary news |
| 2026-04-29 | 2026-05-13 | 2026-05-22 | -2.8% | 23 | US fiscal news |
| 2025-10-06 | 2025-10-10 | 2025-10-17 | -2.8% | 11 | other |


**P&L concentration** (Herfindahl index of absolute contributions; 1 = everything on a single item):


| strategy | dimension | HHI |
|---|---|---|
| A1_theory_with_dollar | currency | 0.14 |
| A1_theory_with_dollar | month | 0.04 |
| base_carry | currency | 0.29 |
| base_carry | month | 0.05 |
| pm_timed | currency | 0.27 |
| pm_timed | month | 0.05 |


**A versus B** (correlation with PM-timed B):


| strategy A | daily correlation | weekly correlation | drawdown correlation |
|---|---|---|---|
| A1_theory_with_dollar | -0.04 | -0.17 | -0.01 |
| A1+S_theory_with_dollar | -0.03 | -0.12 | -0.14 |
| A2_theory_with_dollar | -0.03 | -0.03 | 0.17 |
| A2+S_theory_with_dollar | 0.02 | -0.06 | 0.31 |


## 7b. Intraday lead-lag (D26, exploratory)


Event studies: top 1% of hourly changes (mechanical selection). Values aligned on the sign of the event; hour 0 = hour of the event (intervals dated by their end); 95% CI. A significant mean at negative hours would mean that the other market moves first.


| study | h-3 | h-2 | h-1 | h+0 | h+1 | h+2 | h+3 |
|---|---|---|---|---|---|---|---|
| FX top 1% -> PM GLOBAL/GEOPOLITICS | -0.0083 [-0.2307, 0.2142] | 0.0243 [-0.2119, 0.2605] | -0.0670 [-0.2983, 0.1642] | 0.2726 [0.0944, 0.4507] | 0.0876 [-0.1533, 0.3285] | 0.1449 [-0.1083, 0.3982] | -0.1172 [-0.3717, 0.1374] |
| FX top 1% -> PM US/FISCAL_POLITICAL | -0.0827 [-0.4213, 0.2559] | 0.0300 [-0.3036, 0.3635] | 0.0182 [-0.3012, 0.3377] | 0.1116 [-0.0963, 0.3194] | 0.1685 [-0.0854, 0.4224] | 0.0729 [-0.2097, 0.3555] | -0.1283 [-0.4702, 0.2135] |
| FX top 1% -> PM US/MONETARY | 0.1486 [-0.0488, 0.3461] | -0.1272 [-0.3077, 0.0533] | 0.1701 [-0.0860, 0.4262] | 0.9250 [0.6123, 1.2376] | 0.2965 [0.0762, 0.5168] | 0.1648 [-0.0329, 0.3625] | -0.0073 [-0.2542, 0.2397] |
| PM GLOBAL/GEOPOLITICS top 1% -> FX dollar basket | -0.0000 [-0.0001, 0.0001] | 0.0001 [0.0000, 0.0002] | 0.0001 [-0.0001, 0.0002] | 0.0000 [-0.0000, 0.0001] | -0.0001 [-0.0003, -0.0000] | 0.0001 [-0.0001, 0.0003] | -0.0000 [-0.0002, 0.0001] |
| PM US/FISCAL_POLITICAL top 1% -> FX dollar basket | -0.0000 [-0.0002, 0.0001] | 0.0000 [-0.0001, 0.0001] | 0.0000 [-0.0001, 0.0001] | -0.0001 [-0.0002, 0.0000] | -0.0000 [-0.0001, 0.0001] | 0.0000 [-0.0001, 0.0001] | 0.0000 [-0.0001, 0.0001] |
| PM US/MONETARY top 1% -> FX dollar basket | 0.0001 [-0.0001, 0.0002] | 0.0000 [-0.0001, 0.0001] | 0.0001 [-0.0000, 0.0002] | 0.0002 [0.0000, 0.0004] | 0.0000 [-0.0001, 0.0002] | -0.0000 [-0.0001, 0.0001] | -0.0000 [-0.0001, 0.0001] |


## 8. Caveats

- Statistics that rest on a regressor that is almost always zero (fiscal × regime interaction, own-zone geopolitics in the weekend test) cannot be interpreted, even with a high t.
- Several variants are reported (D14, D17), plus the a posteriori additions of 2026-10-03: results must be read with the multiple-testing caveat, and an a posteriori addition must never be presented as pre-registered.
- Costs come from Bloomberg closing bid/ask (indicative composite quotes). They are wide for NOK and SEK (median half-spread of about 11 to 12 bp) and CHF (about 5 bp), probably wider than dealable spreads: A's costs are conservative. A's daily turnover makes its net Sharpe very sensitive to this.
- No price is a 16:00 London fix: the FX day (New York close to New York close) ends six hours after the PM day (16:00 to 16:00 London), which slightly dilutes contemporaneous coefficients; predictive regressions and backtests are not affected (signal known before execution).
- The Sharpe t (annualised Sharpe x square root of the number of years) and the 90% block-bootstrap confidence interval (blocks of 20 days, 1000 draws) show the uncertainty: over two to three years, a Sharpe below about 1.2 is not significantly different from zero.

- Base EM carry (primary universe, 5 currencies used): the most heavily weighted currency is KRW (29% of average exposure).
