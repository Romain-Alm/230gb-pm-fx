# Decisions log

Every choice not fixed by `PROJECT_SPEC.md`, with its date and reason. Entries are
appended, never rewritten. Decisions are recorded before the backtest they affect.

## 2026-10-03

**D1. Contract classification is deterministic (rules), not LLM-based.**
Spec 4.2 asks for LLM-assisted classification. We use a rule-based pipeline instead:
zone from the geographic entity resolver `geo_registry.resolve` (Kairos Arb project),
theme from the rule classifier `classifier_v2` (Kairos main repo) plus a hand-written
Kalshi series table, direction from fixed regex rules. Reason: fully reproducible,
zero marginal cost, no API dependency. AI involvement is limited to code written with
Claude Code, documented in `ai_log/code_generation.md`. Validation on a hand-labelled
random sample (spec 4.2) is kept.

**D2. Strategy A primary rule uses theory-given signs, with no estimation.**
The spec rule (only themes with predicted sign and |t| > 3 in 2024-2025 enter) is kept
as a reported variant. Reason: the usable training window is about 18 months
(Polymarket liquidity is thin before mid-2024; Kalshi non-US central-bank series start
in November 2025), so the gate is likely to select nothing. A sign-from-theory rule is
fully ex ante and cannot be overfit. Regressions are reported as diagnostics.

**D3. Out-of-sample period is 2026-01-01 to 2026-09-27.**
The frozen Probalytics archive ends 2026-07-21; the `probalytics_live` trades tape,
same schema, extends it to 2026-09-27. This matches the spec ("to latest"). Known
caveat: 130 raw fill days (2026-03-14 to 2026-07-21) were re-fetched on 2026-09-28,
after the tape was built; differences are below 1% per shard.

**D4. Weekend gap test uses Dukascopy hourly FX.**
Bloomberg intraday bar history covers only about 140 days, not enough for every
weekend since 2024.

**D5. Deferred items.** The bond leg (spec 6.5), constant-horizon interpolation of
implied policy rates (we use the nearest eligible meeting and "number of cuts"
markets), the extensions in spec 7.5, the traditional benchmarks in spec 9 except a
VIX-timed carry benchmark (kept because it answers the most likely question), and the
HTML page (after the October 8 presentation).

**D6. Prediction-market volume.** Computed from `amount_usd` in the trades tape,
dropping non-positive values (Kalshi sign anomaly in June 2026) and duplicate rows.
Polymarket rows are fills against individual maker orders; the sum over a transaction
is the taker notional.

**D7. Market metadata.** Union of the frozen archive `markets.parquet` and the
2026-09-24 export (needed for markets created after 2026-07-21); on conflict the export
row is kept.

**D8. Constraints from the team.** No changes outside the project folder, no LLM API
calls, no interaction with any trading account. All data access is read-only.

**D9 (amends D3). Sample end is 2026-09-24.** The live trades tape is near-empty
from 2026-09-25 (a few hundred trades per day versus about two million). Continuity
across the archive/live switch on 2026-07-21 was checked on the candidate markets
(same number of active markets and similar volume on both sides).

**D10 (amends D6). Volume is |price x size| in USD.** The tape's `amount_usd` column
has negative values on both venues (daily sums are often negative), so it is not used.
On clean rows `price x size` equals `amount_usd`.

**D11. Contract change since the previous fresh snapshot.** A contract's daily change is
measured against its previous non-stale snapshot (at most 7 days earlier), not only the
previous calendar day. Otherwise information arriving on weekends or quiet days would be
lost for contracts that do not trade within 6 hours of every snapshot. Still causal.

**D12. Causal demeaning of trading signals.** Deadline markets ("cut by date", "strike by
date") decay mechanically as time passes without the event, which gives some theme
indices a deterministic drift (US MONETARY drifts up). Trading signals use daily index
changes minus their expanding mean computed with data up to t-1. Index levels in figures
are not demeaned.

## 2026-10-03 (coverage gate, before any backtest)

**D13. Coverage result.** With the spec rule (USD 50k trailing 7-day volume, at least 60% of
weekdays covered in 2024-2025), three cells qualify: US MONETARY (94%), GLOBAL
GEOPOLITICS (77%), US FISCAL_POLITICAL (69%). All non-US G10 cells are below 10% in the
training period (at USD 10k: EA and UK FISCAL about 31%, JP MONETARY 8%). Country-relative
signals (spec 5) are therefore not feasible for most G10 pairs.

**D14. Strategy A: three pre-declared variants, all reported (team decision).**
- A1 "USD + safe haven": US MONETARY and US FISCAL drive an equal-risk G10 basket against
  USD (dollar leg); the spillover map (spec 6.3) drives the cross-section: GLOBAL
  GEOPOLITICS escalation is long JPY and CHF against the other G10 currencies, oil-relevant
  geopolitics is long NOK and CAD.
- A2 "relaxed coverage": country-relative signals (spec 5) with every G10 cell, each cell
  contributing only on days with eligible contracts (USD 10k threshold).
- A3 "spec strict": country-relative signals with only the cells that pass the coverage
  rule (equivalent to a dollar signal plus spillovers).
All three use the theory-signed rule (D2) as primary and the regression-gated rule as
variant. The conclusion compares them in-sample and out-of-sample and reports every
variant, given the multiple-testing risk this creates.

**D15. Fiscal regime is time-varying and observable (team decision, spec 6.1 and 6.4 amended).**
Fiscal dominance = high debt AND (capped yields OR loss of fiscal credibility). The regime
indicator is the rolling 60-day correlation between daily changes in the zone's 10-year
yield and in its currency (for the US, the dollar against the G10 basket), both at the
16:00 London snapshot, lagged one day; a negative correlation marks fiscal dominance.
`b_fiscal = b0 + b1 * debt_diff + b2 * regime`, with predictions b0 > 0 and b2 < 0. The
yield-cap dummy is a robustness variant. The theory-signed rule uses +1 under monetary
dominance and -1 under fiscal dominance. Reason: the US switched regime within the sample
(November 2024 versus April-May 2025, both cited in the course). The static table
`data/manual/fiscal_regime.csv` is kept only for the debt differential and the yield-cap
robustness variant.

**D16. Strategy B: "level" component replaced by a stationary "escalation" component
(team decision, spec 4.6, 7.3 and 7.4 amended; logged before any FX return is used).**
The cumulative geopolitical index is a random walk, so the expanding z-score of its level
measures drift since the start of the sample, not a risk level: it was at least 1 at 67% of
month-ends and at least 2 at 18%, which would leave the strategy half-exposed two thirds of
the time. This is a spec design error. Main rule: expanding z-score of the EWMA (half-life
20 days) of daily index changes, first signal after a 60-trading-day burn-in (at least 1 at
18% of month-ends, at least 2 at 12%). The literal rule is kept only as a reported variant
labelled misspecified. A 1-year rolling window was rejected: it needs a year of burn-in
(signal from 2025, most of the estimation window lost) and its length would be an
arbitrary detrending parameter. The component is called "escalation" in code, spec and
HTML page.

## 2026-10-03 (team review of spec and decisions, before any further backtest)

No FX return had been computed on real data when D17 to D21 were logged.

**D17. Strategies A and B use separate information.** A1's safe-haven leg (GLOBAL
GEOPOLITICS driving long JPY and CHF) used the same index as Strategy B's timing, so A and B
would trade the same information. This contradicts spec 6.3 ("global aggregate geopolitics
belongs to Strategy B"); row 4 of the spillover map was a spec error. In this pipeline every
geopolitics contract carries the GLOBAL zone and every tariff contract carries the US zone,
so the GEOPOLITICS and TRADE_TARIFFS cells (any zone, including GEO_OIL and CN
TRADE_TARIFFS) are built from exactly the contracts of B's index. Primary A1 is therefore
US MONETARY and US FISCAL (regime-signed) driving the dollar leg only. The oil leg (NOK, CAD)
is dropped from the primary because its contracts are part of B's index. The same principle
applies to A2 and A3: their primary versions exclude GEOPOLITICS and TRADE_TARIFFS. The
versions including them ("+ spillovers": safe haven JPY/CHF, oil NOK/CAD, CN trade AUD/NZD,
own-zone geopolitics and trade) are reported variants, with their return correlation to B.

**D18. Hazard-rate transform for deadline markets (replaces D12 as the primary treatment).**
For "by date" contracts (the event happens or not before a deadline), the contract value is
the implied hazard rate lambda = -ln(1 - p) / tau, with tau the time to the scheduled close
in years, floored at 3 days (the inclusion limit), and p clipped to [0.001, 0.999]. The daily
contract change is the change in lambda, standardised as before. A constant hazard no longer
produces a mechanical drift as the deadline approaches. Applies to all themes, including the
geopolitical index of Strategy B. Deadline contracts are identified by fixed title patterns
("by <date>", "before <date>", "in <year>", "this year/month/week"). The causal demeaning of
D12 is kept only as a robustness variant (on probability-based indices).

**D19. Multi-day changes are scaled to daily units.** In D11, when a contract's change spans
g > 1 days, it is divided by sqrt(g) before being standardised by its daily EWMA volatility;
the EWMA volatility is estimated on the same scaled changes.

**D20. Spec header and open decisions.** `PROJECT_SPEC.md` carries a header note that
DECISIONS.md supersedes it where they differ (notably D1, D2, D13 to D21); its section 13
points to the decisions that closed each open item.

**D21. Data for the HTML page (built later by another team member).** Every series and table
needed by spec 11.2 is exported to `results/site_data/` as CSV or JSON (theme indices,
strategy returns gross and net, exposure w(t), drawdowns, t-statistic tables, robustness
grids, risk tables), with `results/site_data/README.md` listing each file, its columns,
units and the spec section it supports. The page must be buildable from these files alone.

**D22. Preliminary results on free data (team authorised downloads).** Until the Bloomberg
export arrives, a preliminary run uses public data: Dukascopy hourly bid/ask candles (16:00
London snapshot for G10 and deliverable EM currencies; weekend gap test), FRED (VIX, Brent,
US 10-year yield, broad dollar, S&P 500 price index, OECD 3-month interbank rates, H.10 noon
spot for KRW). Forwards are synthetic, from covered interest parity with the OECD 3-month
rates lagged one month (no cross-currency basis, no NDF onshore/offshore wedge); the EM
universe is restricted to currencies with both a price and a rate (MXN, ZAR, PLN, HUF, CZK,
KRW; TRY has no OECD rate after 2008, CNH is excluded by the screen). MSCI World is proxied
by the S&P 500 price index. These results are stored in `results/preliminary_free/`,
labelled preliminary, and superseded by the Bloomberg run. The FRED API key is kept in the
git-ignored `config/secrets.local.yaml`.

## 2026-10-03 (team review of preliminary results; logged before running these analyses)

Pre-registered: D23, D24, D25. Exploratory: D26, D27 (reported as such).

**D23 (pre-registered). Managed currencies in Strategy B.** Spec 7.2 is applied literally:
every EM currency is checked against the Ilzetzki-Reinhart-Rogoff de facto classification
(latest available vintage, documented in `data/manual/em_exclusions.csv`); currencies
classified as crawling peg, narrow band or managed (fine classification below "freely
floating / managed floating with wide band") are excluded from the primary universe.
Variants: (i) the previous universe; (ii) a single-currency cap of 20% of gross exposure.
Reason: inverse-volatility weighting overweights low-volatility managed currencies, whose
risk is devaluation rather than volatility (Topic 2). Decided by the rule, not by results.

**D24 (pre-registered). Weekend gap test on hourly data.** Spec 6.6 rerun with Dukascopy
hourly FX: gap from Friday 17:00 New York to Monday 07:00 London (robustness: Sunday 18:00
New York). GLOBAL GEOPOLITICS enters on the pre-specified spillover currencies. The
Friday-noon to Monday-noon daily version is kept but labelled "not a gap test".

**D25 (pre-registered). Static versus timing decomposition of A1.** A1's positions are split
into a static part (average position over the estimation window 2024-2025, held constant)
and a timing part (position minus that average). Sharpe of each, in-sample and 2026.

**D26 (exploratory). Intraday lead-lag.** Mechanically select the top 1% hourly absolute moves
of the G10 dollar basket (Dukascopy) since 2024; event study of the US MONETARY, US FISCAL
and GLOBAL GEOPOLITICS hourly index changes from -6h to +6h (mean and confidence interval).
Same with the top 1% hourly moves of the PM indices, looking at FX from -6h to +6h.
Question: which market moves first.

**D27 (exploratory finding, no retuning).** The fiscal regime indicator (D15) is not modified.
It was active on 0.8% of days in 2025: the 2025 fiscal-dominance episode was too short for a
60-day correlation window. Reported as a finding.

**D23, rule fixed by the team before any variant result was looked at.** IRR fine
classification, monthly file `ERA_Classification_Monthly_1940-2019.xlsx` (latest vintage
available, ends 2019M12), code taken as the latest non-missing month. Primary universe: fine
codes 12 (managed floating) and 13 (freely floating); excluded: pegs, crawling pegs, all
narrow, crawling or moving bands (codes 1 to 11), freely falling (14) and unclassified
currencies (TRY: freely falling 2018M8-2019M5 then n.a.; TWD: not in the database). Reason:
B's thesis needs currencies whose exchange rate carries crash risk; managed currencies have
artificially low volatility, which biases inverse-volatility weights and risk measures.
Variants reported: "exclude coarse 1-2" (keeps codes 9 to 13), the previous universe, and a
20% single-currency cap of gross exposure. Portfolio formation becomes: long the top tercile
and short the bottom tercile of the carry sort (number per leg = floor(N/3), at least 1),
instead of 3 versus 3: 2 versus 2 with the six-currency Bloomberg universe (BRL, MXN, COP,
CLP, ZAR, KRW), 1 versus 1 with the four currencies available in free data (mechanical
check only, not interpreted). Limitation: the 2019 vintage does not see regime changes after
2019; no manual reclassification.

**Scope freeze (team, 2026-10-03).** No new variants. Remaining work: D24 and D26 on hourly
Dukascopy data, and the Bloomberg rerun. Reporting addition (no new analysis): every
performance table carries the approximate t-statistic of the Sharpe ratio (annualised
Sharpe x sqrt(years)) and a moving-block bootstrap 90% confidence interval (block 20 days,
1000 draws, seed 230), in particular for A1 total / timing / static and B base / PM / VIX.

## 2026-10-03 (market data delivery, before the definitive run)

**D28 (data integration, logged before any result on these data was looked at).** The market
delivery (`data/raw/delivery/market/`, README there) replaces the free data. Bloomberg for
every FX spot, 1-month forward and 1-month NDF (outrights = Bloomberg spot + points / scale,
scales checked by the data team) and for MSCI World net TR, S&P 500 TR, DXY and Brent;
WRDS/Cboe for VIX; official constant-maturity 10-year yields (US Treasury, Bundesbank,
Bank of England, MOF Japan) instead of the Bloomberg generic tickers. Course use only, not
redistributed (`data/raw/` is not versioned). Choices, answering the data team's questions:

- (a) Timing. No series is a 16:00 London fix. G10, LatAm, CEE, ZAR and TRY close around the
  New York close, after the prediction-market snapshot: a signal of day t trades at the
  close of t (a delay of about six hours, conservative). Asian currencies close before the
  snapshot: one-day execution lag (`close: asia` in `config/market_series.yaml`;
  `strategy_b.exec_lag_days: by_close`). In the primary B universe this concerns KRW only.
  No BFIX re-pull. Consequence for the contemporaneous diagnostics of A: the FX day
  (New York close to New York close) ends six hours after the PM day (16:00 to 16:00 London),
  which dilutes same-day coefficients slightly; predictive regressions are unaffected.
- (b) MSCI World net TR (NDDUWI) accepted. (c) Official 10-year yields accepted; they are
  local-market observations, not synchronous with the FX close (limitation of the fiscal
  regime indicator, unchanged).
- (d) Asian NDF forwards (IDR, INR, KRW, TWD, PHP, MYR) are discarded before 2011-01-01
  (erratic points in 2010). The B carry history therefore uses KRW from 2011.
- (e) Local holidays stay empty (no fill from Datastream); the loader carries the last
  price forward and forms no return from a stale value (spec 3, unchanged).
- (f) Majors from 2023-06-01 are enough (Strategy A warm-up); the 2010 history is not used.
- (g, h) Observations removed before use (all fields of that date and ticker), from the data
  team's QC file: `last_outside_bid_ask` (37 spot prints, 2010-2012), `isolated_spike` on FX
  tickers only (risk-series spikes are genuine crisis days), `wide_points_spread` (forward
  bid/ask unusable) and `premium_sign_vs_datastream` (MYR 2017, TWD 2025-26 forward windows).
  Other flags (premium outliers, mostly TRY carry moves; crossed or locked quotes) are kept.
- Costs: half of the delivered 1-month forward bid/ask spread, as the spec asks, smoothed by a
  causal 20-day rolling median (removes crossed, locked and one-day wide indicative quotes).
  These are Bloomberg end-of-day composite quotes: wide for NOK and SEK (median half-spread
  about 11-12 bp in 2024-26) and CHF (about 5 bp), probably wider than dealable spreads, so
  costs are conservative there. The cost multiplier grid (0.5x to 3x) is unchanged.

**D29 (diagnostic after the definitive results, labelled as such; no rule change).** Monthly
attribution of the gap between the PM-timed and the base carry of Strategy B, and the timed
portfolio rebuilt without the event that moved the escalation index most in the 35 days
before the best month (`key_month_check` in `src/strategies/run_b.py`). Reason: the B gain
looked concentrated in one month. Result in `results/RESULTATS.md` (section 5); the rule and
its parameters are unchanged.

**D27, value on the definitive data.** With the delivered yields and Bloomberg FX, the fiscal
regime indicator is active on 4.6% of 2025 days (0.8% on free data). The reading is
unchanged: the indicator almost never activates.

## 2026-10-03 (team review of the definitive results; partial lifting of the scope freeze)

**Partial lifting of the scope freeze.** Logged after the definitive results were seen. A draft
listing B2 and a weekly A1 had been written earlier but was never sent or logged: nothing below
is pre-registered. Exactly these items are added, and no other variant:

1. **B2, oil-shock reallocation (spec 7.5).** Label: mechanism and direction pre-specified in
   spec 7.5 (deferred by D5); implementation details fixed today, after seeing B's oil
   exposure. Rule: a confirmed shock is "oil" when oil-relevant contracts (Middle East,
   Russia-Ukraine) carry more than half of the day's aggregated change (two-day change for a
   shock confirmed the next day). A non-oil shock cuts the carry portfolio as in the primary
   rule. An oil shock does not cut it; instead it adds a tilt long the oil exporters and short
   the oil importers, sized by the cut the shock would have made and following the same
   re-risk path. Exporters BRL, MXN, COP and importers KRW, INR, THB, TWD, PHP, intersected
   with the primary universe: exporters BRL, MXN, COP; importers KRW. Tilt: inverse-volatility
   inside each leg, equal gross per leg, 10% volatility target. The escalation component is
   unchanged. Benchmark: same rule with the oil shock triggered by a Brent daily rise above
   2 EWMA standard deviations (Brent settles after the snapshot, so the move of t-1 triggers
   at t).
2. **A1 with weekly rebalancing** (weights decided on the last trading day of each week),
   a posteriori.
3. **D30, regression-gated rule at the 20-day horizon for A1 and A2.** The horizon was chosen
   after seeing the full-sample 20-day diagnostic (A1 US FISCAL, t = 3.35): this is a
   post-hoc choice. Estimation on 2024-2025 only, with targets ending inside the training
   window, pooled panel with pair effects and Driscoll-Kraay standard errors (Bartlett,
   bandwidth 20, which handles the overlapping 20-day returns). Components with the predicted
   (positive) sign and t > 3 are kept, coefficients frozen, positions rebalanced every 20
   trading days, evaluation on 2026. Net and gross, turnover, t of the Sharpe and bootstrap CI
   reported.
4. **Costs of A**: scenario at 0.5x the Bloomberg composite half-spread (composite closing
   spreads overstate tradable G10 spreads). The primary result stays at 1x.
5. **D31, B robustness, a posteriori and motivated by D29**: an index day contributes to the
   escalation measure and to shock confirmation only if at least 3 distinct events have
   eligible contracts that day. The primary B rule is unchanged.
6. **Presentation**: B is presented as "EM carry (IRR 12-13 universe) with a PM geopolitical
   overlay", with D29 next to the PM-timed result.

**Placebos of the a posteriori additions (reporting only, 2026-10-03).** Placebos (a), (b), (c)
with 100 draws for A1 weekly, A1 gated 20-day (D30: frozen component and coefficient applied to
the placebo signals, no re-estimation), B2 and D31 (`results/robustness/posthoc.csv`, run by
`run_all.py --stage robustness`). The Brent benchmark has no prediction-market signal and gets
no placebo. No new variant.

## 2026-10-03 (final review checks and final freeze)

**D30 sanity checks (no rule changed; reported next to D30 in `results/RESULTATS.md`).**
`src/strategies/d30_checks.py`, outputs in `results/strategy_a/d30_checks/`: (1) phase
robustness of the frozen rule over the 20 possible start offsets of the 20-day rebalancing;
(2) days long and short USD, sign changes, monthly P&L in 2026; (3) static and timing
decomposition (D25 method) plus two ex post benchmarks (2026 average position, 2026 average
direction at full size); (4) effective-sample OLS on the dollar basket with non-overlapping
20-day returns, 2024-2025 and 2026. B2 and its Brent version have no fixed rebalancing cycle
(month-end carry, daily overlay), so the phase test does not apply to them. Reading: the
published phase is the best of the 20 in every period; the 2026 Sharpe averaged over phases is
far below the published one and the effective-sample regression is not significant. D30 is
reported as an exploratory lead, not a result. Strategy B summary: 18 of 19 confirmed shocks are
classified as oil-related, so B2 almost always tilts instead of cutting.

**Final freeze.** No further rule, variant or parameter change. Remaining tasks: hand validation
of the 200-contract sample (accuracy per field: theme, zone, direction, via
`python -m src.pm.validation score`), figures for the slides, HTML page.

## 2026-10-06 (reporting additions; scope frozen, no rule, variant or parameter change)

Reporting only, no new strategy:
- **Leverage and exposure** (`src/risk/leverage.py`, `results/risk/leverage.csv`): gross and net USD
  exposure (mean, median, 95th percentile, max) for A1, A2, A1 weekly, base carry, PM overlay,
  VIX overlay and B2, by period; share of days on which Strategy A's 3x gross cap and 30%
  per-pair cap bind (measured on the daily targets before the no-trade band, through a helper
  shared with the volatility target, `engine.cap_flags`; results unchanged); realised versus
  target volatility. Strategy B has no cap in its rule.
- **Turnover and cost columns** filled for every Strategy B variant (coarse12, previous, cap20,
  level, D12).
- **Liquidity risk**: performance by tercile of the strategy's own average 1-month forward
  half-spread (causal 20-day median, value known at t-1), in `results/risk/conditional_performance.csv`.
- **Slide figures** in `results/figures/slides/` (1920 x 1080 PNG and SVG, no in-figure title),
  data exported to `results/site_data/slide_*.csv`; existing figures unchanged.
- **Replication package**: README rewritten (one command, runtime, Python 3.13.13, data access per
  source, vendored Kairos code); `requirements.txt` pinned to the working environment;
  `ai_log/code_generation.md` completed for every phase; `ai_log/design_conversations.md`
  created, to be filled from the team's exports.
- **Validation sheet** split into `validation_sheet_1.csv` to `_4.csv` (50 rows each);
  `src.pm.validation.score` merges them. The scoring is not run before the sheets are labelled.

## 2026-10-07 (submission package)

**Confidential inputs are not in the repository.** The prediction-market data (Probalytics,
through the Kairos industry project), the contract-level panels derived from them
(`data/processed/`) and the Kairos classification code (`src/pm/vendor/`) are confidential and
not versioned; nothing from Kairos is included. The README states it. All results stay in
`results/`; without these inputs the `pm` stage cannot run and the tests that need them are
skipped. No rule, variant or parameter change.

**Everything in English (2026-10-07).** All deliverables are in English, because parts of them go
into the LaTeX report. `results/RESULTATS.md` is replaced by `results/RESULTS.md`, generated in
English by `src/report/summary_md.py` (same numbers); the earlier entries of this log that cite
`RESULTATS.md` refer to it. The progress notes moved from `avancement/` to `progress/` and were
translated. No rule, variant or parameter change.
