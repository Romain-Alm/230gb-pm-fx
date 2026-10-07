# MFE 230GB Final Project: Prediction-Market Signals for Global FX Strategies

> **Note (2026-10-03, D20):** DECISIONS.md supersedes this document where they differ
> (notably D1, D2, D13 to D21). Sections 4.6, 6.1, 6.4, 7.3 and 7.4 carry inline amendments.

Project specification for implementation. This document is the single source of truth
for the replication package. Read it fully before writing code.

---

## 0. Instructions for the implementer (Claude Code)

1. **Economic logic first.** Every signal, sign convention, parameter and inclusion rule in
   this document is fixed *before* looking at backtest results. Do not tune anything on the
   test period (2026). If a choice is not specified here, ask, or pick the simplest option
   and log it in `DECISIONS.md` with the date and the reason.
2. **No look-ahead.** Every value used at time t must have been observable before t.
   Section 3 lists the known traps. Write unit tests for them (Section 12).
3. **Do not assume data schemas.** The Probalytics schema and the market-data export
   format are not yet documented here. Inspect the raw files first, write a short
   `data/SCHEMA.md` describing what you find, then build loaders.
4. **Report everything.** Themes or variants that fail are reported, not dropped.
5. **Document AI use.** All prompts used for contract classification (Section 4.2) and any
   AI-generated code that materially contributes to results are logged in `ai_log/`
   (required by the assignment).
6. **Reproducibility.** One config file, fixed random seeds, all paths relative, one
   command to rebuild every table and figure.
7. **Style.** No em dashes in any written output (README, HTML page, captions).

---

## 1. Context

### 1.1 Assignment (summary)

- Two distinct trading strategies:
  - **Strategy A:** developed / OECD markets only (currencies, short and long sovereign
    bonds, FX forwards, options allowed).
  - **Strategy B:** must involve emerging markets (we use EM FX).
- Each strategy starts from an economic hypothesis, translated into measurable signals
  and a transparent trading rule.
- At least one important part must use alternative data: we use **prediction markets**
  (explicitly encouraged by the instructor).
- Required: signal construction, portfolio formation, holding period, rebalancing,
  leverage; cumulative / average returns, volatility, Sharpe, max drawdown, turnover,
  transaction cost impact; at least one out-of-sample or robustness exercise; analysis of
  when the strategy loses money; economically meaningful risk measures.
- Grading: quality of the economic idea, use of course concepts, creativity (especially
  alternative data), empirical implementation, risk and robustness, reproducibility,
  clarity. Complexity is not rewarded per se.

### 1.2 Deliverables and deadline

- **Presentation:** Thursday, October 8, 2026, in class (3:00 to 6:00 PM). All members speak.
- **Replication package:** data (or instructions to obtain it), all code, short README,
  AI usage log.
- **Self-contained interactive HTML page:** economic idea, signals, strategy, key results,
  charts, risk analysis (Section 11).

### 1.3 Course concepts we rely on (MFE 230GB, Topics 1 to 3)

- **CIP / forward pricing:** carry is measured from forward points; NDFs for
  non-deliverable EM currencies (Topic 1).
- **Exchange rate regimes (Ilzetzki, Reinhart, Rogoff):** exclude heavily managed
  currencies from tradable universes; reserves cushion global shocks (Topic 2).
- **UIP failure and carry:** carry earns a premium for crash risk; crashes coincide with
  equity volatility spikes (Lustig and Verdelhan; Lustig, Roussanov, Verdelhan);
  downside-risk CAPM (Lettau, Maggiori, Weber 2014) (Topic 3).
- **Fiscal policy and FX:** under monetary dominance, fiscal expansion raises yields and
  the currency; under fiscal dominance (high debt, capped yields), yields rise and the
  currency falls (UK 2022, Japan 2025 to 2026); in the euro area the sovereign spread
  adjusts (Topic 3).
- **Terms of trade:** oil shocks move exporters' and importers' currencies in opposite
  directions (Topic 3, 2022 and 2026 oil shocks).

---

## 2. Data

### 2.1 Prediction markets (core alternative data)

- **Source:** Probalytics (provided through the Kairos industry project). Intraday
  probability data on prediction-market contracts (Polymarket, and other platforms if
  covered: verify).
- **Sample:** from 2024-01-01 (liquidity becomes meaningful) to latest available.
- **Needed fields (verify presence):** contract id, platform, title / question text,
  description, outcome(s), category tags if any, creation date, end / resolution date,
  resolution outcome, timestamped price or probability, volume, open interest or
  liquidity. Bracket / multi-outcome markets must keep all outcomes linked.
- If Probalytics lacks a field, public Polymarket / Kalshi APIs may complement it.
  Document any merge.

### 2.2 Market data (Bloomberg or Refinitiv via Berkeley)

- **G10 FX:** spot and 1-month forward (outright or points) vs USD, with bid and ask,
  for: EUR, JPY, GBP, CHF, AUD, NZD, CAD, NOK, SEK. Intraday or at least the 16:00 London
  snapshot (WM/Reuters).
- **EM FX:** spot and 1-month forward / NDF, with bid and ask, for: BRL, MXN, COP, ZAR,
  IDR, INR, KRW, TWD, THB, CNH (plus candidates in Section 7.1). Also the official NDF
  fixing series used for settlement (e.g. BRL PTAX, RBI reference rate, KRW and TWD
  onshore fixings, IDR JISDOR).
- **Sovereign bonds (Strategy A bond leg):** 2y, 10y, 30y benchmark yields for US,
  Germany, France, Italy, UK, Japan (and DV01 or duration to convert yield changes to
  returns). Prefer bond futures total returns if available.
- **Risk analysis series:** VIX, Brent, MSCI World and S&P 500 total return, broad dollar
  index. These are used for **risk analysis only** at this stage.

### 2.3 Traditional macro benchmarks

Deferred. Traditional signals (rate expectations, breakevens, uncertainty indices, etc.)
will be specified later, when we test prediction-market signals against them
(Section 9). Do not build them yet, but design the pipeline so that any theme index can
be swapped for an alternative series with the same timestamping.

### 2.4 Country-level fundamentals (low frequency)

- General government gross debt, % of GDP (IMF WEO), annual.
- FX reserves, % of GDP (IMF IFS), for the Strategy B extension.
- Indicator of central-bank yield capping (BoJ YCC until March 2024; large JGB purchases
  thereafter; ECB TPI backstop for euro area members). Coded by hand, documented in
  `data/manual/yield_cap.csv` with sources.
- Use the vintage available at time t (lag annual data by the publication delay).

---

## 3. Timing and alignment (critical)

All signals and returns are sampled at a common snapshot time:
**16:00 London (WM/Reuters fix)**. Store every timestamp in **UTC** and convert explicitly.

Known pitfalls, by source:

- **Different publication times across regions.** US and euro area series are not
  observed simultaneously. FRED FX rates (H.10) are noon New York rates; ECB reference
  rates come from a concertation around 14:10 CET; Treasury yields reflect late New York
  afternoon quotes; Bund yields close in Frankfurt. A US series dated day t may contain
  information released after the 16:00 London snapshot of day t: lag it.
- **Next-day publication of overnight rates.** SOFR and €STR are published the following
  business morning but dated to the prior day. Always use the publication date.
- **Daylight saving time.** The US and Europe switch on different weekends (March and
  October / November). During these weeks the New York / London gap is 4 hours, not 5.
- **Holidays.** US, UK, TARGET2 and EM calendars differ. Forward-fill and flag stale
  values; never form a signal change from a stale value.
- **24/7 prediction markets vs closed FX.** FX is closed from Friday about 17:00 New York
  to Sunday about 17:00 New York. Weekend probability changes are matched to the Sunday
  reopening gap, never to Friday's close (Section 6.6).
- **EM fixings.** NDFs settle on local fixings published at local times. Signals stay on
  the 16:00 London snapshot; NDF returns are computed on the actual settlement fixings.
- **Prediction-market snapshot.** Use the last trade or mid strictly before 16:00 London.
  If no trade in the last N hours (config, default 6), mark the contract as stale for
  that day.

---

## 4. Prediction-market processing

### 4.1 Contract universe and inclusion rules (fixed ex ante)

A contract enters a theme index on day t only if all of the following hold:

1. It exists at t (created before t, not yet resolved). Use only information available
   at t; no survivorship filtering based on later volume.
2. Trailing 7-day volume above a threshold (config, default USD 50k; robustness: 10k and
   250k).
3. Time to resolution between 3 days and 365 days (exclude the last days before
   resolution, where prices mechanically converge to 0 or 1).
4. Probability between 0.03 and 0.97 (bounded prices near the edges carry little
   information).
5. Classified into a (zone, theme) cell with a defined economic direction (Section 4.2).

### 4.2 Classification into zones and themes (LLM-assisted)

- Classify every contract by title and description into:
  - **Zone:** US, EA (euro area, with country sub-tag DE / FR / IT / ES / other),
    JP, UK, CH, AU, NZ, CA, NO, SE, CN, EM-country (ISO code), GLOBAL.
  - **Theme:** MONETARY, INFLATION, FISCAL_POLITICAL, TRADE_TARIFFS, GEOPOLITICS, OTHER.
    (Social issues are merged into FISCAL_POLITICAL; anything without a clear macro
    channel goes to OTHER and is excluded.)
  - **Direction:** which outcome is the "positive" direction for the theme
    (see sign conventions, Section 4.4), or NONE if ambiguous.
  - **Unit (if quantitative):** e.g. CPI bracket, policy-rate bracket, number of cuts.
- Use a fixed prompt and a fixed taxonomy written before classification. Store prompt,
  model name and version, raw outputs and the final labels in `ai_log/classification/`.
- Validate: hand-label a random sample of at least 200 contracts, report accuracy per
  field, fix the prompt only on that validation sample.

### 4.3 First deliverable: coverage table

Before any signal or backtest, produce `results/coverage.csv` and a heatmap:
number of eligible contracts, total volume and number of days with at least one eligible
contract, per (zone, theme) cell, per quarter since 2024. Cells with insufficient
coverage (config: fewer than 60% of trading days covered in the training period) are
excluded from signal construction. **This table decides the final list of zones and
themes.**

### 4.4 Sign conventions

Each theme index is oriented so that a higher value means:

| Theme | Higher index means |
|---|---|
| MONETARY | More hawkish expected policy (higher expected policy rate) |
| INFLATION | Higher expected inflation |
| FISCAL_POLITICAL | More expansionary fiscal outcome / higher fiscal risk (e.g. deficit-raising party wins, budget passes with larger deficit, government falls) |
| TRADE_TARIFFS | More trade restriction affecting the zone (tariffs imposed on or by the zone) |
| GEOPOLITICS | More escalation / conflict risk involving the zone |

Ceasefire, deal or de-escalation contracts enter with a negative sign.

### 4.5 From contracts to a continuous theme index

1. **Common economic unit before aggregation.**
   - Bracket markets (CPI print, policy rate at a meeting): compute the implied expected
     value from bucket probabilities (renormalize to sum to one; bucket midpoints;
     open-ended buckets at a configured distance). Output in pp (inflation) or bp (rates).
   - Policy-meeting markets: implied expected policy rate per meeting; interpolate to a
     **constant horizon** (default 6 months; robustness 3 and 12 months).
   - Binary event markets (elections, budgets, conflicts): use the signed probability.
2. **Daily change** at the snapshot: for each contract, the change in its unit since the
   previous snapshot (only if both snapshots are non-stale).
3. **Standardize** each contract's change by its own trailing volatility (60-day EWMA,
   computed with information up to t-1 only); winsorize at 5 standard deviations.
4. **Aggregate** within (zone, theme): volume-weighted average of standardized changes.
   Robustness: equal weights.
5. **Index level** = cumulative sum of daily aggregated changes (a continuous series
   despite contract turnover, like a rolled futures series).
6. **Resolution surprise (optional signal):** on the resolution day of a quantitative
   contract, realized value minus the last implied expected value. Stored separately;
   never mixed into the daily change.

### 4.6 Smoothing by theme

- MONETARY, INFLATION, FISCAL_POLITICAL, TRADE_TARIFFS: signal = EWMA of daily index
  changes (half-life config, default 5 days; robustness 1, 10, 20).
- GEOPOLITICS: two components kept separate:
  - **Escalation (amended 2026-10-03, D16):** EWMA (half-life 20 days) of the daily index
    changes, i.e. the recent escalation trend. The original "EWMA of the index level" is
    misspecified: the cumulative index is a random walk, so its z-score measures drift since
    the start of the sample, not a risk level. It is kept only as a reported variant labelled
    misspecified.
  - **Shock:** raw daily change, flagged when above k standard deviations (default k = 2).
  - **False-shock filter:** a shock is confirmed only if it persists for at least H hours
    (default 4, using intraday data) and the contract's volume over that window exceeds
    a threshold; if another platform covers the same event, the move must have the same
    sign there.

---

## 5. Relative signals

FX rates are relative prices. For a pair with base zone i and quote zone j
(e.g. EUR/USD: i = EA, j = US), the signal for theme k is:

`x_k(i,j,t) = theme_k(i,t) - theme_k(j,t)`

Only themes from the two zones of the pair enter, **except** pre-specified spillovers
(Section 6.3). Robustness: estimate the two legs separately (`theme_k(i)` and
`theme_k(j)` as two regressors) and test whether coefficients are equal and opposite.

---

## 6. Strategy A: G10 thematic prediction-market strategy

### 6.1 Hypothesis

Prediction markets update beliefs about policy, fiscal, trade and geopolitical outcomes
continuously and before prices fully adjust. Changes in country-relative theme indices
predict subsequent G10 currency excess returns (and, for the fiscal theme, long-end
sovereign bond returns), with signs given by course theory. The fiscal theme's sign
depends on the regime: monetary dominance (currency up) vs fiscal dominance (currency
down, long yields up).

*Amended 2026-10-03, before any backtest.* Fiscal dominance = high public debt AND
(capped yields OR loss of fiscal credibility); "capped yields" alone would wrongly exclude
UK 2022, our reference example. The regime is not fixed per country: it can switch within
the sample (US: November 2024, yields and USD up, monetary dominance; April-May 2025, long
yields up and USD down, fiscal dominance). It is measured ex ante by the observable
indicator defined in 6.4.

### 6.2 Universe

- Pairs vs USD: EUR, JPY, GBP, CHF, AUD, NZD, CAD, NOK, SEK (final list subject to the
  coverage table; open decision, see Section 13).
- Bond leg (fiscal theme only): 10y or 30y benchmark of US, DE, FR, IT, UK, JP, or
  2s10s / 2s30s steepeners (duration-neutral).

### 6.3 Pre-specified spillover map (fixed before backtesting)

| Pair(s) | Third-zone signal | Channel |
|---|---|---|
| EUR/USD, USD/JPY | FISCAL_POLITICAL (JP) | Japan sells Treasuries to fund interventions, pushing US yields (Topic 3) |
| AUD/USD, NZD/USD | TRADE_TARIFFS (CN) | Terms of trade, Chinese commodity demand |
| USD/NOK, USD/CAD | GEOPOLITICS (Middle East, Russia; GLOBAL tags) | Oil shock, terms of trade |
| Pairs vs JPY, CHF | GEOPOLITICS (GLOBAL) | Safe haven and carry unwinds |

Nothing outside this table enters. Geopolitics in Strategy A is **relative or targeted
spillover only**; global aggregate geopolitics belongs to Strategy B.

### 6.4 Estimation

- **Target:** next-day FX excess return of the pair (from 16:00 London t to 16:00 London
  t+1), using forward-implied carry: `rx(t+1) = Δs(t+1) + carry(t)/252`, with
  `s` = log USD price of one unit of foreign currency and `carry = s - f` (1-month
  forward, annualized). Robustness horizons: 5 and 20 days (overlapping returns, use
  Newey-West or Hodrick standard errors).
- **Model (pooled across pairs, pair-specific regressors):**
  `rx(p,t+1) = a_p + Σ_k b_k · x_k(p,t) + spillover terms + e`
  One coefficient per theme, common to all pairs; pair fixed effects.
- **Fiscal heterogeneity, modeled economically (amended 2026-10-03, before any backtest):**
  `b_fiscal(p,t) = b0 + b1 · (debt-to-GDP differential) + b2 · regime(t)`
  `regime(t)` is an observable fiscal-dominance indicator computed ex ante: the rolling
  60-day correlation between daily changes in the zone's 10-year government yield and in
  its currency (USD price of the currency; for the US, the value of the dollar against the
  G10 basket), both measured at the 16:00 London snapshot, lagged by one day. A negative
  correlation (yields up, currency down) marks the fiscal-dominance regime:
  `regime(t) = 1{corr(t-1) < 0}`. For a pair, each leg uses its own zone's regime.
  Pre-specified predictions: b0 > 0 (monetary-dominance baseline: fiscal expansion
  strengthens the currency) and b2 < 0 (the sign flips under fiscal dominance). The
  yield-cap dummy differential is kept as a robustness variant. In the theory-signed
  trading rule (DECISIONS D2) the fiscal sign is +1 when regime(t) = 0 and -1 when
  regime(t) = 1.
- **Test of the pooling restriction:** also estimate pair-specific coefficients; Wald test
  of equality. Report both.
- **Inference:** standard errors clustered by date (or Driscoll-Kraay); significance
  threshold |t| > 3 (multiple testing; Harvey, Liu, Zhu). Report all themes.
- **US inflation sub-test:** the INFLATION (US) theme is tested on USD pairs and US
  2y / 10y. Its incremental value vs breakevens is assessed in Section 9.

### 6.5 Trading rule

- **Sample split:** estimation 2024-01-01 to 2025-12-31; out-of-sample test 2026-01-01
  to latest. Also an expanding-window version (re-estimate monthly, trade next month).
- Only themes with the predicted sign and |t| > 3 in the estimation window enter the
  trading signal. Coefficients are frozen for the test period.
- **Forecast** `ŷ(p,t)` from the model. **Position** proportional to `ŷ / σ̂²`
  (σ̂ = 60-day EWMA volatility of the pair), cross-sectionally demeaned (dollar-neutral
  version) and also not demeaned (with dollar exposure, reported separately).
- **Portfolio volatility target:** 10% annualized (ex ante, 60-day covariance); gross
  leverage cap 3x; single-pair cap 30% of gross.
- **Rebalancing:** daily at 16:00 London, with a no-trade band (trade only if the target
  position changes by more than 10% of its own size) to control turnover.
- **Bond leg (fiscal theme):** when the relative fiscal signal is high for a high-debt or
  yield-capped country, short its long bond / steepener in addition to the FX position,
  sized to the same risk budget. Report FX-only and FX + bonds.

### 6.6 Weekend gap test

- Sample: **every weekend** since 2024 (not a hand-picked list).
- Signal: change in each relative theme index from Friday 17:00 New York to Sunday 17:00
  New York.
- Target: FX gap from Friday close to the first liquid price after the reopening
  (config, default Monday 07:00 London; robustness Sunday 18:00 New York).
- Regression of the gap on weekend signal changes, same signs and pooling as 6.4.
- Named episodes (e.g. Takaichi LDP win, French dissolution, Maduro, Khamenei) appear as
  **illustrations only** on the HTML page.
- Optional trading version: position taken at reopening based on weekend signal change,
  closed at Monday 16:00 London.

---

## 7. Strategy B: EM carry timed by a global geopolitical prediction-market index

### 7.1 Hypothesis

EM carry earns a premium for crash risk (UIP failure; downside-risk CAPM). Part of these
crashes are geopolitical or trade shocks. Prediction markets revise probabilities of
escalation before the realized shock, while VIX reacts at the time of the shock.
Reducing carry exposure when the global geopolitical index rises, and re-risking slowly,
should preserve most of the carry premium while cutting geopolitical crash losses and
downside beta.

### 7.2 Base portfolio: EM carry

- **Universe (candidates):** BRL, MXN, COP, CLP, PEN, ZAR, TRY, PLN, HUF, CZK, IDR, INR,
  KRW, TWD, THB, PHP, MYR, CNH. Exclude currencies classified as pegs / narrow bands by
  Ilzetzki-Reinhart-Rogoff de facto classification, and currencies with major capital
  control episodes or untradable NDF markets during the sample. Log exclusions with
  reasons. (PLN, HUF, CZK are OECD members: keep them in Strategy B only, never in A.)
- **Carry:** from forward points or NDF outright rates (`carry = s - f`, 1 month,
  annualized), **not** from policy-rate differentials (onshore and offshore rates
  diverge for NDF currencies).
- **Portfolio:** at each month-end, sort by carry; long top 3, short bottom 3 (equal
  risk weights, inverse 60-day volatility), vs USD. Robustness: top/bottom 4, long-only
  high-carry vs USD.
- **Instruments:** NDFs for BRL, COP, CLP, PEN, IDR, INR, KRW, TWD, PHP; deliverable
  forwards otherwise. Returns computed on actual settlement fixings for NDFs.
- **Volatility target:** 10% annualized on the base portfolio.

### 7.3 Timing signal: global geopolitical index

- Built from GEOPOLITICS (GLOBAL and all zones) and TRADE_TARIFFS (GLOBAL, US vs world)
  contracts using Section 4.5, oriented so that higher = more escalation / restriction.
- Contracts are signed, standardized, volume-weighted. **No weighting by estimated
  market impact** (look-ahead).
- Two components (Section 4.6): escalation (EWMA of daily changes, half-life 20 days) and
  raw daily shock with false-shock filter.

### 7.4 Timing rule (parameters fixed ex ante)

- **Exposure** `w(t)` in [0, 1] multiplies the base carry portfolio.
- **Escalation component (monthly, amended D16):** at month-end, `w_escalation = 1` if
  the escalation z-score (expanding window, data up to t only, first signal after a
  60-trading-day burn-in) is below 1; 0.5 between 1 and 2; 0 above 2.
- **Shock component (daily):** on a confirmed shock (z > 2), set `w = min(w, 0.25)` at the
  next snapshot.
- **Asymmetric re-risking:** after the last confirmed shock, `w` increases linearly back
  to `w_escalation` over 10 trading days, provided no new shock occurs.
- **Robustness grid:** shock thresholds 1.5 / 2 / 2.5; re-risk window 5 / 10 / 20 days;
  shock cut level 0 / 0.25 / 0.5. Show the full grid, not the best cell.

### 7.5 Extension (only if time allows)

- **Oil-shock reallocation:** if the confirmed shock comes from oil-relevant contracts
  (Middle East, Russia), instead of cutting, tilt toward oil exporters (BRL, MXN, COP)
  and away from importers (KRW, INR, THB, TWD, PHP).
- **Reserves:** cut first the long-leg currencies with the lowest reserves / GDP.

### 7.6 Known limitation to report

Funding-driven carry crashes (e.g. the August 2024 yen carry unwind) are not
geopolitical and are not expected to be anticipated by the index. Decompose drawdowns
into geopolitical / trade episodes vs other episodes and report timing performance in
each.

---

## 8. Transaction costs

- Use quoted bid-ask from the market-data source where available: cost per trade = half
  spread times traded notional.
- Fallback assumptions (to replace with data, then sensitivity): G10 spot / forwards
  1 to 3 bp half-spread; EM forwards / NDFs 5 to 15 bp; sovereign bonds or futures
  0.5 to 1 bp of yield-equivalent; double these on days with VIX above its 90th
  percentile.
- Roll costs: forwards rolled monthly; include the roll spread.
- Report performance gross and net; sensitivity at 0.5x, 1x, 2x, 3x costs; break-even
  cost level.

---

## 9. Benchmarks vs traditional signals (deferred)

To be specified in a later iteration. Planned structure only:

- For each theme, a traditional counterpart signal (market-implied or text-based).
- Three tests: incremental information (nested regressions, orthogonalized PM signal),
  lead-lag (Granger, both directions), strategy horse race (PM only, traditional only,
  combined).
- Strategy B: base carry vs carry timed by VIX vs by a text-based geopolitical index vs
  by the PM index.

Pipeline requirement now: every signal is a time series with the same timestamping
convention, so a benchmark series can replace or be added to any theme index without
code changes.

---

## 10. Evaluation, robustness and risk

### 10.1 Performance (each strategy, each variant, gross and net)

Cumulative return, annualized mean, volatility, Sharpe, Sortino, max drawdown and
duration, Calmar, hit rate, skewness, kurtosis, turnover (annualized, one-way), average
holding period, cost drag. In-sample and out-of-sample reported separately.

### 10.2 Robustness

- Out-of-sample 2026 (primary) and expanding-window estimation.
- Parameter grids (Sections 4, 6, 7): show distributions, not the best value.
- **Placebo:** (a) shuffle signal dates within month; (b) replace theme contracts with
  randomly drawn contracts from OTHER; (c) reverse the sign. Strategy performance should
  collapse.
- Leave-one-event-out: drop each major episode and recompute.
- Sub-periods: 2024, 2025, 2026.
- Weighting: volume vs equal weights in theme indices.
- Pooled vs pair-specific coefficients (Strategy A).

### 10.3 When does it lose money?

- List the 10 worst drawdowns with dates and the dominant news / theme at the time.
- Performance conditional on: VIX terciles, Brent large moves, dollar up / down months,
  geopolitical shock days vs other days.

### 10.4 Risk measures

- Betas to S&P 500, MSCI World, VIX changes, Brent, broad dollar, and to a standard
  carry factor (G10 and EM).
- **Downside beta** (Lettau, Maggiori, Weber 2014): beta conditional on market return at
  least one standard deviation below its mean. Report normal vs downside beta, before and
  after timing (Strategy B).
- Exposure during carry crashes and risk-off episodes (August 2024, April 2025 tariffs,
  2026 Iran war, others found in data).
- Concentration: P&L share by currency, by theme, by event, by month; Herfindahl index of
  P&L contributions.
- Liquidity: performance and costs when spreads widen.
- Country risk (Strategy B): exposure to low-reserve and high-debt countries.
- **Correlation between Strategy A and Strategy B returns** (they must be meaningfully
  different; target low correlation) and correlation of their drawdowns.

---

## 11. Deliverables: technical requirements

### 11.1 Repository structure

```
230gb-pm-fx/
  README.md                  # how to reproduce, data access, runtime
  PROJECT_SPEC.md            # this document
  DECISIONS.md               # every choice not fixed here, dated
  config/config.yaml         # all parameters
  data/
    raw/                     # not committed if licensed; instructions in README
    manual/                  # hand-coded files with sources (yield_cap.csv, exclusions)
    processed/
    SCHEMA.md
  ai_log/
    classification/          # prompts, model, raw outputs, validation
    code_generation.md       # AI-generated code that matters
  src/
    data/                    # loaders, calendars, timezone alignment
    pm/                      # classification, theme indices, shocks
    strategies/              # strategy_a.py, strategy_b.py
    backtest/                # engine, costs, metrics
    risk/                    # betas, downside beta, drawdowns, concentration
    report/                  # figures, tables, HTML build
  tests/
  results/                   # tables and figures (generated)
  site/index.html            # self-contained interactive page (generated)
  Makefile or run_all.py
```

### 11.2 Interactive HTML page (self-contained)

- Single HTML file, all data and JS inlined (library via CDN script tags allowed), works
  offline once loaded, responsive.
- Sections:
  1. Idea: why prediction markets, mapped to course concepts.
  2. Data: coverage heatmap (zone x theme), contract classification example.
  3. Signals: theme indices over time with event annotations (selectable zone / theme).
  4. Strategy A: t-stat heatmap theme x pair with expected signs, cumulative returns
     (in-sample / out-of-sample shaded), weekend gap results.
  5. Strategy B: base carry vs timed carry, exposure w(t) over time, drawdown comparison.
  6. Risk: downside vs normal beta, worst drawdowns table, concentration, A vs B
     correlation.
  7. Robustness: parameter grids, placebo results, cost sensitivity.
  8. Limitations and what the data do not support.
- Interactivity: toggles gross / net, in-sample / out-of-sample, parameter selection on
  grids, hover tooltips with event descriptions.

### 11.3 Presentation support

Export key figures as PNG / SVG in `results/figures/` for slides.

---

## 12. Tests (minimum)

- No look-ahead: for random dates, assert every input to the signal at t has a
  timestamp strictly before the 16:00 London snapshot of t.
- DST: snapshot conversion correct during US / EU DST mismatch weeks.
- SOFR / €STR (if used later): aligned on publication date.
- Contract inclusion uses only information available at t (no future volume).
- Theme index continuity across contract roll (no jump on resolution days).
- Bracket-implied expectation equals a hand-computed example.
- Backtest: positions at t use only signals up to t; returns from t to t+1.
- Cost model: a round trip on one pair reproduces the expected cost.

---

## 13. Open decisions (status 2026-10-03, see DECISIONS.md)

1. Final G10 pair list for Strategy A: all 9 pairs vs USD; the coverage table (D13) leaves
   only US cells, so the primary signal is a dollar signal (D14, D17).
2. Final EM universe for Strategy B: `data/manual/em_exclusions.csv` (CNH excluded; PEN, INR
   and TRY to verify against the IRR classification).
3. Probalytics schema and platform coverage: Polymarket and Kalshi, schema in
   `data/SCHEMA.md` (D7, D9, D10).
4. Volume threshold and staleness window: USD 50k and 6 hours, grids 10k / 250k (D11, D13,
   D19).
5. Bond leg of Strategy A: deferred (D5).
6. Traditional benchmark list (Section 9): deferred except the VIX-timed carry benchmark (D5).
7. Fiscal regime (D15), escalation component (D16), separation of A and B information (D17),
   deadline markets (D18).

---

## 14. Suggested order of work (deadline: Thursday Oct 8)

1. Inspect data, write `SCHEMA.md`, build loaders and the UTC / snapshot alignment, with
   tests.
2. Classify contracts (LLM, logged), validate on a hand-labeled sample.
3. **Coverage table** (Section 4.3), then freeze zones and themes.
4. Theme indices and shock detection.
5. Strategy B base carry and timing (simplest version first).
6. Strategy A regressions, trading rule, weekend gap test.
7. Costs, metrics, risk analysis, robustness.
8. HTML page and figures.
9. README and AI log completed.
10. Extensions (Section 7.5) and traditional benchmarks (Section 9) only if time remains.