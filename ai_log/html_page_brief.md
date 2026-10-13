# Interactive HTML page: design brief and data contract

Written 2026-10-10 for whoever builds `site/index.html`: a Claude Code session working inside
`GB/230gb-pm-fx/` (recommended path), or Claude web producing a first template from this brief
(path 2, section 9). The oral presentation of 2026-10-08 (`GB/PRESENTATION.txt`, 17 slides with
speaker notes) is the narrative to follow. The page is the last deliverable of the project
(assignment: "a self-contained interactive HTML page showcasing the economic idea, signals,
strategy, key results, charts, and risk analysis").

---

## 0. Hard constraints

From `PROJECT_SPEC.md` section 11.2 and the standing rules (`01_RULES_AND_PREFERENCES.md`):

1. **One file**, `site/index.html`. All data and JavaScript inlined. A charting library may come
   from a CDN script tag, but inlining it is safer: the grader may open the file from a zip with
   no network. Responsive (phone width must work, no horizontal scroll).
2. **Generated, never hand-edited.** A script (`src/report/build_site.py`) reads
   `results/site_data/*.csv` and writes the page. Every number on the page comes from a data file.
   This is the same rule as `results/RESULTS.md` ("nothing is typed by hand"). The build is hooked
   into `run_all.py` (stage `figures`, or a new stage `site`).
3. **English only. No em dash anywhere** (the long dash character), in text, captions, tooltips or
   code comments. Use commas, colons or full stops.
4. **Status badges.** Everything added after the freeze is labelled: weekly A1, the 20-day gated
   rule (D30), costs at 0.5x, B2, the 3-events filter (D31). The page uses three badges:
   `pre-registered`, `a posteriori`, `exploratory`. The 2.46 Sharpe of D30 is shown only inside a
   panel titled "Not a result".
5. **Sections required by the spec** (11.2): Idea, Data, Signals, Strategy A, Strategy B, Risk,
   Robustness, Limitations. Interactivity required: gross / net toggle, in-sample /
   out-of-sample, parameter selection on grids, hover tooltips with event descriptions.
6. **Course concepts named explicitly** where they motivate a choice (assignment section 2):
   carry and UIP failure, crash risk, monetary vs fiscal dominance, terms of trade, IRR regime
   classification, CIP and forward pricing, downside-risk CAPM, efficient markets.
7. **Logging.** One entry in `DECISIONS.md` (dated, "reporting: HTML page"), one row in
   `ai_log/code_generation.md`, a line in `README.md` (how to rebuild and open the page).
8. **Confidentiality.** The page may show aggregated series and the 60 example contract titles
   already exported in `classification_examples.csv`. No raw Kairos data, no contract-level panel.

---

## 1. What the page should feel like

A long, scrollable research page, not a slide deck. Each section opens with one sentence that
states the claim, then one main interactive figure, then stat cards, then a collapsible
"Details" block with the full table and the method. The reader who only skims gets the story
from the claims and the figures; the reader who cares opens the details.

Principles:

- **Answer up front.** The hero repeats slide 17 (three cards: Timing, Content, Carry).
- **Progressive disclosure.** Nothing important hidden, nothing secondary shown by default.
  `<details>` blocks for method, full tables and variant lists.
- **Same honesty as the talk.** The best-looking numbers (A2 gross 1.43, PM-timed 1.30, D30 2.46)
  are always shown next to the reason they are not the headline.
- **Every chart answers one question**, written as its caption, in the form of a claim.
- **Sticky navigation** with the 10 section names and a progress indicator.

---

## 2. Technical approach

### 2.1 Build pipeline (recommended)

```
src/report/site/template.html    page skeleton with {{DATA}} and {{CSS}}, {{JS}}, {{PLOTLY}} slots
src/report/site/site.css         styles (tokens on :root)
src/report/site/site.js          rendering code, reads window.DATA
src/report/site/vendor/plotly-basic.min.js   vendored once (about 1.1 MB)
src/report/build_site.py         reads results/site_data, builds window.DATA, writes site/index.html
site/index.html                  output, committed so the grader can open it without rebuilding
```

`build_site.py`:

1. Reads the CSVs listed in section 7 and the new exports of section 6.
2. Computes derived series at build time (cumulative returns in percent from daily returns,
   drawdowns, placebo histograms as bin counts, confirmed-shock table, percent-of-placebos-beaten,
   mean over the 20 D30 phases). Keeping these computations in Python keeps the JS simple and
   lets a test compare page numbers with `results/RESULTS.md`.
3. Rounds floats (4 significant digits for returns, 3 for statistics) and emits
   `window.DATA = {...}` (schema in section 10). Target: under 1.5 MB of JSON.
4. Inlines CSS, JS and the chart library, writes `site/index.html`. Expected size: 3 to 4 MB.
5. Asserts: no em dash in the output; every headline number of section 8 is present in DATA.

### 2.2 Charts

Recommended: **Plotly.js basic bundle, inlined**, with one shared layout template (font, colours,
no modebar, unified hover). It gives hover tooltips, zoom, legend toggles and responsive resize
for free, which is most of the required interactivity.

- The basic bundle has scatter, bar and pie only. Heatmaps (coverage, t-stats, B grid) are built
  as HTML tables with coloured cells, which is better anyway: they need a slider and click
  handlers. Histograms are bar traces of bins computed in Python. Confidence bands are two scatter
  traces with fill.
- Source: `https://cdn.plot.ly/plotly-basic-2.35.2.min.js`, downloaded once into
  `src/report/site/vendor/` and committed. Fallback if no network: `plotly.offline.get_plotlyjs()`
  from the `plotly` Python package (full bundle, 3.6 MB).
- Alternative, if a fully custom look is wanted: hand-written inline SVG (line, bar, heatmap,
  histogram) with a small helper; more code, no dependency. Only worth it if time allows.

If a Claude Code session builds the charts, load the `dataviz` skill before writing chart code
and use its palette validator.

### 2.3 Visual design

- Light theme, optional dark mode through `prefers-color-scheme` (tokens on `:root`).
- Palette, matching the slides: ink `#1f2937` for text, grey `#6b7280` for base carry and
  secondary lines, blue `#1f5fa8` for prediction-market lines and the "kept" state, red `#c0392b`
  for VIX and losses, sand `#efe3c2` for shaded windows (June 2024, Iran war), light blue
  `#dbe7f5` for out-of-sample shading, green `#2e7d32` only for "passes the gate" or positive
  stress returns. Status badges: pre-registered (blue outline), a posteriori (amber), exploratory
  (grey, dashed).
- Typography: Inter or the system stack; numbers in tabular figures; captions 14 px.
- Layout: max width 1100 px, 16 px gutters on phones, charts 380 to 440 px tall, stat cards in a
  responsive grid (4 per row on desktop, 2 on phones).

---

## 3. Page structure and interactions, section by section

Each block gives: content, main figure, interactions, data (file names refer to
`results/site_data/` unless stated), key numbers (source column in brackets).

### Hero: "Prediction markets and currency strategies"

- Question: "Do Kalshi and Polymarket carry information that helps trade currencies, and where
  does that information sit?" Authors, Berkeley Haas, MFE 230GB, October 2026.
- Three answer cards (slide 17): Timing (move with FX, not before: same day t = 4.0, next day
  t < 1), Content (usable information is about the dollar: only US monetary, US fiscal and global
  geopolitics are liquid), Carry (EM carry earns a premium, net Sharpe 1.25; the overlay's gain
  comes from one contract in one month).
- Sample line: Jan 2024 to 24 Sep 2026, in-sample 2024-25, out-of-sample 2026, every rule logged
  before its backtest (31 dated decisions).
- A legend for the three status badges.
- Interaction: each card scrolls to its section.

### Section 1. Idea: three course mechanisms set the sign of every trade

- Three clickable mechanism cards (slide 2). Each expands into a causal chain drawn as boxes and
  arrows, the strategy that uses it, and the course topic:
  1. **Carry and the failure of UIP** (Strategy B): rx = (i* - i) + delta s; UIP says E[delta s]
     = i - i*, carry earns zero; in the data high-rate currencies fall by less, so carry earns a
     premium read as compensation for crash risk.
  2. **Monetary vs fiscal dominance** (Strategy A): hawkish Fed news lifts the dollar in both
     regimes; a bigger deficit lifts the currency under monetary dominance (rates up, capital in)
     and lowers it under fiscal dominance (risk premium, capital out), as in the UK in 2022 and the
     US in April and May 2025.
  3. **Terms of trade** (explains B's results): oil up lifts exporters (BRL, MXN, COP) and hurts
     the importer (KRW). A book long BRL, MXN, COP and short KRW gains on Middle East escalation.
- Secondary list of concepts used elsewhere: IRR regime classification (B universe, codes 12-13
  only), CIP and forward pricing (carry measured from forward and NDF points), downside-risk CAPM
  (risk section), efficient markets (timing section).
- Data: static text. No numbers beyond the formulas.

### Section 2. Data pipeline: from 80,000 contracts to daily theme indices

- Five-step stepper (slide 3), each step opens its example:
  1. Contracts: 80,203 markets with trades, USD 11.2 bn (Kalshi 50,281 and 2.28 bn; Polymarket
     29,922 and 8.88 bn) [new export `pm_summary.csv`, section 6].
  2. Classify by theme, zone, direction with fixed rules, no language model.
  3. Hazard rate for deadline contracts: lambda = -ln(1 - p) / tau.
  4. Standardise: each contract's daily change divided by its own EWMA volatility, signed.
  5. Average: volume-weighted within a (zone, theme) cell, one index per cell.
- **Hazard-rate calculator** (interactive, pedagogical): two sliders, p (0.05 to 0.95) and tau
  (5 to 365 days). Shows lambda, and a small chart of a contract whose hazard is constant: its
  raw probability decays to zero as the deadline approaches while lambda stays flat. This is the
  one-figure answer to "why not use the raw probability".
- Classification summary: stacked bars of markets by theme and platform, with "usable" share on
  hover (`classification_summary.csv`).
- **Contract explorer**: table of the 60 example contracts, filter chips by theme and platform,
  columns title, theme, zone, direction, rule used (`classification_examples.csv`). The point is to
  show that the rules are legible: "text:strikes, geo:escalate:strike" next to "Israel strikes
  Yemen by August 15?".
- Timing card: snapshot at the last trade before 16:00 London, trade at the NY close (KRW next
  Asian close), stale after 6 hours, eligibility 50k USD weekly volume, 3 to 365 days to close.
- Hand-validation note: 200 events to be labelled by the team; score shown when available.

### Section 3. Coverage gate: prediction markets speak about the US and the world

- **Heatmap zone x theme** as an HTML table (16 zones x 5 themes), cell = share of weekdays with
  liquid contracts, cell colour by share, bold when it passes the gate. Built from
  `coverage_cells.csv` (zones absent from the file get 0).
- **Gate slider** (default 60%): cells above the gate turn blue, a counter reads "3 cells pass".
  The reader can drag it and see that any cutoff from 53% to 68% keeps the same three cells
  (US geopolitics is at 52.6%, US fiscal at 68.5%).
- **Period toggle** "2024-25 (training)" / "2026": the 2026 view shows coverage growing (UK fiscal
  55%, Japan monetary 19%, US tariffs 24%, euro area fiscal 18%) [`share_test`].
- **Threshold toggle** 50k / 10k USD [new export `coverage_cells_v10k.csv`]: at 10k, five cells
  pass, including China geopolitics and US geopolitics; this is what A2 uses.
- Details: full table with contracts, events and volume per cell.
- Consequence callout: Strategy A trades the dollar; Strategy B uses global geopolitics; nothing
  country-relative is feasible in the G10 during 2024-25.
- Key numbers: US monetary 93.9%, global geopolitics 76.7%, US fiscal 68.5% [`share_train`].

### Section 4. Signals: theme indices over time

- Line chart of the volume-weighted index for a selectable cell (dropdown: the three kept cells
  first, then any cell with coverage above 5% in either period). Below it, a bar strip with the
  number of contracts behind the index each day (`theme_indices.csv`: day, zone, theme,
  index_vw, n_contracts).
- Event annotations as markers with hover labels (`annotations.json`), shown on the cells they
  belong to. Out-of-sample shading from 2026-01-01. Range buttons: 6 m, 1 y, all.
- Toggle: volume-weighted / equal-weighted index (`index_ew`), to show the aggregation does not
  drive the shape.
- Details: how a cell index is formed (steps 3 to 5 of section 2), the EWMA span (60), the
  staleness rule.
- Data budget: about 10 cells x 1,000 days x 3 numbers, roughly 300 KB.

### Section 5. Timing: is the information early?

- **Horizon table** (slide 5): rows same day, 1 day, 5 days, 20 days; columns Monetary, Fiscal;
  cell = Driscoll-Kraay t-statistic, coloured; hover shows coefficient, standard error, number of
  observations (`strategy_a_tstats.csv`, models `A1_contemporaneous` and `A1_predictive`).
  Values: 4.02 / 0.33 (same day), 0.75 / 0.93 (1 d), 1.02 / 1.92 (5 d), -0.46 / 3.35 (20 d).
  The 20-day fiscal cell links to the "Not a result" panel of section 6.
- **Hourly lead-lag event study** (slide 5, exploratory badge): selector among the six studies
  (FX top 1% to PM for each of the three cells, and PM top 1% to the dollar basket), mean
  response with 95% band, vertical line at hour 0, event count in the subtitle
  (`slide_leadlag.csv`). Reading: FX moves first or together; monetary odds follow in the same and
  next hour.
- **Weekend gap test** (pre-registered badge): card with 1,278 pair-weekends, largest |t| = 1.3,
  null result; details table of the regressions (`strategy_a_weekend_gap.csv`); optional
  distribution of weekend changes per cell (`weekend_changes.csv`).
- Claim: for liquid G10 FX this is the efficient-markets outcome.

### Section 6. Strategy A: do US policy odds predict the dollar against the G10?

- **Rule card** (slide 6): universe (9 G10 currencies vs USD, inverse-variance basket), signal
  (daily index change, 5-day half-life, scaled by its own volatility), execution (16:00 London
  signal, NY close), sizing (10% vol target, caps 3x gross and 30% per pair), costs (half the 1M
  forward bid-ask, 20-day median). Two channel cards: monetary (hawkish shift, long USD, every
  regime) and fiscal (expansion, long USD; short USD under fiscal dominance, detected by a 60-day
  rolling yield-FX correlation below zero: active on 12 days of 2025, 0 in 2024 and 2026) [new
  export `fiscal_regime_days.csv`].
- **Main chart: cumulative returns** (`strategy_a_returns.csv`, cumulated at build time in
  percent). Variant chips: A1 (primary), A2, A1 + geopolitics, A2 dollar-neutral, A1 weekly (a
  posteriori), A1 and A2 at 0.5x costs (a posteriori). Toggle gross / net. Out-of-sample shading.
  Event markers from `annotations.json`. Hover: date, value, variant.
- **Stat cards** bound to the selected variant and a period selector (full / 2024-25 / 2026):
  Sharpe, Sharpe t, 90% CI, annual return, volatility, max drawdown, turnover, cost drag
  (`strategy_a_performance.csv`).
- **Sharpe ladder** (slide 7): horizontal bars with 90% CI whiskers for A1 gross 0.88, A1 net
  0.43, A2 gross 1.43, A2 net 0.81, A2 dollar-neutral net -0.95, A1 + geopolitics net -0.21.
  Caption: costs halve the edge; country cells help only through the dollar; the cross-country
  part alone loses; adding geopolitics hurts.
- Cost card: turnover 133x a year, cost drag 4.7% a year, about 7 bp earned against 3.5 bp paid
  per unit traded; Bloomberg composite spreads are probably wider than dealable, so costs are
  conservative.
- Out-of-sample card: A1 net 0.28 (gross 0.85), A2 net 1.08; the monetary leg drives A1, long USD
  into the September 2026 hike (+5.5% in the FOMC window).
- **Robustness panel** (slide 8, a table plus three small charts):
  - Placebo histogram: 200 date-shuffled Sharpes, the actual marked, "A1 beats 92%, A2 99%"
    (`robustness_a.csv`, test `placebo_a_shuffle`).
  - Leave-one-event-out strip: 10 points per variant, A1 stays between 0.23 and 0.63.
  - Static vs timing: gross 0.32 vs 0.81 [new export `decomposition_static_timing.csv`].
  - Half-life sensitivity (8 values), equal weights, reversed signs (placebo c), random contracts
    (placebo b): in the details table.
  - Dollar momentum benchmark: 1-day and 5-day momentum lose (gross Sharpe -1.05 and -0.54); A1's
    beta on 5-day momentum 0.19 with alpha about 10% a year (t 1.8) [new export from
    `results/notes/strategy_a_checks`].
  - Spec gated rule (|t| > 3 to trade): selects nothing, largest t = 1.68.
  - Rows marked with the a posteriori badge: weekly (net 0.75, turnover 63), costs at 0.5x (A1
    0.65, A2 1.12).
- **"Not a result" panel** (exploratory badge): the 20-day rule. Bar chart of the 2026 Sharpe for
  each of the 20 rebalancing start offsets (`d30_phase.csv`), offset 0 (ours, 2.46) highlighted,
  a line at the mean 0.22, 12 of 20 positive; period toggle (2024-25, 2026, full); non-overlapping
  regression t = 0.72 (`d30_effective_sample.csv`). Lesson in one line: test every rebalancing
  phase.

### Section 7. Strategy B: EM carry timed by a geopolitical index

- **Mechanism 1, the carry** (slide 9): universe chips with IRR codes (BRL, MXN, COP, CLP, ZAR,
  KRW; pegs and bands excluded; KRW trades with a one-day lag); monthly sort on the 1-month forward
  or NDF premium; long top two, short bottom two; inverse-vol weights, 10% vol target. Long-history
  cards: Sharpe 0.33, max drawdown -43.7%, excess kurtosis 2.7 over 17 years [new export
  `base_carry_long_history.csv`], with an optional long-history cumulative curve [new export
  `base_carry_long_history_returns.csv`]. Claim: losses come in bursts in global risk-off, so the
  premium looks like crash-risk compensation.
- **Mechanism 2, the overlay** (slide 10): two stacked charts sharing the x axis.
  1. The global geopolitics index with its escalation z-score and the 19 confirmed shocks as bars
     whose height is the number of contracts behind the shock (`geo_signals.csv`: index,
     escalation_z, confirmed, n_contracts). Hover: date, contracts, nearest annotation. The late
     2024 shocks rest on 1 to 3 contracts; the Iran war of 2026 on up to 39.
  2. Exposure w(t) in [0, 1] (`strategy_b_exposure.csv`): w, w_escalation as a lighter line,
     shock days as markers; toggle to overlay the VIX version. Caption: average exposure 0.81,
     reduced on 211 of 714 days. The June 2024 cut (monthly rule, one Taiwan contract) is
     annotated.
  - Rule card: escalation (monthly expanding z-score of an EWMA of daily changes, half-life 20
    days, scales exposure down) and shock (a move above 2 sd that persists cuts exposure to 25%,
    restored over 10 days). "Cut fast, re-risk slowly."
- **Main chart: cumulative net returns** (slide 11 and the slide figure): base carry (grey),
  PM-timed (blue), VIX-timed (red), PM-timed without the Taiwan contract (dashed blue), June 2024
  shaded; out-of-sample shading; per-line toggles; gross / net toggle (`strategy_b_returns.csv`,
  cumulated at build). A drawdown panel below with the same lines (`drawdowns.csv`).
- **The one-month decomposition**: three bars, June 2024 alone +6.3 points, all other months
  -10.4, total -4.1 [new export `key_month_check.csv`]. A toggle "remove the Taiwan contract"
  switches the stat cards to `pm_timed_without_event`: Sharpe 1.00, drawdown -13.1%.
- **Sharpe ladder** with 90% CIs: PM-timed 1.30, base carry 1.25 (CI 0.33 to 2.31, t 2.1), without
  Taiwan 1.00, VIX-timed 1.12, B2 oil tilt 1.37 (a posteriori), 3-events filter 0.89 (a
  posteriori). Out-of-sample 2026: base carry 2.03. Costs 0.4% a year (monthly trading).
- **Why the overlay fails** (slide 12): composition chart, average position per currency with the
  weekly Brent beta as a label: COP +40% (beta +0.02), BRL +33% (0.00), MXN +31% (-0.01), ZAR 0
  (-0.06), CLP -44% (-0.05), KRW -61% (-0.06) [`slide_b_composition.csv`, needs a currency column,
  section 6]. Three reason cards: long oil (Brent beta t = 4.5, equity beta 0; the oil exposure
  comes from the two short legs), escalation helped (Iran war Feb-Apr 2026: base +8.0%, PM-timed
  +5.9%), no crash to insure (yen unwind Aug 2024: -1.3%; the -43.7% drawdown is in the long
  history, not in the window).

### Section 8. Risk: when the strategies lose money

- **Stress episodes table** (slide 13): four episodes (yen carry unwind Aug 2024, Liberation Day
  Apr 2025, Israel-Iran war Jun 2025, Iran war Feb-Apr 2026) x four strategies (A1, A2, base
  carry, PM-timed), cells coloured by sign, hover shows the worst day (`risk_episodes.csv`).
  Clicking an episode highlights its window on the cumulative charts of sections 6 and 7
  (optional, nice to have).
- Worst drawdowns: A1 -14.1% (Mar to Jul 2026, still open, overlapping the Iran war); base carry
  -14.0% (Apr to Sep 2024). Table of the worst drawdowns per strategy with peak, trough,
  recovery, depth and the dominant-news tag (`risk_worst_drawdowns.csv`), strategy selector.
- **Factor exposure**: grouped bars of weekly betas (S&P 500, MSCI World, VIX, Brent, dollar, EM
  carry) per strategy, t-statistic on hover, strategy selector (`risk_betas.csv`). Reading: A1 is
  neutral; A2 is hedge-like (MSCI beta -0.24, t -2.0); B is a commodity carry (Brent t 4.5).
- **Downside vs normal beta** (downside-risk CAPM, Lettau, Maggiori and Weber): dumbbell chart,
  one row per strategy, market selector (MSCI World, EM carry) (`risk_downside_beta.csv`). About 0
  for A1 and B, -0.81 for A2; in the 21 worst equity weeks the carry earns +12 bp on average.
- **Concentration**: share of absolute P&L by currency and by month, HHI (`risk_concentration.csv`).
  KRW is 29% of the carry's exposure, always short.
- **Conditional performance**: Sharpe by VIX tercile, dollar month, Brent week, shock day and
  own-spread tercile, conditioner selector (`risk_conditional.csv`). Liquidity result: base carry
  Sharpe 2.38 in the low-spread tercile against 0.64 in the high-spread one.
- **Leverage**: gross exposure mean, p95, max; share of days the caps bind (A1: 30% pair cap on
  18.4% of days, 3x gross cap on 0.6%); realised vs target vol (`risk_leverage.csv`).
- A vs B card: daily return correlation -0.04, weekly -0.17 (`a_vs_b_correlation.csv`).

### Section 9. Robustness: parameter grids, placebos, costs

- **Placebo histograms** for A1, A2, PM-timed B (and the a posteriori variants from
  `robustness_posthoc.csv`): actual marked, share beaten (A1 92%, A2 99%, B 93%). Random-contract
  placebo for B: 1.10, so B's Sharpe is mostly the carry (`robustness_b.csv`).
- **B parameter grid**: shock threshold (1.5, 2.0, 2.5 sd) x re-risk days (5, 10, 20) as a
  coloured table of Sharpe, with a selector for the cut level (0, 25%, 50%); the chosen cell
  (2.0, 10, 25%) outlined (`robustness_grid_b.csv`, 27 combinations). Hover: max drawdown,
  annual return.
- **Cost sensitivity**: B at 0.5x, 1x, 2x, 3x (Sharpe 1.38, 1.30, 1.15, 1.00)
  (`cost_sensitivity_b.csv`); A at 1x vs 0.5x (performance rows `_cost0.5x`).
- **Subperiods**: Sharpe by calendar year per strategy (`subperiods.csv`).
- Details: equal weights, volume thresholds, half-life grid, leave-one-event-out for B (10 events).

### Section 10. Protocol, limitations, replication

- **Protocol cards** (slide 14): pre-registration (31 dated decisions, post hoc additions
  labelled), out-of-sample (anything estimated uses 2024-25; 2026 reported separately),
  uncertainty (block-bootstrap 90% CIs, blocks of 20 days, 1,000 draws; with under three years a
  Sharpe below about 1.2 is not significant), placebos, costs (0.5x to 3x), full reporting of
  every declared variant.
- **What the data do not support** (spec section 8 of the page): no next-day predictability of
  G10 FX from US policy odds; no country-relative G10 signal (coverage); no evidence that the
  geopolitical overlay protects the carry (no crash in the window, one lucky month); the D30
  20-day result; the fiscal sign conventions for shutdowns rest on a generic rule; the
  classification has not been hand-validated yet; costs rely on Bloomberg composite spreads;
  2.7 years of data.
- **Replication**: one command rebuilds every table, figure and this page; pinned environment;
  decision log; AI log; data access documented per source, some data confidential.
- **Natural extensions** (slide 16): Kalshi vs Polymarket disagreement on the same FOMC meeting,
  non-US cells as coverage grows, a bond leg for fiscal news, OIS and fed funds futures as a
  benchmark for Fed news, regime detection on fiscal news days only.

---

## 4. Interaction catalogue

| Interaction | Where | State |
|---|---|---|
| Gross / net toggle | sections 6, 7 | one global switch, default net |
| Period selector (full, 2024-25, 2026) | stat cards of 6, 7 | per section |
| Out-of-sample shading | every time chart | always on |
| Variant chips | section 6 chart, section 7 lines | per chart |
| Hover tooltips with event labels | sections 4, 6, 7 | `annotations.json` |
| Coverage gate slider, period and threshold toggles | section 3 | local |
| Cell dropdown, VW / EW toggle, range buttons | section 4 | local |
| Lead-lag study selector | section 5 | local |
| D30 phase bars with period toggle | section 6 | local |
| "Remove the Taiwan contract" toggle | section 7 | switches cards and dashed line |
| VIX overlay toggle on exposure chart | section 7 | local |
| Episode click highlights the window on charts | section 8 | optional |
| Strategy, market and conditioner selectors | section 8 | local |
| Cut-level selector on the B grid | section 9 | local |
| Hazard-rate calculator sliders | section 2 | local |
| `<details>` blocks for method and full tables | every section | closed by default |

Keyboard and screen readers: every control is a native `<button>`, `<select>`, `<input
type=range>` or `<details>`, with a visible label.

---

## 5. Content rules for the writer

- Captions are claims, one sentence, no jargon the slides did not use.
- Numbers come from DATA at render time, including those in prose (use `<span data-key=...>`
  placeholders filled by JS, or Python string formatting at build time). This is how the page
  stays consistent with `RESULTS.md` after a rerun.
- Each a posteriori or exploratory item carries its badge in the same line as its number.
- Write "prediction markets" in full, "PM" only in chart legends. "Out-of-sample" with a hyphen.
- Units: Sharpe ratios with two decimals, returns and drawdowns in percent with one decimal,
  t-statistics with one or two decimals, shares in percent.

---

## 6. Exports to add to `src/report/site_data.py` before building

All sources exist in `results/`; they are not in `site_data/` yet.

| New file | Source | Why |
|---|---|---|
| `pm_summary.csv` | the table of RESULTS.md section 1 (markets with trades, market-days, volume by platform) | hero and section 2 totals (80,203 markets, USD 11.2 bn) |
| `coverage_cells_v10k.csv` | `results/coverage_cells_v10k.csv` | threshold toggle in section 3 |
| `base_carry_long_history.csv` | `results/strategy_b/base_carry_long_history.csv` | long-history cards in section 7 |
| `base_carry_long_history_returns.csv` | `results/strategy_b/returns_long_history.parquet` | optional long-history curve |
| `key_month_check.csv` | `results/strategy_b/key_month_check.csv` | June 2024 decomposition |
| `decomposition_static_timing.csv` | `results/strategy_a/decomposition_static_timing.csv` | static vs timing in section 6 |
| `fiscal_regime_days.csv` | `results/strategy_a/fiscal_regime.csv`, count of regime days per zone and year | regime card in section 6 |
| `momentum_benchmark.csv` | tables under `results/notes/strategy_a_checks/` (see `strategy_a_checks.md`) | momentum rows in section 6 |
| `confirmed_shocks.csv` | derived from `geo_signals.csv` (rows with `confirmed`), 19 rows | shock bars in section 7 |

Fixes to existing exports:

- `slide_b_composition.csv`: add a `currency` column (row order is COP, BRL, MXN, ZAR, CLP, KRW).
- `slide_coverage_heatmap.csv`: add a `zone` column (row order US, EA, JP, UK, CH, AU, NZ, CA,
  NO, SE, CN, KR, MX, BR, TW, GLOBAL), or build the heatmap from `coverage_cells.csv`.
- `strategy_b_exposure.csv` and `slide_*_cumulative.csv`: the first column is unnamed; call it
  `date`.

---

## 7. Existing files used, by section

| Section | Files |
|---|---|
| 2 Data | `classification_summary.csv`, `classification_examples.csv` |
| 3 Coverage | `coverage_cells.csv`, `coverage_quarterly.csv` (optional quarterly view) |
| 4 Signals | `theme_indices.csv` (filtered), `annotations.json` |
| 5 Timing | `strategy_a_tstats.csv`, `slide_leadlag.csv`, `strategy_a_weekend_gap.csv`, `weekend_changes.csv` |
| 6 Strategy A | `strategy_a_returns.csv`, `strategy_a_performance.csv`, `robustness_a.csv`, `d30_phase.csv`, `d30_effective_sample.csv`, `d30_monthly_2026.csv`, `d30_decomposition.csv` |
| 7 Strategy B | `strategy_b_returns.csv`, `strategy_b_performance.csv`, `strategy_b_exposure.csv`, `geo_signals.csv`, `drawdowns.csv`, `slide_b_composition.csv` |
| 8 Risk | `risk_episodes.csv`, `risk_betas.csv`, `risk_downside_beta.csv`, `risk_worst_drawdowns.csv`, `risk_concentration.csv`, `risk_conditional.csv`, `risk_leverage.csv`, `a_vs_b_correlation.csv` |
| 9 Robustness | `robustness_a.csv`, `robustness_b.csv`, `robustness_posthoc.csv`, `robustness_grid_b.csv`, `cost_sensitivity_b.csv`, `subperiods.csv` |

`results/site_data/README.md` documents every column.

---

## 8. Headline numbers and their sources (checked on 2026-10-10)

These are the numbers of the talk; the build must reproduce each from the file named.

| Claim | Value | Source (file, row, column) |
|---|---|---|
| Markets with trades, volume | 80,203; USD 11.16 bn | RESULTS.md section 1 (export as `pm_summary.csv`) |
| Coverage US monetary / global geopolitics / US fiscal | 93.9% / 76.7% / 68.5% | `coverage_cells.csv`, `share_train` |
| UK fiscal coverage in 2026 | 55.0% | `coverage_cells.csv`, `share_test` |
| Same-day t, monetary / fiscal | 4.02 / 0.33 | `strategy_a_tstats.csv`, model `A1_contemporaneous`, horizon 0 |
| Predictive t at 1, 5, 20 days | 0.75, 1.02, -0.46 (mon.); 0.93, 1.92, 3.35 (fisc.) | same file, model `A1_predictive` |
| Weekend gap | 1,278 pair-weekends, max abs t 1.3 | `strategy_a_weekend_gap.csv` |
| A1 net / gross Sharpe | 0.43 / 0.88 | `strategy_a_performance.csv`, `A1_theory_with_dollar`, `full` |
| A1 net t, 90% CI | 0.72; -0.70 to 1.22 | same row, `sharpe_t`, `sharpe_ci90_*` |
| A2 net / gross | 0.81 / 1.43; gross CI 0.37 to 2.25 | `A2_theory_with_dollar` rows |
| A2 dollar-neutral net | -0.95 | `A2_theory_dollar_neutral`, `full` |
| A1 + geopolitics net | -0.21 | `A1+S_theory_with_dollar`, `full` |
| A1 turnover, cost drag | 132.6 a year, 4.69% | same row, `turnover_ann`, `cost_drag_ann` |
| 2026 out-of-sample: A1 net / gross, A2 net | 0.28 / 0.85, 1.08 | `out-of-sample` rows |
| A1 weekly net, turnover | 0.75, 62.8 | `A1_theory_with_dollar_weekly` |
| D30 full / 2026 | 1.51 / 2.46 | `A1_gated20_frozen` |
| D30 phase mean 2026, positive phases | 0.22, 12 of 20 | `d30_phase.csv`, mean of `sharpe_2026` |
| Base carry net Sharpe, t, CI | 1.25, 2.10, 0.33 to 2.31 | `strategy_b_performance.csv`, `base_carry`, `full` |
| Base carry 2026, cost drag | 2.03, 0.36% | `out-of-sample` row; `cost_drag_ann` |
| PM-timed Sharpe, max drawdown | 1.30, -8.0% | `pm_timed`, `full` |
| Base carry max drawdown | -14.0% | `base_carry`, `max_drawdown` |
| Without the Taiwan contract | 1.00, -13.1% | `key_month_check.csv`, `pm_timed_without_event` |
| June 2024 alone / other months / total | +6.3 / -10.4 / -4.1 points | `key_month_check.csv`, `best_month_gain`, `total_gain` |
| VIX-timed, B2, 3-events filter | 1.12, 1.37, 0.89 | `strategy_b_performance.csv` |
| Long-history carry | Sharpe 0.33, drawdown -43.7%, kurtosis 2.70 | `base_carry_long_history.csv` |
| Confirmed shocks | 19; contracts 1 to 39 | `geo_signals.csv`, `confirmed`, `n_contracts` |
| Average exposure, days reduced | 0.81, 211 of 714 | `strategy_b_exposure.csv`, `w` |
| Episodes: carry in the Iran war, PM-timed | +8.0%, +5.9% | `risk_episodes.csv` |
| Episodes: yen unwind, Liberation Day (carry) | -1.3%, -2.8% | same file |
| Brent beta t (carry) | 4.5 | `risk_betas.csv`, `base_carry`, `brent` |
| A2 MSCI beta, t | -0.24, -2.0 | `risk_betas.csv`, `A2_theory_with_dollar` |
| Downside beta A2 | -0.81 | `risk_downside_beta.csv` |
| A vs B correlation, daily / weekly | -0.04 / -0.17 | `a_vs_b_correlation.csv`, A1 with dollar vs pm_timed |
| Placebos beaten: A1, A2, B | 92%, 99%, 93% | `robustness_a.csv`, `robustness_b.csv` |
| B cost sensitivity 0.5x to 3x | 1.38, 1.30, 1.15, 1.00 | `cost_sensitivity_b.csv` |
| Composition and Brent betas | COP +40, BRL +33, MXN +31, ZAR 0, CLP -44, KRW -61 | `slide_b_composition.csv` |

---

## 9. Two ways to use this brief

**Path 1, recommended: build in Claude Code inside the repository.** The session reads the
CSVs, adds the exports of section 6 to `site_data.py`, writes `build_site.py`, the template and
the JS, hooks the build into `run_all.py`, logs it, and commits `site/index.html`. The numbers
flow from the data with no retyping. Estimated size of the work: the exporter changes (small),
the template and CSS (medium), the JS rendering of about 18 figures (the bulk), a test that
compares DATA with `RESULTS.md` (small).

**Path 2: Claude web designs the template, Claude Code fills the data.** Send Claude web this
brief with the instruction: "Build the page against the `window.DATA` contract of section 10,
with mock data of the right shape; no number may be typed into the HTML, every value is read
from DATA". Claude web returns `template.html`, `site.css`, `site.js`. Claude Code then writes the
exporter and `build_site.py` that produce the real DATA and assemble the file. This split works
only if both sides respect the contract below exactly.

In both paths the page is a generated artefact of the repository, rebuilt by one command.

---

## 10. `window.DATA` contract

Dates are ISO strings. Series are arrays aligned on a shared `dates` array when they have the
same index. Missing values are `null`. Keys that the JS reads:

```
DATA = {
  meta: { built: "2026-10-10", sample_start, sample_end, oos_start: "2026-01-01",
          n_days: 714, n_decisions: 31 },
  pm_summary: [ {platform, markets, market_days, volume_usd_bn} ],
  classification: { summary: [ {platform, theme, markets, events, usable} ],
                    examples: [ {platform, title, theme, zones, direction, theme_rule, direction_rule} ] },
  coverage: { zones: [...], themes: [...],
              cells: [ {zone, theme, share_train, share_test, n_contracts, n_events, volume_usd_m, keep} ],
              cells_10k: [ same shape ] },
  signals: { dates: [...],
             cells: { "US/MONETARY": {index_vw: [...], index_ew: [...], n_contracts: [...]}, ... } },
  annotations: [ {date, label, cells: [...]} ],
  timing: { tstats: [ {regressor, horizon, model, coef, se, t, p, n_obs} ],
            leadlag: { studies: [...], rows: [ {study, hour, mean, ci_low, ci_high, n_events} ] },
            weekend: { n_pair_weekends: 1278, max_abs_t: 1.3, rows: [ {regressor, coef, se, t, p, n_obs} ] } },
  strategy_a: { dates: [...],
                variants: [ {id, label, status, primary: bool} ],
                cum_net: { id: [...] }, cum_gross: { id: [...] }, drawdown: { id: [...] },
                performance: [ {strategy, period, sharpe, sharpe_t, sharpe_ci90_low, sharpe_ci90_high,
                                ann_mean, ann_vol, max_drawdown, turnover_ann, cost_drag_ann, hit_rate} ],
                fiscal_regime_days: [ {zone, year, days} ],
                robustness: { placebo_bins: { variant: {edges: [...], counts: [...], actual, share_beaten} },
                              leave_one_out: [ {variant, event, sharpe} ],
                              halflife: [ {variant, halflife, sharpe} ],
                              static_timing: [ {part, period, sharpe, ann_mean} ],
                              momentum: [ {benchmark, sharpe, beta, alpha, t} ] },
                d30: { phase: [ {offset, sharpe_2024_2025, sharpe_2026, sharpe_full} ],
                       mean_2026, n_positive_2026, effective_t, monthly_2026: [...] } },
  strategy_b: { dates: [...],
                lines: [ {id, label, status} ],
                cum_net: { id: [...] }, cum_gross: { id: [...] }, drawdown: { id: [...] },
                performance: [ same shape as strategy_a.performance ],
                exposure: { w: [...], w_escalation: [...], shock: [...], w_vix: [...], shock_vix: [...] },
                geo: { index: [...], escalation_z: [...], n_contracts: [...],
                       confirmed_shocks: [ {date, n_contracts} ] },
                key_month: { month: "2024-06", gain: 0.0633, total: -0.0408, others: -0.1041,
                             event: "will-china-invade-taiwan-in-2024", without: {sharpe, max_drawdown} },
                long_history: { n_days, years, sharpe, max_drawdown, excess_kurtosis,
                                cum: {dates: [...], values: [...]} },
                composition: [ {currency, average_weight, share_of_gross, brent_beta_weekly} ],
                exposure_summary: { mean_w, days_reduced, n_days } },
  risk: { episodes: [ {episode, start, end, strategy, cum_return, worst_day} ],
          betas: [ {strategy, factor, beta, t, corr, n} ],
          downside: [ {strategy, market, beta, downside_beta, n_down, mean_return_down_days_bp} ],
          worst_drawdowns: [ {strategy, peak, trough, recovery, depth, duration_days, tag} ],
          concentration: [ {strategy, dimension, key, share_of_abs, hhi} ],
          conditional: [ {strategy, conditioner, bucket, sharpe, ann_mean, n_days} ],
          leverage: [ {strategy, period, gross_mean, gross_p95, gross_max, share_days_gross_cap,
                       share_days_pair_cap, realised_vol, target_vol} ],
          a_vs_b: { return_corr, weekly_return_corr, drawdown_corr } },
  robustness: { placebo_b_bins: {edges, counts, actual, share_beaten, random_contracts, reversed},
                posthoc: [ {strategy, share_beaten, actual} ],
                grid_b: [ {shock_k, rerisk_days, shock_cut, sharpe, max_drawdown, ann_mean} ],
                grid_b_chosen: {shock_k: 2.0, rerisk_days: 10, shock_cut: 0.25},
                cost_b: [ {cost_multiplier, sharpe, max_drawdown} ],
                cost_a: [ {variant, multiplier, sharpe} ],
                subperiods: [ {strategy, period, sharpe, ann_mean, max_drawdown} ] }
}
```

Strategy identifiers keep the names of the CSV columns (`A1_theory_with_dollar`, `pm_timed`,
...); the `label` field carries the display name ("A1, primary", "with PM geopolitical overlay").

---

## 11. Build and QA checklist

1. `python run_all.py --stage figures` (or `--stage site`) rebuilds `site/index.html`.
2. The file opens from disk with the network off; every chart renders; no console error.
3. Phone width (375 px): no horizontal scroll, charts and tables readable, controls reachable.
4. `grep` for the em dash character returns nothing.
5. Every value of section 8 appears on the page with the same rounding as `RESULTS.md`.
6. Each a posteriori and exploratory item carries its badge.
7. The page states the sample, the in-sample and out-of-sample split and the snapshot time.
8. File size under 5 MB.
9. `DECISIONS.md`, `ai_log/code_generation.md` and `README.md` updated; `site/index.html`
   committed when the user asks.

---

## Amendments from the team (2026-10-10), applied

1. Order of work: data exports, `build_site.py`, DATA assembly and the consistency test against
   `results/RESULTS.md` first; no chart code before that test passes. Then the hero, the coverage
   heatmap with the gate slider, the horizon table, the cumulative charts of A and B with gross / net
   and period selectors, the "Not a result" panel, the stress-episodes table and section 10; then
   the remaining figures; dark mode and episode highlighting last, only if time remains.
2. The em-dash assertion runs on `template.html`, `site.css`, `site.js` and the DATA JSON, not on
   the final `index.html` (the vendored Plotly bundle is outside our control).
3. No hand-validation note in section 2 and no placeholder anywhere; the missing hand validation
   is mentioned once, in section 10, as a limitation.
4. Numbers in prose are formatted in Python at build time; charts read `window.DATA`; prose is
   static text, so the page is searchable and the consistency test can grep the HTML.
5. The A1 half-life sensitivity is an interactive strip (clickable values updating Sharpe cards).
6. In the horizon table, the 20-day fiscal cell carries the exploratory badge inside the cell and
   links to the "Not a result" panel.
7. The hero's Carry card says in one sentence that the overlay's gain comes from one contract in
   one month, next to the carry and overlay Sharpe ratios.
8. Mobile: Plotly `responsive: true, displayModeBar: false`, a resize handler on orientation
   change, every HTML table in a container with `overflow-x: auto`, tested at 375 px.
9. Path 1 only: everything built inside the repository, `site/index.html` committed, build hooked
   into `run_all.py`, no mock data at any stage.
10. Logging: `DECISIONS.md` entry, `ai_log/code_generation.md` row, README line.
