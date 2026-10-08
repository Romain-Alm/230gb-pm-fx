# Brief for Claude Code: opening slides 1 to 6 (Piero), MFE 230GB presentation

Presentation: Thursday October 8, 2026, 3:00 PM, in class. These six slides open the talk.
Speaker: Piero, 5 minutes total. Then Romain (Strategy A), Thomas (Strategy B), Hino (risk,
inference, synthesis). Their slides are NOT part of this task.

Job of these six slides: give the professor the base that everything after builds on.
1. why this data (new, direct),
2. what the course economics predicts (the sign of every trade, fixed before any backtest),
3. how contracts become daily indices,
4. where the information actually is (coverage gate),
5. what the data can and cannot do (it moves with FX, not before),
6. how the two strategies use it (design only, no results).

---

## 0. Deliverables and housekeeping

- `presentation/build_piero_slides.py`: one short script. Reads the CSV files listed in
  section 2, computes the few derived numbers, asserts them against the expected values in
  section 2, and writes the deck with all data inlined as JSON.
- `presentation/index.html`: the deck (slides 1 to 6 now; the other members' slides will be
  appended later in the same file, so keep slides as independent `<section>` blocks).
- Delete the empty file `.write_test` at the repo root (left behind by a write check).
- Do not modify anything in `src/`, `results/`, `config/`, `DECISIONS.md`. Do not rerun the
  pipeline. Read-only use of `results/`.

### Look and feel
- Copy the visual system of Piero's 230GA and 230ZB decks: fonts, palette, title bar,
  footer, slide frame, navigation, chart styling. Look for them on this machine (search
  under `~/Desktop/uni/Berkeley/` for the 230GA and 230ZB project folders and their HTML
  slides). If you cannot find them, stop and ask Piero for the path.
- Use the same charting library as those decks. If they use none, use Plotly.js from cdnjs,
  pinned to an exact version (e.g. 2.35.2).
- 16:9 slides, keyboard navigation (left/right arrows, space), slide counter, press `N` to
  toggle a speaker-notes overlay (notes are given per slide below), works on a projector at
  1920x1080 and on a laptop.
- Charts: bold titles, minimal formatting, default fonts of the deck, light gridlines, no dual
  axes, hover tooltips with exact values. Text never in the series color (use a colored mark
  next to it).
- Fixed colors used on every slide for the three data cells:
  US MONETARY = blue, US FISCAL-POLITICAL = orange, GLOBAL GEOPOLITICS = green (use the deck
  palette's first three categorical colors if it has them; else #2a78d6 / #eb6834 / #1baf7a).
  Strategy A inherits the two US colors, Strategy B the green.
- Project style rule: no em dashes in any slide text. Use commas, colons or periods.
- Every headline is a full sentence that states the slide's message.

### Hosting
The team repo `Romain-Alm/230gb-pm-fx` looks private, so GitHub Pages or raw/preview links
may not open for the professor. Check how the 230GA and 230ZB decks are served (same link
pattern) and do the same. If they live on Piero's public GitHub (`pieropls`), also publish
`index.html` there and print the direct link. Ask Piero before pushing to a repo you are
unsure about.

---

## 1. Global numbers rule

Every number on the slides is read from the files in section 2 at build time, never typed
by hand, except the few marked HARDCODED (with their source). The build script asserts the
expected values below (tolerance: last displayed digit) and fails loudly on mismatch.

---

## 2. Data sources (all paths relative to the repo root)

| Key | File | What to use |
|---|---|---|
| CELLS_DAILY | `results/site_data/theme_indices.csv` | columns `day, zone, theme, n_contracts, vol7d, d_vw` |
| CLASS_SUMMARY | `results/site_data/classification_summary.csv` | `platform, theme, markets, events, usable` |
| CLASS_EXAMPLES | `results/site_data/classification_examples.csv` | real contract titles with `theme, zones, direction, partition, unit` |
| COV_CELLS_50K | `results/coverage_cells.csv` | `zone, theme, share_train, share_test, n_contracts, volume_usd_m, keep` |
| COV_CELLS_10K | `results/coverage_cells_v10k.csv` | same columns, USD 10k threshold |
| COV_QUARTERLY | `results/site_data/coverage_quarterly.csv` | `zone, theme, quarter, share_days_covered` (USD 50k) |
| DIAG | `results/strategy_a/diagnostics.csv` | `regressor, t, horizon, model` |
| LEADLAG | `results/leadlag/event_study.csv` | `study, hour, mean, ci_low, ci_high, n_events` |
| WEEKEND | `results/weekend/weekend_gap_regressions.csv` | `regressor, t, model, n_obs` |
| AB_CORR | `results/risk/a_vs_b_correlation.csv` | row `a = A1_theory_with_dollar`, column `return_corr` |

### Derived quantities and expected values

**S1. Active liquid contracts per day in the three kept cells.** From CELLS_DAILY keep
(US, MONETARY), (US, FISCAL_POLITICAL), (GLOBAL, GEOPOLITICS); per day sum `n_contracts`
by cell; quarterly mean of daily values (calendar days). Expected totals:
2024Q1 2.7, Q2 3.7, Q3 18.1, Q4 31.5; 2025Q1 9.1, Q2 16.6, Q3 14.0, Q4 19.3;
2026Q1 41.8, Q2 45.2, Q3 38.0 (Q3 2026 ends Sep 24). No double counting: each contract has
one theme, and the three cells have different themes.

**S3. Funnel.** From CLASS_SUMMARY: all markets = 80,203 (Kalshi 50,281, Polymarket 29,922);
macro (theme != OTHER) = 29,704; usable (column `usable`, theme != OTHER) = 11,276.
HARDCODED: contracts in the daily panel = 9,103 (source `results/RESULTS.md`, section 1;
bracket markets are collapsed into one expected-value contract, hence fewer than 11,276).
Cells passing the gate = count of `keep == True` in COV_CELLS_50K = 3.
HARDCODED: $11.2bn traded (2.28 Kalshi + 8.88 Polymarket, `results/RESULTS.md` section 1).
HARDCODED drift check (D18, `results/RESULTS.md` section 3): US MONETARY drift without hazard
transform 0.079 sd/day (t = 2.9), with it 0.06 (t = 2.1).

**S4. Gate.** Pass rule: `share_train >= gate`. Expected at USD 50k and gate 0.60: exactly
US MONETARY 0.939, GLOBAL GEOPOLITICS 0.767, US FISCAL_POLITICAL 0.685. Next cell below:
US GEOPOLITICS 0.526. So any gate in (0.526, 0.685] selects the same three cells.
At USD 10k and 0.60: five cells (adds CN GEOPOLITICS 0.746, US GEOPOLITICS 0.642).
Best non-US G10 cell at USD 10k: UK FISCAL_POLITICAL 0.314 (EA FISCAL_POLITICAL 0.310).
UK FISCAL_POLITICAL `share_test` (2026) = 0.55.

**S5a. Daily horizons (DIAG).** model `A1_contemporaneous` (horizon 0) and `A1_predictive`
(horizons 1, 5, 20), regressors MONETARY and FISCAL_POLITICAL. Expected t:
MONETARY 4.02 / 0.75 / 1.02 / -0.46; FISCAL 0.33 / 0.93 / 1.92 / 3.35.

**S5b. Hourly (LEADLAG).** For each row: `t = mean / ((ci_high - ci_low) / (2 * 1.96))`.
Default view, US MONETARY. Expected:
- `FX top 1% -> PM US/MONETARY` (prediction-market response to big dollar moves):
  h-3 1.48, h-2 -1.38, h-1 1.30, h0 5.80, h+1 2.64, h+2 1.63, h+3 -0.06.
- `PM US/MONETARY top 1% -> FX dollar basket` (dollar response to big PM moves):
  h-3 0.96, h-2 0.46, h-1 1.49, h0 2.50, h+1 0.61, h+2 -0.21.
Show hours -6 to +6.

**S5c. Weekend (WEEKEND).** Main: model `A1+GEO_weekend_gap_london`, regressors MONETARY,
FISCAL_POLITICAL, SPILL_GLOBAL_GEOPOLITICS: t = 0.00, 0.59, -0.62 (n_obs 1,278).
Robustness: `A1+GEO_weekend_gap_ny`: t = 1.27, -0.64, 0.74 (n_obs 1,272).

**S5 example day.** HARDCODED (computed from `results/site_data/theme_indices.csv` and the
A1 P&L/weights files): on 2024-08-02 (weak US jobs report) US MONETARY `d_vw` = -5.0, its
largest dovish move of the sample; the dollar fell about 0.8% against the G10 basket the
same day (EUR +1.1%, JPY +1.9%, CHF +1.6%). Verify the -5.0 from CELLS_DAILY.

**S6.** AB_CORR `return_corr` for A1 vs PM-timed B = -0.04.

---

## 3. The slides

Timing target: 45 + 55 + 65 + 50 + 60 + 25 seconds = 5:00.

---

### Slide 1. Title and motivation (45 s)

**Eyebrow:** MFE 230GB · Currency Markets · Final project
**Title:** Prediction Markets and Currency Strategies
**Subtitle (the question):** Do event odds tell us anything about currencies that currency
prices do not already know?
**Team line:** Romain Almeida · Piero Pelosi · Hino Wirachapong · Thomas Claudel · Berkeley
Haas · October 8, 2026

**Layout:** left 55% text, right 45% chart.

Left, three short blocks with a one-word label each:
- **New.** Liquid macro contracts barely existed before mid-2024. Kalshi and Polymarket:
  80,203 markets, $11.2bn traded in our sample.
- **Direct.** One contract, one event: "Will the Fed cut in December?" A currency price
  blends every piece of news at once.
- **Testable.** Each event maps onto a course mechanism with a known sign, so the rules can
  be fixed before any backtest.

Below, a two-branch "fork" graphic (small, clean):
`Do event odds move...` → branch 1 **before FX** → "a predictor: trade it" ;
branch 2 **with FX** → "an explainer: use it to read and manage risk".
Caption under the fork: "Our tests tell which."

Right, chart: **"Liquid contracts behind our three indices, average per day"**. Stacked
quarterly bars, 2024Q1 to 2026Q3, stacked by cell (US monetary, US fiscal-political, global
geopolitics; fixed colors). Data S1. Annotate 2024Q4 "US election". Label the first and
last full bars with their totals (2.7 and 45.2). Hover: quarter, value per cell, total.
Footnote: "Contracts with at least $50k of weekly volume and a trade within 6 hours of the
16:00 London snapshot. 2026Q3 ends Sep 24."

**Interaction:** hover on the chart; clicking a fork branch highlights it (cosmetic only).

**Speaker notes (Piero):**
The assignment asked for alternative data and named prediction markets as the example. We
took that literally, because this data is genuinely new. In early 2024, on an average day,
the three indices we ended up using rested on fewer than three liquid contracts. Today
they rest on about forty. And each contract isolates one event, like "Will the Fed cut in
December?", while a currency price blends everything at once. So our question was simple.
Do event odds move before currencies, in which case we trade them? Or at the same time, in
which case they explain moves but cannot predict them? The rest of the talk answers that.

---

### Slide 2. What we took from the course (55 s)

**Eyebrow:** Economic framework
**Headline:** Without economics, a signal is a bet. The course gives every trade its sign
before we look at any return.

**Layout:** three equal columns (cards), each with: mechanism name, a small diagram, "What
it predicts", "Sign we trade", "Used in" tag (Strategy A or B, in the strategy color).

Card 1, **Carry and the failure of UIP**
- Formula line: `rx ≈ (i* − i) − Δs` (carry minus depreciation).
- Predicts: UIP says high-yield currencies fall by the rate gap, so carry earns zero. They
  fall less: carry earns a premium that pays for crash risk in global risk-off (downside
  beta, Lettau, Maggiori and Weber).
- Sign: long high-carry currencies, short low-carry; cut exposure when crash risk rises.
- Used in: **Strategy B**.

Card 2, **Monetary vs fiscal dominance** (interactive)
- Small arrow chain with a two-position toggle `Monetary dominance | Fiscal dominance`:
  - Monetary: `Bigger deficit → Fed expected higher → rates ↑ → USD ↑` (last box green).
  - Fiscal: `Bigger deficit → debt worries, risk premium → yields ↑ → USD ↓` (last box red).
  Toggling animates only the last two boxes. Under it: "Signature of fiscal dominance:
  yields and the currency move in opposite directions (UK 2022, US Apr to May 2025)."
- Predicts: hawkish Fed news lifts the dollar; fiscal news lifts it or sinks it depending on
  the regime.
- Sign: monetary +1; fiscal +1, or -1 when the 60-day yield/dollar correlation turns
  negative.
- Used in: **Strategy A**.

Card 3, **Terms of trade**
- Small diagram: `Oil ↑ → exporters ↑ (BRL, MXN, COP, NOK, CAD) / importers ↓ (KRW, INR)`.
- Predicts: an oil shock moves exporters' and importers' currencies in opposite directions.
- Sign: which currencies win a Middle East shock.
- Used in: **Strategy B** (with a note: "and it explains B's result").

Footer strip (small): "Also from the course: covered interest parity (carry read from
forwards and NDFs) and de facto exchange-rate regimes (Ilzetzki, Reinhart, Rogoff) to pick
which emerging currencies are tradable."

**Interaction:** the toggle on card 2; hovering a card's "Used in" tag highlights it.

**Speaker notes (Piero):**
Without economics, a signal is just a bet. So before touching the data we fixed, from the
course, the sign of every trade. Three mechanisms. One, carry and the failure of uncovered
interest parity: high-yield currencies do not fall enough, so carry earns a premium, which
pays for crash risk in global sell-offs. That is the base of Strategy B. Two, monetary
versus fiscal dominance. Hawkish Fed news lifts the dollar. A bigger deficit lifts it too
in normal times, but sinks it when markets doubt the debt, like the UK in 2022 or the US
in spring 2025. [click the toggle] Same news, opposite sign. That is Strategy A. Three, terms of
trade: oil up lifts exporters' currencies and hurts importers'. Keep this one in mind; it
explains Strategy B's result.

---

### Slide 3. From 80,000 bets to a daily index (65 s)

**Eyebrow:** Alternative data: prediction markets
**Headline:** Every contract becomes one number per day; contracts on the same theme and
country are averaged into an index.

**Layout:** top band = funnel; middle band = five-step pipeline (clickable); bottom-right =
detail panel that changes with the selected step (default: step 3, hazard).

Top, funnel (horizontal bars shrinking left to right, labels inside or right):
`80,203 markets` → `29,704 macro` → `11,276 we can sign (direction or bracket)` → `9,103
contracts in the daily panel` → `3 indices pass the gate`. Hover on the first bar shows the platform
split (Kalshi 50,281 · Polymarket 29,922). Data S3.

Middle, pipeline: five boxes with arrows. Each box has a title and a one-line rule:
1. **Classify** · theme, country, direction, by fixed rules (no AI model: reproducible,
   free, no API).
2. **Snapshot** · last trade before 16:00 London; stale if no trade for 6 hours; kept only
   3 to 365 days before resolution and priced 3% to 97%.
3. **Value** · probability; brackets → expected value in bp or pp; "by-date" contracts →
   hazard rate.
4. **Standardise** · daily change ÷ the contract's usual daily move, × direction sign,
   capped at ±5.
5. **Index** · volume-weighted average per country × theme; running sum = index level.

Detail panel (click a box to switch; arrows also step through):
- Step 1: three real examples from CLASS_EXAMPLES, shown as "title → zone · theme ·
  direction":
  "Will the upper bound of the federal funds rate be above 3.50% following the Fed's Apr 28,
  2027 meeting?" → US · MONETARY · +1 (hawkish);
  "Russia x Ukraine ceasefire by January 31, 2026?" → GLOBAL · GEOPOLITICS · -1
  (de-escalation);
  "Will the Republican Party win the NJ-08 House seat?" → US · FISCAL-POLITICAL · no
  direction → excluded.
- Step 2: a mini timeline of one day: trades before 16:00 London count for day t, trades
  after count for t+1; "no look-ahead: the signal is known 6 hours before we trade at the
  New York close".
- Step 3 (default), **the hazard-rate fix**, interactive:
  Title: "A 'by Dec 31' contract decays even when nothing changes."
  Slider: "risk per month" from 2% to 20% (default 10%).
  Two small side-by-side charts (NOT one chart with two axes), x-axis "months left" from 12
  down to 0:
  left "Price (probability)": p = 1 − exp(−h·τ), falls toward 0 as the deadline nears;
  right "Implied hazard −ln(1−p)/τ": a flat line at h.
  Text under it: "Read naively, the falling price looks like a stream of good news that
  never happened. The hazard stays flat. Without this fix, our US monetary index drifts by
  0.079 sd a day (t = 2.9); with it, 0.06 (t = 2.1)."
  Worked numbers shown at default: 6 months left → p = 45%; 1 month left → p = 9.5%;
  hazard both times = 10%/month. (Compute live from the slider; with h = 0.10 per month:
  1 − e^(−0.6) = 45.1%, 1 − e^(−0.1) = 9.5%.)
- Step 4: formula `z = (Δvalue / √gap) / σ_EWMA × sign`, capped at ±5; one sentence: "a
  2-point move in a calm contract counts more than in a jumpy one".
- Step 5: formula `index change = Σ volume × z / Σ volume`; "cumulated like a rolled
  futures series".

**Interaction:** clickable pipeline steps, hazard slider, funnel hover.

**Speaker notes (Piero):**
Then the data. We start from about 80,000 Kalshi and Polymarket markets, 11 billion dollars
traded. About 30,000 are macro; 11,000 have an economic direction we can sign. Each goes
through five steps. [click Classify] Fixed rules, no AI model, tag the theme, the country and
the direction: a higher probability of a Fed cut is dovish, so it gets a minus sign. We read
the last price before 16:00 London every day. [click Value] One trap: "by-date" contracts. A
"ceasefire by January 31" contract loses value every day nothing happens, even if the risk
has not changed. [move the slider] So we convert the price into the implied risk per month,
the hazard rate, which stays flat. Finally, each daily change is divided by the contract's
usual move, signed, capped, and averaged by volume into one index per theme and country.

---

### Slide 4. The coverage gate: where the information is (50 s)

**Eyebrow:** Coverage gate
**Headline:** Prediction markets talk about the US and the world, not about Germany or
Japan.

**Layout:** left 62% heatmap, right 38% controls and three short text blocks.

Left, heatmap: rows = the 14 cells with the highest `share_train` in COV_CELLS_50K (sorted
descending; readable labels like "US · Monetary", "Global · Geopolitics", "UK ·
Fiscal-political", "Japan · Monetary"); columns = quarters 2024Q1 to 2026Q3 (from
COV_QUARTERLY); color = share of weekdays with at least one eligible contract (0 to 100%,
one sequential hue). Missing quarter = 0. Right of each row, a pass/fail marker computed
from the current gate setting on `share_train` (2024 to 2025). A thin vertical divider
between 2025Q4 and 2026Q1 labelled "training | out of sample".
Hover: cell, quarter, share, eligible contracts that quarter.

Right, controls:
- Slider "Gate: share of weekdays covered in 2024 to 2025", 30% to 90%, default 60%.
- Toggle "Weekly volume floor: $50k | $10k" (switches pass/fail to COV_CELLS_10K; the
  heatmap colors stay at $50k, say so in a small note).
- Live counter: "Cells that pass: 3".
- A small static line under the slider: "Same three cells for any gate between 53% and 68%."

Right, text blocks:
- **Why a gate?** A daily signal has to exist on most days. A cell alive one day in three
  is mostly zeros: its volatility and z-scores rest on a handful of contracts.
- **Why 60% and $50k?** Fixed in the spec before any data: a signal on three trading days
  out of five, and enough money behind each price. The result does not hinge on it: even at
  $10k, the best non-US developed-market cell (UK fiscal) covers 31% of days.
- **So:** Strategy A trades the dollar; global geopolitics feeds Strategy B. Coverage is
  rising fast (UK fiscal: 55% of days in 2026).

**Interaction:** gate slider, volume toggle, heatmap hover.

**Speaker notes (Piero):**
An index is only useful if it exists most days. So the spec fixed a gate before any
backtest: at least one contract with 50,000 dollars of weekly volume, on 60% of weekdays in
2024 and 2025. This heatmap is the most important table of the project. Only three cells
pass: US monetary policy, US fiscal politics, and global geopolitics. Nothing on Germany,
Japan or the UK. [drag the slider] And it is not a threshold artefact: anywhere between 53
and 68% gives the same three, and even at 10,000 dollars the best non-US developed-market
cell is the UK at 31%. So prediction markets speak about the US and about the world. That
decides our design: Strategy A becomes a dollar strategy, and geopolitics feeds Strategy B.

---

### Slide 5. Does the data move before currencies? (60 s)

**Eyebrow:** What we asked the data
**Headline:** Prediction markets move with currencies, not before them.

**Layout:** three panels side by side, each with a one-line question on top and a one-line
answer under the chart. Bottom: one takeaway bar across the slide.

Panel a, **"Same day or later?"** (daily, DIAG, data S5a)
- Grouped bars: x = horizon (Same day, +1 day, +5 days, +20 days); two bars per group
  (US monetary blue, US fiscal orange); y = t-statistic. Shaded band from -2 to +2 labelled
  "noise zone (|t| < 2)". Label the same-day monetary bar "4.0".
- Small annotation on the +20-day fiscal bar (3.35): "horizon picked after looking; fails
  robustness (Romain)".
- Example callout under the chart: "Aug 2, 2024, weak US jobs report: our Fed index has its
  largest dovish move (−5 sd) and the dollar falls 0.8% vs G10, the same day."
- Answer line: "Fed news hits both markets the same day, then nothing."

Panel b, **"Who moves first, hour by hour?"** (LEADLAG, data S5b)
- Two lines, x = hours from −6 to +6 around the event (0 = event hour), y = t-statistic of
  the response, shaded band ±1.96, vertical line at 0:
  "Fed odds after a big dollar move" (study `FX top 1% -> PM US/MONETARY`) and
  "Dollar after a big move in Fed odds" (study `PM US/MONETARY top 1% -> FX dollar basket`).
- Small toggle to switch the cell: US monetary (default) | US fiscal | Global geopolitics
  (uses the matching study names). Note under it: "about 140 to 300 events per study".
- Answer line: "Nothing before hour 0; Fed odds keep adjusting an hour after the dollar."

Panel c, **"Does the weekend move predict Monday?"** (WEEKEND, data S5c)
- Horizontal bars of t-statistics for US monetary, US fiscal, global geopolitics, with the
  ±2 band. Toggle "Reopening measured at: Monday 07:00 London | Sunday 18:00 New York".
- One-line explainer above: "FX closes Friday 17:00 New York; prediction markets keep
  trading."
- Answer line: "1,278 pair-weekends: no weekend move predicts the reopening (all |t| < 1.3)."

Takeaway bar: "Prediction markets explain currency moves in real time; they do not predict
them. The bar for both strategies: A must survive with a slower signal and real costs; B
uses event odds to manage risk, not to forecast returns."

**Interaction:** hover on all three panels; cell toggle in b; reopening toggle in c.

**Speaker notes (Piero):**
Before building strategies, we asked the data the key question: does it move first? Three
tests. Left: currency returns regressed on our Fed index. Same day, a t of 4. Next day,
0.75; five days, 1. Fed news hits both markets the same day and stops there. A concrete case:
our largest Fed move is August 2nd, 2024, the weak jobs report. Cut odds jumped and the
dollar fell about 0.8% that same day. Middle: hour by hour around the biggest dollar moves.
Nothing before hour zero, and prediction markets keep adjusting one hour after. Right: the
weekend, when FX is closed but prediction markets trade. Their weekend moves do not predict
Monday's reopening. So prediction markets explain currency moves in real time; they do not
predict them. That sets the bar for both strategies.

---

### Slide 6. Two strategies, two uses of the same data (25 s)

**Eyebrow:** From data to strategies
**Headline:** The same data gets two different jobs: choose the direction of the dollar, or
choose how much risk to hold.

**Layout:** two cards side by side, a thin row of three "data cell" chips above them (US
monetary, US fiscal, Global geopolitics, in their colors) and a row of three "mechanism"
chips (Carry/UIP, Monetary vs fiscal dominance, Terms of trade). Lines connect each card to
the chips it uses.

Card A (presenter: Romain), **Strategy A · Developed markets**
- Data: US monetary + US fiscal-political indices.
- Mechanism: monetary vs fiscal dominance.
- Job of the prediction markets: pick the direction, long or short the dollar against 9 G10
  currencies, every day.
- Question: can event odds time the dollar once trading costs are paid?

Card B (presenter: Thomas), **Strategy B · Emerging markets**
- Data: global geopolitics index.
- Mechanisms: carry and UIP failure; terms of trade.
- Job of the prediction markets: pick how much carry to hold, from 100% down to 0%, in a
  BRL, MXN, COP, CLP, ZAR, KRW carry portfolio.
- Question: can event odds protect a carry portfolio from crashes?

Footer: "Built on separate contracts on purpose: daily return correlation between A and B =
−0.04." (from AB_CORR, rounded to 2 decimals). No other result numbers on this slide.

**Interaction:** hovering a card highlights its chips and connecting lines; the other card
dims.

**Speaker notes (Piero):**
So the same data gets two different jobs. Romain's Strategy A asks whether Fed and fiscal
odds can time the dollar against the G10 once trading costs are paid. Thomas's Strategy B
asks a risk question: can geopolitical odds protect an emerging-market carry portfolio from
crashes? They use separate contracts, so they are genuinely different strategies. Romain.

---

## 4. Verification before pushing

1. `python presentation/build_piero_slides.py` runs clean; all asserts in section 2 pass.
2. Open `presentation/index.html` in a browser at 1920x1080 and at 1366x768: no overflow,
   no overlapping labels, every chart renders, every control works (pipeline steps, hazard
   slider, gate slider, volume toggle, hourly cell toggle, weekend toggle, MD/FD toggle).
3. Check by eye against section 2: S1 totals 2.7 and 45.2; funnel 80,203 / 29,704 / 11,276 /
   9,103 / 3; gate counter 3 at 60% and $50k, 5 at $10k; daily t 4.02; hourly h0 5.80 and
   2.50; weekend all |t| < 1.3.
4. No em dashes in slide text (grep for the character).
5. Speaker notes open with `N`.
6. Commit only `presentation/` (and the deletion of `.write_test`); print the link that
   opens the deck directly.

## 5. Open points (Piero to confirm; defaults in brackets)

- Slide 5 takes over the timing evidence that was on old slide 8 (Romain). [Yes: it is a
  property of the data, not of Strategy A. Romain keeps the 20-day rule check.]
- Slide 6 shows no strategy results. [Yes: Romain and Thomas deliver them.]
- Hino covers risk, inference and synthesis. [Assumed; only used in the intro line above.]
