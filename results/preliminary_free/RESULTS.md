# Quantitative results: prediction markets x FX (MFE 230GB)

Generated on 2026-10-07 by `src/report/summary_md.py` from the result files. Every number comes from the CSV/Parquet files listed in each section; nothing is typed by hand.

> **Preliminary results (DECISIONS D22).** Free market data: FRED H.10 (G10, New York noon), ECB reference rates (EM, one-day execution lag), synthetic forwards from covered interest parity with OECD short rates, flat costs (2 bp G10, 10 bp EM). They validate the mechanics and flag the points to decide; the Bloomberg run supersedes them.

Sample: 2024-01-01 to 2026-09-24; in-sample 2024-2025, out-of-sample from 2026-01-01. Signals at the 16:00 London snapshot, returns at the free-data fixing, statistics annualised over 252 days. Returns and volatility are in percent.

## Key numbers

- Cells that pass the coverage rule: 3 (US/MONETARY, GLOBAL/GEOPOLITICS, US/FISCAL_POLITICAL).

- **A1 (dollar leg)**, net Sharpe: 0.65 in 2024-2025, 1.30 in 2026; gross over 2024-2026: 1.09; annual turnover 132.

- **A2 (relaxed coverage)**, net Sharpe: 0.73 in 2024-2025, 1.89 in 2026; spec gated rule: no theme passes |t| > 3.

- **B, EM carry (IRR 12-13 universe) with a PM geopolitical overlay**, net Sharpe 2024-2026: base carry 0.68; with the PM overlay 0.69.

- **B, the three versions**, net Sharpe 2024-2026: base carry 0.68, PM-timed 0.69, VIX-timed 0.29; maximum drawdown: -12.0%, -10.6%, -12.9% (primary universe 1 versus 1 on free data: a mechanical check, not interpretable; "coarse 1-2" variant: carry 0.72, PM-timed 0.61).

- **A1, decomposition (D25)**: the timing part carries most of the gross P&L (see section 4).

- **Downside beta** (equities): base carry 0.16, PM-timed 0.14, VIX-timed 0.15.

- **Correlation A1 / B** (daily returns): 0.08.



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
| A1_theory_with_dollar | 2024-2025 | 0.65 | 0.94 | [-0.34, 1.86] | 6.6% | 10.1% | -14.8% | 48.9% | -0.24 | 114.78 | 2.3% |
| A1_theory_with_dollar | 2024-2026 | 0.83 | 1.40 | [-0.34, 1.73] | 8.5% | 10.3% | -14.8% | 49.6% | -0.32 | 131.65 | 2.6% |
| A1_theory_with_dollar | 2026 (OOS) | 1.30 | 1.13 | [-1.54, 2.97] | 13.8% | 10.6% | -9.7% | 51.3% | -0.53 | 177.83 | 3.6% |
| A1_theory_with_dollar_gross | 2024-2025 | 0.88 | 1.27 | [-0.13, 2.07] | 8.9% | 10.1% | -13.4% | 49.9% | -0.21 |  |  |
| A1_theory_with_dollar_gross | 2024-2026 | 1.09 | 1.84 | [-0.08, 1.97] | 11.1% | 10.2% | -13.4% | 50.8% | -0.29 |  |  |
| A1_theory_with_dollar_gross | 2026 (OOS) | 1.64 | 1.43 | [-1.14, 3.33] | 17.4% | 10.6% | -8.1% | 53.4% | -0.49 |  |  |
| A2_theory_with_dollar | 2024-2025 | 0.73 | 1.05 | [-0.31, 1.90] | 7.2% | 10.0% | -15.6% | 47.6% | -0.18 | 168.00 | 3.4% |
| A2_theory_with_dollar | 2024-2026 | 1.03 | 1.74 | [-0.09, 1.97] | 10.3% | 9.9% | -15.6% | 49.2% | -0.21 | 179.40 | 3.6% |
| A2_theory_with_dollar | 2026 (OOS) | 1.89 | 1.65 | [-0.74, 3.04] | 18.6% | 9.8% | -7.8% | 53.4% | -0.28 | 210.59 | 4.2% |
| A2_theory_with_dollar_gross | 2024-2025 | 1.07 | 1.54 | [0.04, 2.26] | 10.6% | 9.9% | -14.1% | 48.8% | -0.14 |  |  |
| A2_theory_with_dollar_gross | 2024-2026 | 1.40 | 2.36 | [0.29, 2.35] | 13.8% | 9.9% | -14.1% | 50.7% | -0.18 |  |  |
| A2_theory_with_dollar_gross | 2026 (OOS) | 2.33 | 2.03 | [-0.31, 3.48] | 22.8% | 9.8% | -6.6% | 56.0% | -0.27 |  |  |
| A2_theory_dollar_neutral | 2024-2025 | -1.10 | -1.59 | [-2.25, 0.08] | -5.9% | 5.3% | -14.6% | 33.3% | -0.11 | 157.19 | 3.1% |
| A2_theory_dollar_neutral | 2024-2026 | -1.06 | -1.79 | [-2.05, -0.06] | -6.0% | 5.7% | -20.5% | 37.0% | -0.17 | 194.45 | 3.9% |
| A2_theory_dollar_neutral | 2026 (OOS) | -0.99 | -0.86 | [-2.71, 0.66] | -6.5% | 6.6% | -7.9% | 47.1% | -0.25 | 296.48 | 5.9% |
| A1+S_theory_with_dollar | 2024-2025 | 0.38 | 0.54 | [-0.77, 1.62] | 3.7% | 9.7% | -15.2% | 48.8% | -0.19 | 174.11 | 3.5% |
| A1+S_theory_with_dollar | 2024-2026 | 0.29 | 0.48 | [-0.94, 1.12] | 2.8% | 9.7% | -15.2% | 49.4% | -0.31 | 202.31 | 4.0% |
| A1+S_theory_with_dollar | 2026 (OOS) | 0.05 | 0.04 | [-2.62, 1.85] | 0.5% | 9.9% | -12.2% | 51.3% | -0.60 | 279.55 | 5.6% |
| A1+S_theory_dollar_neutral | 2024-2025 | 0.54 | 0.77 | [-0.63, 1.60] | 3.4% | 6.3% | -6.9% | 37.7% | 2.58 | 183.71 | 3.7% |
| A1+S_theory_dollar_neutral | 2024-2026 | -0.01 | -0.02 | [-1.07, 0.94] | -0.1% | 6.1% | -13.6% | 40.3% | 1.98 | 217.64 | 4.4% |
| A1+S_theory_dollar_neutral | 2026 (OOS) | -1.75 | -1.52 | [-3.07, -0.17] | -9.6% | 5.5% | -8.3% | 47.6% | -0.60 | 310.54 | 6.2% |
| A2+S_theory_with_dollar | 2024-2025 | 0.08 | 0.12 | [-0.93, 1.25] | 0.8% | 9.4% | -18.0% | 45.1% | 0.03 | 215.42 | 4.3% |
| A2+S_theory_with_dollar | 2024-2026 | 0.60 | 1.02 | [-0.49, 1.47] | 5.7% | 9.5% | -18.0% | 46.6% | 0.07 | 225.85 | 4.5% |
| A2+S_theory_with_dollar | 2026 (OOS) | 2.03 | 1.76 | [-0.23, 3.37] | 19.2% | 9.5% | -6.1% | 50.8% | 0.18 | 254.41 | 5.1% |
| A2+S_theory_dollar_neutral | 2024-2025 | -0.41 | -0.59 | [-1.53, 0.51] | -2.8% | 6.9% | -9.3% | 41.1% | 2.25 | 286.96 | 5.7% |
| A2+S_theory_dollar_neutral | 2024-2026 | -0.62 | -1.04 | [-1.52, 0.25] | -4.2% | 6.7% | -14.3% | 41.9% | 1.77 | 302.23 | 6.0% |
| A2+S_theory_dollar_neutral | 2026 (OOS) | -1.28 | -1.11 | [-2.57, 0.86] | -7.9% | 6.2% | -7.5% | 44.0% | -0.11 | 344.05 | 6.9% |
| A1_theory_with_dollar_D12 | 2024-2025 | 0.24 | 0.34 | [-1.01, 1.48] | 2.4% | 10.1% | -14.9% | 45.9% | -0.22 |  |  |
| A1_theory_with_dollar_D12 | 2024-2026 | 0.07 | 0.12 | [-1.01, 1.05] | 0.7% | 10.3% | -14.9% | 46.1% | -0.02 |  |  |
| A1_theory_with_dollar_D12 | 2026 (OOS) | -0.36 | -0.32 | [-2.51, 1.26] | -3.9% | 10.7% | -12.8% | 46.6% | 0.48 |  |  |
| A1_gated_frozen | 2024-2025 |  |  |  | 0.0% | 0.0% | 0.0% | 0.0% | 0.00 |  |  |
| A1_gated_frozen | 2024-2026 |  |  |  | 0.0% | 0.0% | 0.0% | 0.0% | 0.00 |  |  |
| A1_gated_frozen | 2026 (OOS) |  |  |  | 0.0% | 0.0% | 0.0% | 0.0% | 0.00 |  |  |
| A2_gated_frozen | 2024-2025 |  |  |  | 0.0% | 0.0% | 0.0% | 0.0% | 0.00 |  |  |
| A2_gated_frozen | 2024-2026 |  |  |  | 0.0% | 0.0% | 0.0% | 0.0% | 0.00 |  |  |
| A2_gated_frozen | 2026 (OOS) |  |  |  | 0.0% | 0.0% | 0.0% | 0.0% | 0.00 |  |  |


**Estimation of the gated rule (2024-2025)**: no theme has t > 3 with the right sign, so the rule does not trade.


| variant | component | coef | t | n_obs | passes the gate |
|---|---|---|---|---|---|
| A1 | MONETARY | 0.0000 | 0.17 | 4,509 | no |
| A1 | FISCAL_POLITICAL | 0.0002 | 1.41 | 4,509 | no |
| A2 | MONETARY | 0.0001 | 0.66 | 4,509 | no |
| A2 | INFLATION | -0.0001 | -0.60 | 4,509 | no |
| A2 | FISCAL_POLITICAL | 0.0002 | 1.39 | 4,509 | no |


**Diagnostics** (pooled panel regressions, pair fixed effects, Driscoll-Kraay; theory predicts positive coefficients; horizon 0 = contemporaneous):


| model | horizon (days) | component | coef | t | n_obs |
|---|---|---|---|---|---|
| A1_predictive | 1 | MONETARY | 0.0001 | 1.05 | 6,165 |
| A1_predictive | 1 | FISCAL_POLITICAL | 0.0001 | 0.87 | 6,165 |
| A1_predictive | 5 | MONETARY | 0.0014 | 2.46 | 5,121 |
| A1_predictive | 5 | FISCAL_POLITICAL | 0.0010 | 2.07 | 5,121 |
| A1_predictive | 20 | MONETARY | 0.0018 | 0.81 | 2,205 |
| A1_predictive | 20 | FISCAL_POLITICAL | 0.0029 | 1.36 | 2,205 |
| A1_contemporaneous | 0 | MONETARY | 0.0012 | 4.92 | 6,165 |
| A1_contemporaneous | 0 | FISCAL_POLITICAL | 0.0001 | 0.45 | 6,165 |
| A1_fiscal_regime | 1 | _fiscal_raw | 0.0001 | 0.86 | 6,165 |
| A1_fiscal_regime | 1 | _fiscal_x_regime | 0.11 | 31.82 | 6,165 |
| A2_predictive | 1 | MONETARY | 0.0002 | 1.51 | 6,165 |
| A2_predictive | 1 | INFLATION | -0.0001 | -0.27 | 6,165 |
| A2_predictive | 1 | FISCAL_POLITICAL | 0.0001 | 1.09 | 6,165 |
| A2_predictive | 5 | MONETARY | 0.0011 | 2.25 | 5,121 |
| A2_predictive | 5 | INFLATION | 0.0003 | 0.28 | 5,121 |
| A2_predictive | 5 | FISCAL_POLITICAL | 0.0009 | 2.36 | 5,121 |
| A2_predictive | 20 | MONETARY | 0.0027 | 1.61 | 2,205 |
| A2_predictive | 20 | INFLATION | -0.0073 | -3.05 | 2,205 |
| A2_predictive | 20 | FISCAL_POLITICAL | 0.0036 | 2.46 | 2,205 |
| A2_contemporaneous | 0 | MONETARY | 0.0010 | 4.12 | 6,165 |
| A2_contemporaneous | 0 | INFLATION | 0.0003 | 1.27 | 6,165 |
| A2_contemporaneous | 0 | FISCAL_POLITICAL | 0.0000 | 0.17 | 6,165 |
| A2_fiscal_regime | 1 | _fiscal_raw | -0.0004 | -0.85 | 6,165 |
| A2_fiscal_regime | 1 | _fiscal_x_regime | 0.0042 | 2.17 | 6,165 |
| A2_fiscal_regime | 1 | _fiscal_x_debt | 0.0004 | 0.99 | 6,165 |


Reading: the `_fiscal_x_regime` line cannot be interpreted (regime active on about 1% of days).


**Static / timing decomposition (D25, pre-registered)**: the static part holds the 2024-2025 average position constant; the timing part is the deviation from that average. Gross P&L.


| strategy | part | period | Sharpe | Sharpe t | 90% CI of the Sharpe (bootstrap) | annual return | annual vol |
|---|---|---|---|---|---|---|---|
| A1_theory_with_dollar | total | 2024-2025 | 0.88 | 1.27 | [-0.13, 2.07] | 8.9% | 10.1% |
| A1_theory_with_dollar | total | 2026 (OOS) | 1.64 | 1.43 | [-1.14, 3.33] | 17.4% | 10.6% |
| A1_theory_with_dollar | total | 2024-2026 | 1.09 | 1.84 | [-0.08, 1.97] | 11.1% | 10.2% |
| A1_theory_with_dollar | static | 2024-2025 | 0.22 | 0.32 | [-0.89, 1.25] | 0.5% | 2.3% |
| A1_theory_with_dollar | static | 2026 (OOS) | 0.68 | 0.59 | [-1.65, 2.28] | 1.5% | 2.1% |
| A1_theory_with_dollar | static | 2024-2026 | 0.34 | 0.57 | [-0.79, 1.11] | 0.8% | 2.2% |
| A1_theory_with_dollar | timing | 2024-2025 | 0.83 | 1.20 | [-0.17, 2.03] | 8.4% | 10.0% |
| A1_theory_with_dollar | timing | 2026 (OOS) | 1.50 | 1.31 | [-1.43, 3.39] | 15.9% | 10.6% |
| A1_theory_with_dollar | timing | 2024-2026 | 1.02 | 1.72 | [-0.11, 1.91] | 10.4% | 10.2% |
| A2_theory_with_dollar | total | 2024-2025 | 1.07 | 1.54 | [0.04, 2.26] | 10.6% | 9.9% |
| A2_theory_with_dollar | total | 2026 (OOS) | 2.33 | 2.03 | [-0.31, 3.48] | 22.8% | 9.8% |
| A2_theory_with_dollar | total | 2024-2026 | 1.40 | 2.36 | [0.29, 2.35] | 13.8% | 9.9% |
| A2_theory_with_dollar | static | 2024-2025 | 0.32 | 0.46 | [-0.80, 1.34] | 0.8% | 2.6% |
| A2_theory_with_dollar | static | 2026 (OOS) | 0.66 | 0.57 | [-1.73, 2.33] | 1.6% | 2.5% |
| A2_theory_with_dollar | static | 2024-2026 | 0.41 | 0.69 | [-0.72, 1.20] | 1.0% | 2.6% |
| A2_theory_with_dollar | timing | 2024-2025 | 1.02 | 1.48 | [-0.02, 2.29] | 9.8% | 9.5% |
| A2_theory_with_dollar | timing | 2026 (OOS) | 2.21 | 1.92 | [-0.48, 3.69] | 21.1% | 9.6% |
| A2_theory_with_dollar | timing | 2024-2026 | 1.34 | 2.26 | [0.24, 2.38] | 12.8% | 9.5% |


**US fiscal regime (D15)**, share of days in fiscal dominance by year: 2023: 0.0%, 2024: 0.0%, 2025: 0.8%, 2026: 0.0%.


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


In the preliminary run, only BRL, MXN, ZAR and KRW have both a price and a rate in the free data: the primary universe gives 1 versus 1. It is a mechanical check, **not a result to interpret**.



| strategy | period | Sharpe | Sharpe t | 90% CI of the Sharpe (bootstrap) | annual return | annual vol | max drawdown | positive days | skew | annual turnover | annual cost |
|---|---|---|---|---|---|---|---|---|---|---|---|
| base_carry | 2024-2025 | 0.48 | 0.70 | [-0.30, 1.51] | 5.2% | 10.7% | -12.0% | 53.5% | -0.24 | 3.20 | 0.3% |
| base_carry | 2024-2026 | 0.68 | 1.15 | [-0.22, 1.52] | 7.2% | 10.5% | -12.0% | 54.3% | -0.30 | 3.17 | 0.3% |
| base_carry | 2026 (OOS) | 1.26 | 1.10 | [-1.25, 3.15] | 12.7% | 10.1% | -10.6% | 56.5% | -0.48 | 3.11 | 0.3% |
| base_carry_gross | 2024-2025 | 0.51 | 0.74 | [-0.28, 1.53] | 5.5% | 10.7% | -11.8% | 53.5% | -0.24 |  |  |
| base_carry_gross | 2024-2026 | 0.71 | 1.20 | [-0.20, 1.55] | 7.5% | 10.5% | -11.8% | 54.5% | -0.30 |  |  |
| base_carry_gross | 2026 (OOS) | 1.29 | 1.13 | [-1.22, 3.17] | 13.0% | 10.1% | -10.5% | 57.1% | -0.49 |  |  |
| pm_timed | 2024-2025 | 0.63 | 0.91 | [-0.16, 1.68] | 5.8% | 9.1% | -7.2% | 48.8% | -0.22 | 14.09 | 1.5% |
| pm_timed | 2024-2026 | 0.69 | 1.16 | [-0.16, 1.55] | 6.4% | 9.3% | -10.6% | 50.6% | -0.31 | 15.15 | 1.6% |
| pm_timed | 2026 (OOS) | 0.84 | 0.73 | [-1.59, 2.56] | 8.1% | 9.6% | -10.6% | 55.5% | -0.52 | 18.06 | 1.9% |
| pm_timed_gross | 2024-2025 | 0.80 | 1.15 | [0.01, 1.85] | 7.3% | 9.1% | -7.1% | 48.9% | -0.20 |  |  |
| pm_timed_gross | 2024-2026 | 0.86 | 1.45 | [-0.03, 1.72] | 8.0% | 9.2% | -10.5% | 51.1% | -0.30 |  |  |
| pm_timed_gross | 2026 (OOS) | 1.03 | 0.90 | [-1.46, 2.81] | 10.0% | 9.6% | -10.5% | 57.1% | -0.54 |  |  |
| vix_timed | 2024-2025 | 0.13 | 0.19 | [-0.69, 1.18] | 1.2% | 9.5% | -12.9% | 53.0% | -0.30 | 17.27 | 1.9% |
| vix_timed | 2024-2026 | 0.29 | 0.48 | [-0.63, 1.16] | 2.7% | 9.4% | -12.9% | 53.6% | -0.35 | 18.64 | 2.0% |
| vix_timed | 2026 (OOS) | 0.74 | 0.64 | [-1.82, 2.60] | 6.7% | 9.1% | -11.5% | 55.5% | -0.49 | 22.39 | 2.3% |
| vix_timed_gross | 2024-2025 | 0.33 | 0.47 | [-0.51, 1.35] | 3.1% | 9.5% | -11.9% | 53.5% | -0.30 |  |  |
| vix_timed_gross | 2024-2026 | 0.50 | 0.84 | [-0.45, 1.38] | 4.7% | 9.4% | -11.9% | 54.5% | -0.35 |  |  |
| vix_timed_gross | 2026 (OOS) | 0.99 | 0.86 | [-1.62, 2.99] | 9.0% | 9.1% | -11.2% | 57.1% | -0.53 |  |  |
| pm_timed_level_misspecified | 2024-2025 | 0.42 | 0.60 | [-0.37, 1.48] | 2.7% | 6.5% | -6.8% | 40.5% | -0.95 |  |  |
| pm_timed_level_misspecified | 2024-2026 | 0.56 | 0.94 | [-0.35, 1.40] | 4.2% | 7.5% | -10.6% | 44.5% | -0.73 |  |  |
| pm_timed_level_misspecified | 2026 (OOS) | 0.84 | 0.73 | [-1.59, 2.56] | 8.1% | 9.6% | -10.6% | 55.5% | -0.52 |  |  |
| pm_timed_prob_index_D12 | 2024-2025 | 0.44 | 0.64 | [-0.34, 1.43] | 3.8% | 8.6% | -7.2% | 46.5% | -0.32 |  |  |
| pm_timed_prob_index_D12 | 2024-2026 | 0.59 | 1.00 | [-0.28, 1.45] | 5.2% | 8.7% | -9.9% | 48.9% | -0.31 |  |  |
| pm_timed_prob_index_D12 | 2026 (OOS) | 0.98 | 0.85 | [-1.62, 2.82] | 8.9% | 9.1% | -9.9% | 55.5% | -0.31 |  |  |


`pm_timed` = base carry with the PM geopolitical overlay. To be read with the D29 diagnostic just below.


**Universe variants and 20% cap per currency (D23)**:


| strategy | period | Sharpe | Sharpe t | 90% CI of the Sharpe (bootstrap) | annual return | annual vol | max drawdown | positive days | skew | annual turnover | annual cost |
|---|---|---|---|---|---|---|---|---|---|---|---|
| base_carry__coarse12 | 2024-2025 | 0.34 | 0.49 | [-0.60, 1.36] | 3.7% | 10.8% | -16.8% | 51.8% | -0.27 |  |  |
| base_carry__coarse12 | 2024-2026 | 0.72 | 1.22 | [-0.19, 1.58] | 7.7% | 10.6% | -16.8% | 53.2% | -0.35 |  |  |
| base_carry__coarse12 | 2026 (OOS) | 1.85 | 1.61 | [-0.20, 3.05] | 18.8% | 10.1% | -6.2% | 57.1% | -0.59 |  |  |
| pm_timed__coarse12 | 2024-2025 | 0.34 | 0.49 | [-0.61, 1.30] | 3.1% | 9.2% | -11.9% | 45.5% | -0.38 |  |  |
| pm_timed__coarse12 | 2024-2026 | 0.61 | 1.03 | [-0.28, 1.43] | 5.7% | 9.3% | -11.9% | 48.5% | -0.43 |  |  |
| pm_timed__coarse12 | 2026 (OOS) | 1.32 | 1.15 | [-0.67, 2.53] | 12.8% | 9.7% | -6.2% | 56.5% | -0.58 |  |  |
| base_carry__previous | 2024-2025 | 1.99 | 2.87 | [0.78, 3.31] | 20.4% | 10.2% | -9.1% | 57.0% | -0.50 |  |  |
| base_carry__previous | 2024-2026 | 2.65 | 4.46 | [1.38, 3.69] | 27.4% | 10.3% | -9.1% | 59.1% | -0.40 |  |  |
| base_carry__previous | 2026 (OOS) | 4.43 | 3.86 | [1.66, 5.80] | 46.8% | 10.6% | -6.2% | 64.9% | -0.16 |  |  |
| pm_timed__previous | 2024-2025 | 1.18 | 1.70 | [0.02, 2.49] | 10.2% | 8.7% | -9.1% | 49.3% | -0.61 |  |  |
| pm_timed__previous | 2024-2026 | 1.95 | 3.28 | [0.71, 3.05] | 17.3% | 8.9% | -9.1% | 53.2% | -0.52 |  |  |
| pm_timed__previous | 2026 (OOS) | 3.90 | 3.39 | [1.25, 5.58] | 36.6% | 9.4% | -6.2% | 63.9% | -0.39 |  |  |
| base_carry__primary_cap20 | 2024-2025 | 0.48 | 0.70 | [-0.30, 1.51] | 5.2% | 10.7% | -12.0% | 53.5% | -0.24 |  |  |
| base_carry__primary_cap20 | 2024-2026 | 0.68 | 1.15 | [-0.22, 1.52] | 7.2% | 10.5% | -12.0% | 54.3% | -0.30 |  |  |
| base_carry__primary_cap20 | 2026 (OOS) | 1.26 | 1.10 | [-1.25, 3.15] | 12.7% | 10.1% | -10.6% | 56.5% | -0.48 |  |  |
| pm_timed__primary_cap20 | 2024-2025 | 0.63 | 0.91 | [-0.16, 1.68] | 5.8% | 9.1% | -7.2% | 48.8% | -0.22 |  |  |
| pm_timed__primary_cap20 | 2024-2026 | 0.69 | 1.16 | [-0.16, 1.55] | 6.4% | 9.3% | -10.6% | 50.6% | -0.31 |  |  |
| pm_timed__primary_cap20 | 2026 (OOS) | 0.84 | 0.73 | [-1.59, 2.56] | 8.1% | 9.6% | -10.6% | 55.5% | -0.52 |  |  |
| base_carry__previous_cap20 | 2024-2025 | 1.31 | 1.88 | [0.24, 2.41] | 13.2% | 10.1% | -9.3% | 53.7% | -0.46 |  |  |
| base_carry__previous_cap20 | 2024-2026 | 2.00 | 3.36 | [0.82, 2.98] | 20.1% | 10.1% | -9.3% | 57.1% | -0.50 |  |  |
| base_carry__previous_cap20 | 2026 (OOS) | 3.93 | 3.42 | [1.09, 5.51] | 39.0% | 9.9% | -6.5% | 66.5% | -0.61 |  |  |
| pm_timed__previous_cap20 | 2024-2025 | 0.86 | 1.24 | [-0.28, 2.06] | 7.7% | 9.0% | -9.3% | 47.0% | -0.59 |  |  |
| pm_timed__previous_cap20 | 2024-2026 | 1.47 | 2.48 | [0.31, 2.51] | 13.4% | 9.1% | -9.3% | 52.0% | -0.58 |  |  |
| pm_timed__previous_cap20 | 2026 (OOS) | 3.08 | 2.68 | [0.45, 4.65] | 29.0% | 9.4% | -6.5% | 65.4% | -0.61 |  |  |


The 20% cap cannot be met with fewer than three currencies per leg; weights are then equal within the leg instead of inverse to volatility.


**Base EM carry over the long history** (crash-risk premise):


| days | Sharpe | annual return | annual vol | max drawdown | skew | excess_kurtosis |
|---|---|---|---|---|---|---|
| 4,365 | 0.11 | 1.2% | 10.6% | -51.5% | -0.15 | 5.58 |


**Composition of the base carry over 2024-2026**:


| currency | share of exposure | days long | cumulative P&L (sum of returns) |
|---|---|---|---|
| BRL | 50.0% | 100% | 0.10 |
| KRW | 50.0% | 0% | 0.11 |
| MXN | 0.0% | 0% | 0.00 |
| ZAR | 0.0% | 0% | 0.00 |


**Exposure w(t)** of the PM timing: mean 0.81; days with w < 1: 211 of 714; shock days: 19. VIX timing: mean 0.88, shock days: 24.


**Full grid** (27 cells: shock threshold k, re-risk days, cut level):


| k | re-risk (days) | cut to | Sharpe | annual return | max drawdown |
|---|---|---|---|---|---|
| 1.50 | 5 | 0.00 | 0.43 | 3.9% | -9.8% |
| 1.50 | 5 | 0.25 | 0.59 | 5.4% | -9.9% |
| 1.50 | 5 | 0.50 | 0.74 | 6.9% | -10.0% |
| 1.50 | 10 | 0.00 | 0.50 | 4.1% | -8.7% |
| 1.50 | 10 | 0.25 | 0.65 | 5.6% | -9.0% |
| 1.50 | 10 | 0.50 | 0.79 | 7.0% | -9.4% |
| 1.50 | 20 | 0.00 | 0.46 | 3.5% | -7.2% |
| 1.50 | 20 | 0.25 | 0.64 | 5.1% | -7.9% |
| 1.50 | 20 | 0.50 | 0.80 | 6.7% | -8.6% |
| 2.00 | 5 | 0.00 | 0.63 | 5.9% | -10.6% |
| 2.00 | 5 | 0.25 | 0.73 | 6.9% | -10.6% |
| 2.00 | 5 | 0.50 | 0.83 | 7.9% | -10.6% |
| 2.00 | 10 | 0.00 | 0.57 | 5.2% | -10.6% |
| 2.00 | 10 | 0.25 | 0.69 | 6.4% | -10.6% |
| 2.00 | 10 | 0.50 | 0.80 | 7.5% | -10.6% |
| 2.00 | 20 | 0.00 | 0.46 | 4.0% | -10.6% |
| 2.00 | 20 | 0.25 | 0.62 | 5.5% | -10.6% |
| 2.00 | 20 | 0.50 | 0.76 | 6.9% | -10.6% |
| 2.50 | 5 | 0.00 | 0.77 | 7.5% | -10.6% |
| 2.50 | 5 | 0.25 | 0.83 | 8.0% | -10.6% |
| 2.50 | 5 | 0.50 | 0.88 | 8.5% | -10.6% |
| 2.50 | 10 | 0.00 | 0.77 | 7.3% | -10.6% |
| 2.50 | 10 | 0.25 | 0.83 | 7.9% | -10.6% |
| 2.50 | 10 | 0.50 | 0.88 | 8.5% | -10.6% |
| 2.50 | 20 | 0.00 | 0.67 | 6.2% | -10.6% |
| 2.50 | 20 | 0.25 | 0.76 | 7.1% | -10.6% |
| 2.50 | 20 | 0.50 | 0.84 | 7.9% | -10.6% |


**Cost sensitivity** (PM timing):


| cost multiple | Sharpe | annual return | max drawdown |
|---|---|---|---|
| 0.50 | 0.78 | 7.2% | -10.6% |
| 1.00 | 0.69 | 6.4% | -10.6% |
| 2.00 | 0.52 | 4.8% | -10.6% |
| 3.00 | 0.35 | 3.2% | -10.6% |


## 6. Robustness and placebos


**Strategy A, A1 with dollar**: the actual Sharpe beats 90% of the 50 placebo draws (a).


| exercise | n | mean Sharpe | min | max |
|---|---|---|---|---|
| actual | 1 | 0.83 | 0.83 | 0.83 |
| equal_weights | 1 | 0.70 | 0.70 | 0.70 |
| halflife | 4 | 0.43 | -0.78 | 1.17 |
| leave_one_event_out | 10 | 0.84 | 0.74 | 1.08 |
| placebo_a_shuffle | 50 | 0.12 | -0.80 | 1.10 |
| placebo_b_random_contracts | 1 | -0.43 | -0.43 | -0.43 |
| placebo_c_reversed | 1 | -1.36 | -1.36 | -1.36 |


**Strategy A, A2 with dollar**: the actual Sharpe beats 94% of the 50 placebo draws (a).


| exercise | n | mean Sharpe | min | max |
|---|---|---|---|---|
| actual | 1 | 1.03 | 1.03 | 1.03 |
| equal_weights | 1 | 0.96 | 0.96 | 0.96 |
| halflife | 4 | 0.59 | -0.24 | 1.03 |
| leave_one_event_out | 10 | 1.05 | 0.91 | 1.44 |
| placebo_a_shuffle | 50 | 0.08 | -0.82 | 1.16 |
| placebo_b_random_contracts | 1 | -0.54 | -0.54 | -0.54 |
| placebo_c_reversed | 1 | -1.77 | -1.77 | -1.77 |


**Strategy A, A1+S dollar-neutral**: the actual Sharpe beats 100% of the 50 placebo draws (a).


| exercise | n | mean Sharpe | min | max |
|---|---|---|---|---|
| actual | 1 | -0.01 | -0.01 | -0.01 |
| equal_weights | 1 | 0.0031 | 0.0031 | 0.0031 |
| halflife | 4 | 0.03 | -0.74 | 0.45 |
| leave_one_event_out | 10 | -0.0040 | -0.01 | 0.06 |
| placebo_a_shuffle | 50 | -1.73 | -2.77 | -0.68 |
| placebo_b_random_contracts | 1 | -0.50 | -0.50 | -0.50 |
| placebo_c_reversed | 1 | -1.43 | -1.43 | -1.43 |


Leave-one-event-out (Strategy A, events removed one at a time):


| event removed | Sharpe | max drawdown |
|---|---|---|
| presidential-election-winner-2024 | 0.79 | -12.4% |
| PRES-2024 | 0.80 | -14.8% |
| who-will-be-inaugurated-as-president | 1.08 | -14.8% |
| presidential-election-popular-vote-winner-2024 | 0.82 | -15.7% |
| fed-decision-in-january | 0.82 | -14.8% |
| fed-decision-in-march-885 | 0.74 | -14.8% |
| fed-decision-in-december | 0.81 | -14.8% |
| fed-decision-in-september-762 | 0.82 | -14.8% |
| fed-decision-in-september | 0.89 | -14.8% |
| fed-decision-in-october | 0.86 | -14.8% |


**Strategy B (PM timing)**: the actual Sharpe beats 88% of the 50 placebo draws (a).


| exercise | n | mean Sharpe | min | max |
|---|---|---|---|---|
| actual | 1 | 0.69 | 0.69 | 0.69 |
| base_carry | 1 | 0.68 | 0.68 | 0.68 |
| equal_weights | 1 | 0.77 | 0.77 | 0.77 |
| leave_one_event_out | 10 | 0.71 | 0.67 | 0.83 |
| placebo_a_shuffle | 50 | 0.53 | 0.25 | 0.85 |
| placebo_b_random_contracts | 1 | 0.61 | 0.61 | 0.61 |
| placebo_c_reversed | 1 | 0.52 | 0.52 | 0.52 |
| volume_threshold | 2 | 0.58 | 0.36 | 0.79 |


Leave-one-event-out (Strategy B (PM timing), events removed one at a time):


| event removed | Sharpe | max drawdown |
|---|---|---|
| us-x-iran-permanent-peace-deal-by | 0.70 | -10.5% |
| us-strikes-iran-by | 0.67 | -10.6% |
| us-x-iran-ceasefire-by | 0.69 | -10.5% |
| will-the-us-invade-iran-before-2027 | 0.69 | -10.6% |
| russia-x-ukraine-ceasefire-in-2025 | 0.71 | -10.6% |
| trump-wins-ends-ukraine-war-in-90-days | 0.83 | -10.6% |
| will-china-invade-taiwan-before-2027 | 0.70 | -10.6% |
| kharg-island-no-longer-under-iranian-control-by-march-31 | 0.69 | -10.6% |
| strait-of-hormuz-traffic-returns-to-normal-by-end-of-june | 0.70 | -10.5% |
| KXHORMUZNORM-26MAR17 | 0.70 | -10.5% |


**Sub-periods**:


| strategy (Sharpe by year) | 2024 | 2025 | 2026 |
|---|---|---|---|
| A1_theory_with_dollar | 0.13 | 1.17 | 1.30 |
| A2_theory_with_dollar | 0.20 | 1.27 | 1.89 |
| base_carry | -0.48 | 1.55 | 1.26 |
| pm_timed | 0.25 | 1.03 | 0.84 |
| vix_timed | -0.84 | 1.18 | 0.74 |


## 7. Risk


**Normal and downside beta** (Lettau, Maggiori, Weber; weekly; market = S&P 500 in place of MSCI World, or EM carry):


| strategy | market | beta | downside_beta | down weeks | mean return in those weeks (bp) |
|---|---|---|---|---|---|
| A1_theory_with_dollar | msci_world | -0.07 | -0.14 | 21 | 52.11 |
| A1_theory_with_dollar | em_carry | 0.08 | 0.05 | 21 | 11.43 |
| A1+S_theory_with_dollar | msci_world | -0.09 | -0.23 | 21 | 32.25 |
| A1+S_theory_with_dollar | em_carry | 0.06 | 0.08 | 21 | 9.79 |
| A2_theory_with_dollar | msci_world | -0.23 | -0.66 | 21 | 86.37 |
| A2_theory_with_dollar | em_carry | 0.12 | 0.13 | 21 | 6.95 |
| base_carry | msci_world | 0.06 | 0.16 | 21 | 13.58 |
| pm_timed | msci_world | 0.05 | 0.14 | 21 | 4.51 |
| pm_timed | em_carry | 0.79 | 0.43 | 21 | -161.53 |
| vix_timed | msci_world | 0.03 | 0.15 | 21 | 18.30 |
| vix_timed | em_carry | 0.82 | 0.60 | 21 | -180.14 |


**Weekly betas** (Newey-West t):


In the preliminary run the S&P 500 stands in for MSCI World: the two lines are identical.


| strategy | factor | beta | t | correlation |
|---|---|---|---|---|
| A1_theory_with_dollar | spx | -0.07 | -1.26 | -0.11 |
| A1_theory_with_dollar | msci_world | -0.07 | -1.26 | -0.11 |
| A1_theory_with_dollar | brent | -0.0041 | -0.31 | -0.02 |
| A1_theory_with_dollar | dollar | 0.10 | 0.33 | 0.04 |
| A1_theory_with_dollar | g10_carry | -0.02 | -0.21 | -0.02 |
| A1_theory_with_dollar | em_carry | 0.08 | 0.88 | 0.08 |
| A1_theory_with_dollar | d_vix | 0.0006 | 1.93 | 0.15 |
| A1+S_theory_with_dollar | spx | -0.09 | -1.37 | -0.13 |
| A1+S_theory_with_dollar | msci_world | -0.09 | -1.37 | -0.13 |
| A1+S_theory_with_dollar | brent | -0.02 | -0.94 | -0.08 |
| A1+S_theory_with_dollar | dollar | -0.07 | -0.25 | -0.03 |
| A1+S_theory_with_dollar | g10_carry | -0.05 | -0.65 | -0.06 |
| A1+S_theory_with_dollar | em_carry | 0.06 | 0.75 | 0.06 |
| A1+S_theory_with_dollar | d_vix | 0.0004 | 1.21 | 0.10 |
| A2_theory_with_dollar | spx | -0.23 | -2.01 | -0.30 |
| A2_theory_with_dollar | msci_world | -0.23 | -2.01 | -0.30 |
| A2_theory_with_dollar | brent | 0.02 | 1.04 | 0.08 |
| A2_theory_with_dollar | dollar | 0.31 | 0.94 | 0.13 |
| A2_theory_with_dollar | g10_carry | -0.13 | -1.07 | -0.14 |
| A2_theory_with_dollar | em_carry | 0.12 | 1.40 | 0.11 |
| A2_theory_with_dollar | d_vix | 0.0015 | 2.70 | 0.36 |
| base_carry | spx | 0.06 | 1.17 | 0.09 |
| base_carry | msci_world | 0.06 | 1.17 | 0.09 |
| base_carry | brent | 0.02 | 1.52 | 0.12 |
| base_carry | dollar | 0.32 | 1.86 | 0.15 |
| base_carry | g10_carry | 0.26 | 3.68 | 0.31 |
| base_carry | d_vix | -0.0004 | -1.11 | -0.09 |
| pm_timed | spx | 0.05 | 0.98 | 0.08 |
| pm_timed | msci_world | 0.05 | 0.98 | 0.08 |
| pm_timed | brent | 0.02 | 1.29 | 0.10 |
| pm_timed | dollar | 0.21 | 1.33 | 0.11 |
| pm_timed | g10_carry | 0.23 | 3.27 | 0.32 |
| pm_timed | em_carry | 0.79 | 10.09 | 0.91 |
| pm_timed | d_vix | -0.0003 | -0.94 | -0.09 |
| vix_timed | spx | 0.03 | 0.75 | 0.05 |
| vix_timed | msci_world | 0.03 | 0.75 | 0.05 |
| vix_timed | brent | 0.02 | 1.60 | 0.11 |
| vix_timed | dollar | 0.40 | 2.73 | 0.21 |
| vix_timed | g10_carry | 0.17 | 3.65 | 0.23 |
| vix_timed | em_carry | 0.82 | 12.91 | 0.94 |
| vix_timed | d_vix | -0.0001 | -0.39 | -0.03 |


**Stress episodes** (cumulative return over the window):


| episode | A1+S_theory_with_dollar | A1_theory_with_dollar | A2_theory_with_dollar | base_carry | pm_timed | vix_timed |
|---|---|---|---|---|---|---|
| Iran war (Feb-Apr 2026) | -6.9% | -5.6% | 3.1% | 7.4% | 5.5% | 5.8% |
| Israel-Iran war (Jun 2025) | 1.2% | 1.0% | 1.7% | 0.6% | -0.2% | 0.6% |
| Liberation Day tariffs (Apr 2025) | 1.7% | 0.9% | 0.5% | -3.6% | -3.6% | -3.1% |
| Yen carry unwind (Aug 2024) | 2.4% | 2.5% | 2.5% | -0.1% | -0.1% | -1.1% |


**Conditional performance** (Sharpe by state):


| state | A1+S_theory_with_dollar | A1_theory_with_dollar | A2_theory_with_dollar | base_carry | pm_timed | vix_timed |
|---|---|---|---|---|---|---|
| VIX tercile: high tercile | -0.15 | 0.60 | 1.27 | 1.70 | 1.08 | 1.10 |
| VIX tercile: low tercile | -1.01 | -0.58 | -0.65 | -0.60 | 0.35 | -0.85 |
| VIX tercile: middle tercile | 2.28 | 2.67 | 2.58 | 0.90 | 0.59 | 0.81 |
| dollar month: dollar down | 0.53 | 0.87 | 0.65 | 0.69 | 0.40 | 0.39 |
| dollar month: dollar up | -0.10 | 0.76 | 1.61 | 0.67 | 1.15 | 0.16 |
| geo shock day: no | 0.15 | 0.75 | 1.00 | 0.55 | 0.60 | 0.15 |
| geo shock day: yes | 8.29 | 4.88 | 2.69 | 8.80 | 6.82 | 8.19 |
| large Brent week: no | 0.29 | 0.60 | 0.75 | 0.89 | 1.04 | 0.53 |
| large Brent week: yes | 0.30 | 2.07 | 2.61 | -0.51 | -1.13 | -1.05 |


**5 worst drawdowns: A1_theory_with_dollar** (label = news between peak and trough):


| peak | trough | recovery | depth | duration (days) | context |
|---|---|---|---|---|---|
| 2024-02-13 | 2024-07-29 | 2024-11-05 | -14.8% | 266 | US fiscal news, US monetary news |
| 2026-03-05 | 2026-08-06 | ongoing | -9.7% | 203 | US fiscal news, US monetary news, geopolitical shock |
| 2024-11-05 | 2025-02-28 | 2025-09-18 | -8.0% | 317 | US fiscal news, US monetary news, geopolitical shock |
| 2025-12-10 | 2025-12-24 | 2026-01-16 | -3.0% | 37 | other |
| 2026-01-26 | 2026-01-29 | 2026-02-02 | -1.8% | 7 | US fiscal news |


**5 worst drawdowns: pm_timed** (label = news between peak and trough):


| peak | trough | recovery | depth | duration (days) | context |
|---|---|---|---|---|---|
| 2026-06-03 | 2026-09-14 | ongoing | -10.6% | 113 | US monetary news |
| 2024-07-10 | 2024-08-05 | 2025-01-29 | -7.2% | 203 | US fiscal news, US monetary news |
| 2025-12-05 | 2025-12-29 | 2026-02-04 | -6.8% | 61 | other |
| 2025-04-03 | 2025-05-06 | 2025-09-18 | -5.5% | 168 | US fiscal news, geopolitical shock |
| 2024-04-15 | 2024-04-19 | 2024-04-29 | -3.8% | 14 | US fiscal news |


**5 worst drawdowns: base_carry** (label = news between peak and trough):


| peak | trough | recovery | depth | duration (days) | context |
|---|---|---|---|---|---|
| 2024-04-29 | 2024-11-29 | 2025-09-12 | -12.0% | 501 | US fiscal news, US monetary news, geopolitical shock |
| 2026-06-03 | 2026-09-14 | ongoing | -10.6% | 113 | US monetary news |
| 2025-12-05 | 2025-12-29 | 2026-01-23 | -6.8% | 49 | other |
| 2024-04-15 | 2024-04-19 | 2024-04-29 | -3.8% | 14 | US fiscal news |
| 2024-01-16 | 2024-03-11 | 2024-03-26 | -3.2% | 70 | US monetary news |


**P&L concentration** (Herfindahl index of absolute contributions; 1 = everything on a single item):


| strategy | dimension | HHI |
|---|---|---|
| A1_theory_with_dollar | currency | 0.14 |
| A1_theory_with_dollar | month | 0.04 |
| base_carry | currency | 0.50 |
| base_carry | month | 0.04 |
| pm_timed | currency | 0.62 |
| pm_timed | month | 0.05 |


**A versus B** (correlation with PM-timed B):


| strategy A | daily correlation | weekly correlation | drawdown correlation |
|---|---|---|---|
| A1_theory_with_dollar | 0.08 | 0.05 | 0.32 |
| A1+S_theory_with_dollar | 0.07 | 0.03 | 0.35 |
| A2_theory_with_dollar | -0.01 | 0.05 | 0.31 |
| A2+S_theory_with_dollar | -0.03 | 0.04 | 0.19 |


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
- Preliminary costs are flat; the true bid-ask (Bloomberg) may change the ranking of high-turnover variants.
- The Sharpe t (annualised Sharpe x square root of the number of years) and the 90% block-bootstrap confidence interval (blocks of 20 days, 1000 draws) show the uncertainty: over two to three years, a Sharpe below about 1.2 is not significantly different from zero.

- Base EM carry (primary universe, 2 currencies used): the most heavily weighted currency is BRL (50% of average exposure): a concentrated portfolio.
- In the preliminary run the primary universe has only a few currencies (1 versus 1): B cannot be interpreted before the Bloomberg run.
