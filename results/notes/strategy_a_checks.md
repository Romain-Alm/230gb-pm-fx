# Strategy A checks for the presentation (2026-10-08)

Diagnostics only. Scope is frozen: no rule, variant or parameter was changed. Logged in
`DECISIONS.md` (2026-10-08, diagnostic).

| Item | Source |
|---|---|
| Sections 1 and 2 | Computed by `src/report/strategy_a_explained.py` (tables in `results/notes/strategy_a_explained/`) |
| Section 3 | Computed by `src/report/strategy_a_checks.py` (tables in `results/notes/strategy_a_checks/`) |
| Section 4 | Restates the equations of `results/notes/strategy_a_explained.md` (section A) |

Conventions:
- **A1**: the primary rule with dollar exposure (`A1_theory_with_dollar`).
- **Returns**: daily; "gross" means before trading costs.
- **Periods**: 2024-2025 (training), 2026 (2026-01-01 to 2026-09-24), 2024-2026.
- **USD position**: minus the sum of the nine G10 weights, as a share of NAV; > 0 means long USD.

---

## 1. Dollar momentum

Code: `src/report/strategy_a_explained.py`, section C of `run`.

Definitions:
- **A1 signal**: $u_t = -y_t$, at the 16:00 London snapshot of day t; > 0 means long USD. $y_t$ is
  the A1 forecast, identical for the nine pairs (`src/strategies/strategy_a.py:103-113`,
  `src/strategies/run_a.py:89-98`).
- **G10 dollar basket return**: $b_t = -\frac{1}{9}\sum_i \Delta \ln S_{i,t}$, the dollar against the
  equal-weighted G10 basket, from the New York close of t-1 to the New York close of t. Spot rates
  are Bloomberg New York closes (`src/data/market.py:92-130`).

### 1a. Same-day correlation

The overlap between the two windows is partial: the snapshot is at 16:00 London (11:00 New York),
and the FX return runs on to the New York close.

`results/notes/strategy_a_explained/c1_correlations.csv`:

| Period | n | corr($u_t$, $b_t$), same day | corr(sign $u_t$, $b_t$) | corr($u_t$, $b_{t-1}$) | corr($u_t$, $\sum_{k=0}^{4} b_{t-k}$) | corr($u_t$, $b_{t+1}$), what A1 trades |
|---|---|---|---|---|---|---|
| 2024-2025 | 523 | 0.096 | 0.065 | 0.116 | 0.210 | 0.039 |
| 2026 | 191 | 0.162 | 0.131 | 0.174 | 0.204 | 0.056 |
| 2024-2026 | 714 | 0.105 | 0.082 | 0.123 | 0.203 | 0.041 |

### 1b. Momentum benchmarks

Construction:
- **Forecast**: common to the nine pairs, $f_t = \mathrm{sign}\big(\sum_{k=0}^{K-1} \overline{rx}_{t-k}\big)$
  with K = 1 or 5, where $\overline{rx}$ is the mean G10 excess return against USD. The position
  is long USD if the dollar rose over the past K days.
- **Portfolio**: built exactly as A1, through `A.positions` (`strategy_a.py:178-185`): $f/\sigma^2$,
  10% volatility target with an EWMA covariance, 30% per-pair and 3x gross caps, 10% no-trade
  band. Execution is at the New York close of t, return on t+1 (`src/backtest/engine.py:114-134`).
- **Timing advantage**: the benchmark uses the FX return up to the New York close of t, which is
  later than A1's 16:00 London information. This favours the benchmark.

`results/notes/strategy_a_explained/c2_benchmarks.csv`:

| Series | Gross Sharpe 2024-2025 | 2026 | 2024-2026 | Gross mean a year, 2024-2026 | Net Sharpe 2024-2026 |
|---|---|---|---|---|---|
| TSMOM 1-day | -1.12 | -0.87 | -1.05 | -11.0% | -2.46 |
| TSMOM 5-day | -0.80 | +0.16 | -0.54 | -5.5% | -1.13 |
| A1 | 0.89 | 0.85 | 0.88 | +9.2% | 0.43 |
| A1 weekly | 1.08 | 0.69 | 0.97 | +10.0% | 0.75 |

### 1c. Regression of A1 gross returns on each benchmark

Specification: $r^{A1}_t = \alpha + \beta\, r^{\text{TSMOM}}_t + \varepsilon_t$, daily gross returns.
- Standard errors: Newey-West HAC with lag $\lfloor 4(T/100)^{2/9}\rfloor$, which is 4 to 6.
- $\alpha$ is annualised (x 252).

`results/notes/strategy_a_explained/c3_regressions.csv`:

| Benchmark | Period | beta | t(beta) | alpha a year | t(alpha) | corr | days with same USD sign |
|---|---|---|---|---|---|---|---|
| TSMOM 1d | 2024-2025 | 0.20 | 2.00 | 11.5% | 1.93 | 0.20 | 55% |
| TSMOM 1d | 2026 | -0.19 | -1.45 | 7.3% | 0.56 | -0.19 | 52% |
| TSMOM 1d | 2024-2026 | 0.09 | 1.00 | 10.1% | 1.78 | 0.09 | 55% |
| TSMOM 5d | 2024-2025 | 0.21 | 2.08 | 10.9% | 1.83 | 0.21 | 56% |
| TSMOM 5d | 2026 | 0.12 | 0.74 | 8.9% | 0.70 | 0.12 | 58% |
| TSMOM 5d | 2024-2026 | 0.19 | 2.17 | 10.2% | 1.83 | 0.18 | 56% |

The same regressions for A1 weekly are in the same file. The largest loading is on 5-day
momentum in 2026: beta 0.35 (t 2.68), alpha 6.8% (t 0.56).

### Reading

1. **A1 follows dollar momentum in part.** The signal is more correlated with the dollar's past
   five days (0.20) than with the same day (0.10) or the next day (0.04). A1 has a modest positive
   beta on 5-day momentum: 0.19, t 2.2 over 2024-2026.
2. **Momentum does not explain A1's return.**
   - Both momentum benchmarks lost money over 2024-2026: daily dollar moves mean-reverted.
   - A1 made money, and its alpha against momentum (about 10% a year) is close to its raw mean
     (9.2%).
   - The alpha's t statistic (about 1.8) equals A1's own, so A1 is not significant at 5%, with or
     without the momentum control.
3. **In 2026 the 1-day beta turns negative** (-0.19, t -1.45): A1 is not a 1-day momentum rule.

---

## 2. US FISCAL_POLITICAL cell

Sections 2a to 2c are written in full in `results/notes/strategy_a_explained.md`, section B.
Below are the answers, with their code locations.

### 2a. Shares by sub-type and the rules defining them

**Sub-types.** They are diagnostic labels written for this check after reading the cell content;
they enter no rule (`src/report/strategy_a_explained.py`, `SUBTYPES`). Each contract gets the
first match, applied to the lower-case title plus event text:

| Order | Sub-type | Rule (regex) |
|---|---|---|
| 1 | other (not US fiscal) | `trudeau\|poilievre\|ishiba\|first leader out\|infantino\|fifa\|kimmel\|moltbook` |
| 2 | shutdown | `shut ?down\|funding bill\|back pay\|government funding\|dhs fund` |
| 3 | debt ceiling | `debt (ceiling\|limit)` |
| 4 | budget and tax bills | `budget\|reconciliation\|\btax\|big beautiful bill\|deficit\|appropriation` |
| 5 | appointments and departures | `resign\|fired\|impeach\|\bout as\b\|\bleaves?\b\|retire\|nominat\|confirm` |
| 6 | elections | `election\|presiden\|popular vote\|electoral college\|inaugurat\|balance of power\|win the (u.s. )?(house\|senate)\|control (the )?(house\|senate)\|house control\|senate control\|seats in the house\|midterm\|blue state\|drop out` |

**Measures.**
- **Volume**: the USD volume on the cell's eligible contract-days with a change.
- **Absolute contribution**: $\sum_t |w_{c,t} z_{c,t}|$, where $w_{c,t} z_{c,t}$ is the contract's
  part of the daily cell change (`src/pm/indices.py:78-84`).

**Results** (`b1_us_fiscal_subtypes.csv`; 268 contracts):

| Sub-type | Contracts | Share of contracts | Volume (USD m) | Share of volume | Share of absolute contribution |
|---|---|---|---|---|---|
| elections | 130 | 48.5% | 1,439 | 96.4% | 59.8% |
| shutdown | 109 | 40.7% | 44 | 2.9% | 31.9% |
| appointments and departures | 18 | 6.7% | 8 | 0.5% | 4.0% |
| other (not US fiscal) | 10 | 3.7% | 2 | 0.1% | 4.2% |
| debt ceiling | 1 | 0.4% | 0.03 | 0.0% | 0.1% |
| budget and tax bills | 0 | 0 | 0 | 0 | 0 |

**Why budget and tax bills are absent.** 484 US fiscal markets mention budget, reconciliation, tax
or deficit. 462 of them carry no direction: the direction lists `FISCAL_UP` / `FISCAL_DOWN`
(`src/pm/classify.py:202-207`) do not match titles such as "Will reconciliation bill be passed by
July 4?", and unsigned markets are dropped (`src/pm/contracts.py:61`). The 8 with a direction
never reach USD 50k of 7-day volume.

**The single largest contract.** "Will Donald Trump win the 2024 US Presidential Election?" alone
is 24.8% of the cell's absolute contribution.

### 2b. Direction rule per sub-type

The direction logic is `src/pm/classify.py:381-394`, applied in this order:
1. the party-stance table `data/manual/party_fiscal_stance.csv` (loaded at `classify.py:503`);
2. date buckets of a shutdown end get no sign;
3. `FISCAL_DOWN` gives -1;
4. `FISCAL_UP` gives +1.

The convention is spec 4.4 (`PROJECT_SPEC.md:196-204`): +1 is a "more expansionary fiscal outcome /
higher fiscal risk (e.g. deficit-raising party wins, budget passes with larger deficit, government
falls)".

| Sub-type | Rule and sign | What a positive signed change means | Example titles (sign) |
|---|---|---|---|
| elections, 2024 presidency | `stance:us_trump_2024` +1; `stance:us_harris_2024` -1 | higher odds of a Trump or Republican presidency | "Will Donald Trump win the 2024 US Presidential Election?" (+1); "Will Donald Trump be inaugurated?" (+1); "Will Kamala Harris win the 2024 US Presidential Election?" (-1) |
| elections, Congress | `stance:us_house_senate_r` +1; `stance:us_house_senate_d` -1; `us_sweep_r` +1 | higher odds of Republican control of a chamber | "Will Republicans win the House in 2026?" (+1); "Will Democrats win the House in 2026?" (-1); "2024 Balance of Power: R Prez R Senate R House" (+1) |
| shutdown | `fiscal:up` +1 (`shut ?down` in `FISCAL_UP`); `fiscal:down` -1 (funding, end of shutdown) | higher odds or a longer duration of a shutdown, read as higher fiscal risk | "Will the government be shut down on January 31?" (+1); "Will the federal government shut down for more than 40 days?" (+1); "Will DHS funding bill become law before Apr 1, 2026?" (-1) |
| debt ceiling | `fiscal:down` -1 | lower odds of a debt-limit increase or suspension | "Debt ceiling raised or suspended by inauguration?" (-1); only one contract |
| budget and tax bills | (none reach the cell) | | |
| appointments and departures | `fiscal:up` +1 (`resign`, `\bout\b`, `leav` in `FISCAL_UP`) | higher odds of an official leaving office, read as political instability | "Will Biden announce resignation by July 31?" (+1); "Will Mitch McConnell resign his office early?" (+1); "Will Mike Waltz resign before May 1, 2025?" (+1) |
| other (not US fiscal) | `fiscal:up` +1 | as above, but these are not US markets | "Poilievre out as leader of Conservatives in 2025?" (+1); "Will Shigeru Ishiba be the first leader out in 2025?" (+1); "Gianni Infantino out as FIFA President by December 31?" (+1) |

#### "Trump wins" is +1

The chain from the contract to the position:
- **Classification.** The stance row `us_trump_2024` matches `trump|republican|\bgop\b` in the
  title and a presidential context in the event text. It gives sign +1 with the written rationale
  "CRFB 2024: Trump platform adds more to deficits than Harris platform (TCJA extension; tariffs)"
  (`data/manual/party_fiscal_stance.csv`, written 2026-10-03, before any signal or backtest).
- **Economic channel.** Spec 1.3 (`PROJECT_SPEC.md:69-72`): under monetary dominance, fiscal
  expansion raises yields and the currency; under fiscal dominance, the currency falls.
- **Regime.** The A1 rule signs the US fiscal signal by the observed regime (D15;
  `strategy_a.py:106-107`):
  - monetary dominance: a higher fiscal signal is USD-positive;
  - fiscal dominance: it is USD-negative.
  The regime was monetary dominance throughout the 2024 election, so higher Trump odds make A1
  long USD.
- **Election day.** The jump on 2024-11-06 ($Z_{\text{FIS}}$ from 0.09 to 2.60) flipped A1 from
  -2.03 to +1.63 times NAV in USD at that day's close. The dollar had already moved: A1 lost 2.6%
  gross on 6 November (short USD) and 1.6% on 7 November (`b2_election_window.csv`).

#### Questionable signs (reported for the validation, not changed)

- **Departures signed +1 where the stance table meant neutral.** Resignations and drop-outs fall to
  the generic `FISCAL_UP` rule. The stance row `us_biden_exit_neutral` was meant to neutralise a
  Biden exit but does not match "resign".
  - 21 contracts, 5.0% of the absolute contribution.
- **Non-US markets in the US zone.** They get there through the un-located default
  (`classify.py:323-327`).
  - 10 contracts, 4.2%.
- **Kalshi `POWER` combinations with a Democratic presidency signed +1.**
  - 3 contracts, below 0.1%.

The list is in `b2_sign_review.csv`.

### 2c. A1 gross P&L: election contracts vs the rest

**Why there is no additive split.** A1 keeps only the sign of $y_t$: the volatility target cancels
its size (section 4, equation 17). An additive split of the P&L in proportion to the terms of
$y_t$ is therefore not meaningful.

**Method.** Leave-one-out counterfactuals: the US fiscal cell is re-aggregated with the frozen
code (`indices.py:78-84`, `strategy_a.py:49-64`) from a subset of its contracts, and A1 is re-run
(`run_a.evaluate`).

Results (`b3_leave_one_out.csv`, `b3_counterfactuals.csv`; annualised gross mean return):

| Removed | 2024-2025 | 2026 | 2024-2026 | Gross Sharpe 2024-2026, A1 / without |
|---|---|---|---|---|
| Election contracts | **-3.4%** (9.2% vs 12.6%) | +0.4% | -2.4% | 0.88 / 1.13 |
| Rest of the fiscal cell | +5.3% (9.2% vs 4.0%) | +0.2% | +3.9% | 0.88 / 0.51 |
| Whole US FISCAL cell | +6.7% | +0.4% | +5.0% | 0.88 / 0.41 |
| US MONETARY cell | +4.0% | **+20.6%** | +8.5% | 0.88 / 0.07 |

Reading:
- **Elections hurt A1 in 2024-2025** and are neutral in 2026.
- **The rest of the cell** (shutdowns and departures) helped in 2024-2025.
- **In 2026 the fiscal leg alone loses**: gross Sharpe -1.08, and -0.52 with elections only.
- **Caveat.** The sub-types were defined after seeing the data: "A1 without elections" is a
  decomposition, not a better rule.

---

## 3. Fed-related contracts and the recent period

Code: `src/report/strategy_a_checks.py`. Tables are in `results/notes/strategy_a_checks/`.

### 3a. Fed chair nomination, removal of Fed officials, political pressure on the Fed

**Contract groups.** These are diagnostic labels on the lower-case title (`FED_GROUPS` in the
script); they enter no rule. Each contract gets the first match:

| Group | Rule (regex) |
|---|---|
| Removal or departure of Fed officials | names Powell, Cook, Miran, Jefferson, Kugler, Barr, a governor or the Fed chair, followed by fire / remove / out / resign / leave / depart / step down / replace; or fire / remove / oust followed by Powell / Cook / Fed / governor |
| Fed chair nomination | Fed / FOMC ... chair, nominat... Fed or chair, or a candidate name (Warsh, Hassett, Rieder, Shelton, Zervos, Bullard, Waller, Bowman) followed by chair / nominat / confirm |
| Political pressure on the Fed | Fed independence, "audit / end the Fed", Trump ... Powell / the Fed / Fed chair, Lisa Cook court case |

**Results** (`a_fed_summary.csv`, `a_fed_contracts.csv`; traded volume from `pm_daily.parquet`):

| Group | Contracts | Theme, direction (rule) | In the contract panel | Volume 2024 / 2025 / 2026 (USD m) |
|---|---|---|---|---|
| Fed chair nomination | 277 | MONETARY 0 (`monetary:personnel-or-meta`): 133; OTHER: 144 | 0 | 1.3 / 29.9 / 244.5 |
| Removal or departure of Fed officials | 64 | MONETARY 0 (`personnel-or-meta`): 24; MONETARY 0 (`monetary:none`): 1; OTHER: 39 | 0 | 0.1 / 6.0 / 2.0 |
| Political pressure on the Fed | 43 | MONETARY 0 (`monetary:none`): 2; OTHER: 41 | 0 | 0.0 / 0.2 / 0.3 |

Example titles, all with sign 0:
- **Nomination**: "Will Trump nominate Judy Shelton as the next Fed chair?" (USD 85.5m); "Will
  Trump nominate Kevin Warsh as the next Fed chair?" (USD 41.4m); "Will Judy Shelton be confirmed
  as Fed Chair?".
- **Removal or departure**: "Powell leaves before 2026?"; "Will Trump try to fire Powell by August
  31?"; "Jerome Powell out as Fed Chair by May 16, 2026?".
- **Pressure**: "Will Trump sue Powell by March 31?"; "Will Trump end the Federal Reserve before
  Jan 20, 2029?"; "Trump drops Powell investigation by February 28?".

**Why none of them is in the index.**
- **MONETARY markets get no direction.** Any MONETARY title matching
  `chair|nominat|confirm|governor|leav|fire|dissent|...|\bout\b` is classified
  `monetary:personnel-or-meta` with direction 0 (`src/pm/classify.py:336-338`).
- **The others** are either theme OTHER (no theme rule matched, `classify.py:273-289`) or have no
  direction (`monetary:none`).
- **Unsigned markets are dropped from the panel** (`src/pm/contracts.py:55-62`).

**Share of the US MONETARY index contribution: 0% in 2024, 2025 and 2026**
(`a_us_monetary_share_by_year.csv`). No contract of the US MONETARY cell names a person or a
pressure word (Powell, Warsh, Hassett, Trump, chair, governor, independence; the list
`a_us_monetary_people_contracts.csv` is empty). The cell is made only of rate outcomes:
- meeting decisions (bp partitions);
- cut counts;
- hike / cut deadline markets (hazard);
- rate thresholds.

This is a design choice of the classifier (written before any backtest). The chair-nomination
markets are large in 2026 (USD 245m), but their effect on the expected rate path has no
unambiguous sign without a view on each candidate. They are therefore left out of the signal.

### 3b. Net USD position and MONETARY vs FISCAL in three windows

**Measures.**
- **USD position**: from A1's actual weights.
- **MONETARY / FISCAL terms**: in USD terms, $-y_{\text{MON}}$ and $-y_{\text{FIS}}$; > 0 favours the
  USD.
- **Counterfactuals**: "MONETARY only" sets the US fiscal signal to zero; "FISCAL only" sets the
  monetary signal to zero (`run_a.evaluate`).
- **Decisive days**: the days are classified by which term sets the sign of $y$ (see 2c).

Results (`b_windows.csv`):

| | Iran war (2026-02-26 to 04-10) | Worst drawdown (2026-03-03 to 07-30) | FOMC 2026-09-16 (09-09 to 09-24) |
|---|---|---|---|
| Trading days | 32 | 108 | 12 |
| Mean net USD position (x NAV) | +0.38 | +0.07 | **+2.02** |
| Days long USD | 62.5% | 53.7% | 100% |
| Sign changes | 6 | 23 | 0 |
| Fiscal-dominance days | 0% | 0% | 0% |
| Mean MONETARY term (USD view) | +0.52 | +0.30 | **+3.18** |
| Mean FISCAL term (USD view) | -0.37 | -0.12 | -1.48 |
| Days on which the two terms agree | 31% | 47% | 8% |
| A1 gross / net | -7.0% / -7.7% | -11.3% / -14.2% | **+5.5% / +5.5%** |
| A1 MONETARY only, gross | +3.2% | -1.3% | +5.6% |
| A1 FISCAL only, gross | -8.7% | -5.4% | -5.3% |
| USD basket (USD against G10) | +1.6% | +2.1% | +2.9% |
| A1 gross on days MONETARY and FISCAL agree | -2.8% | -3.3% | +0.1% |
| ... MONETARY sets the sign | +0.6% | -3.7% | +5.3% |
| ... FISCAL sets the sign | -5.1% | -5.1% | 0.0% |

**Around the 2026-09-16 FOMC** (`b_fomc_daily.csv`, `b_fomc_contracts.csv`):
- **The rise in the MONETARY index.** It rose every day from 9 to 18 September (+1.6 on 10
  September, +3.1 on 11 September). The rise was carried first by the hike deadline markets
  (hazard): "Will the Federal Reserve hike rates by December 31, 2026?", "Fed rate hike in 2026?"
  and "Fed Rate Hike by September 2026 Meeting?".
- **After the meeting.** On 17 September, the first snapshot after the decision (announced at
  19:00 London on 16 September), the move came from the October decision partitions
  (`fed-decision-in-october`, `KXFEDDECISION-26OCT`; cell change +2.98).
- **Position and P&L.** The monetary term dominated (the two terms agreed on 1 day in 12), and A1
  held about 2x NAV long USD throughout. It gained 5.5% while the dollar rose 2.9% against the G10
  basket.
- **This window is outside the D30 / D31 evaluation** that was reported earlier and frozen. It is
  part of the 2026 sample (to 2026-09-24).

**Reading of the three windows.** The monetary term carries A1 in 2026; the fiscal term costs
money in each window. The Iran-war loss and the drawdown come from:
1. FISCAL setting the sign against MONETARY (-5.1% in both windows);
2. the whipsaw of a sign-only rule between two near-zero terms (23 sign changes in 108 days).

### 3c. Average USD position and the residual drift of the MONETARY index

*Corrected 2026-10-08 (see `DECISIONS.md`).*
- The first version proposed longshot decay of the large-cut buckets as the source of the drift.
  The source is the per-meeting decision partitions; the cut-count partitions contribute almost
  nothing.
- A preliminary computation also put most of the 2026 drift in the last week before meetings. It
  measured days to the contract's last day in the panel, which for contracts still open at the end
  of the sample is the end of the sample, not the meeting. The table below uses `ttr_days`
  (days to the market's close, which is the meeting day).

These breakdowns were computed for this correction (scratchpad, not in the tables of the script).

**The drift by period** (`c_monetary_drift.csv`). Mean daily change of the US MONETARY cell on
active days ($d_{\text{MON}}$, equation 6 of section 4):

| Period | Active days | Mean $d_{\text{MON}}$ | t (mean) | Index change | from bp partitions | from hazard | from probability | Mean $Z_{\text{MON}}$ | Days $Z_{\text{MON}} > 0$ |
|---|---|---|---|---|---|---|---|---|---|
| 2024-2025 | 671 | +0.033 | 1.00 | +22.3 | +34.6 | -13.2 | +0.9 | +0.14 | 55% |
| 2026 | 267 | +0.123 | 2.44 | +32.9 | +27.4 | +4.7 | +0.8 | +0.51 | 81% |
| 2024-2026 | 938 | +0.059 | 2.12 | +55.2 | +62.0 | -8.4 | +1.7 | +0.24 | 62% |

**By year and contract type.** Index change by contract type; partition types from
`contracts_classified.parquet`:

| Year | Mean $d_{\text{MON}}$ (t) | Index change | Decision partitions | Cut-count partitions | Rate-level partitions | Hazard | Probability |
|---|---|---|---|---|---|---|---|
| 2024 | -0.008 (-0.16) | -2.3 | +10.1 | -0.3 | 0 | -12.7 | +0.5 |
| 2025 | +0.068 (1.50) | +24.7 | +22.6 | +2.1 | 0 | -0.4 | +0.4 |
| 2026 | +0.123 (2.44) | +32.9 | +26.1 | +0.8 | +0.5 | +4.7 | +0.8 |

- **There is no drift in 2024**: the hazard markets offset the decision partitions.
- **The drift is positive but not significant in 2025**, and significant only in 2026.
- **It comes from the per-meeting decision partitions.**
- **It is not the "number of cuts" mechanism.** The annual cut-count partitions contribute -0.3,
  +2.1 and +0.8. Their expected values do not shift steadily toward fewer cuts:
  - 2024: Kalshi from -132 to -102 bp; Polymarket "this year" from -33 to -99 bp;
  - 2025: from -60 to -87 bp;
  - 2026: from -99 to -11 bp and from -85 to -3 bp, the hawkish repricing.

**Decision partitions by days to the meeting.** The meeting is the market's close (`ttr_days`);
eligibility stops at 3 days (`contracts.py:166`).

| Year | Days to meeting | Contract-days | Mean change (bp/day) | Median own EWMA sd (bp) | Mean \|z\| | Share of z at the +/-5 cap | Mean weight in the cell | Index change |
|---|---|---|---|---|---|---|---|---|
| 2024 | 3-7 | 40 | -0.38 | 1.29 | 0.85 | 0% | 0.38 | -3.6 |
| 2024 | 8-14 | 58 | -0.01 | 1.34 | 0.44 | 0% | 0.36 | -0.8 |
| 2024 | 15-30 | 122 | -0.07 | 1.47 | 0.53 | 0.8% | 0.36 | -2.1 |
| 2024 | 31-90 | 221 | +0.27 | 1.16 | 0.78 | 1.8% | 0.21 | +16.7 |
| 2025 | 3-7 | 62 | +0.13 | 1.08 | 0.24 | 0% | 0.53 | +2.5 |
| 2025 | 8-14 | 108 | -0.10 | 1.12 | 0.27 | 0% | 0.45 | -1.0 |
| 2025 | 15-30 | 244 | +0.02 | 1.21 | 0.50 | 0.4% | 0.44 | +7.2 |
| 2025 | 31-90 | 520 | +0.06 | 1.09 | 0.67 | 1.3% | 0.25 | +13.1 |
| 2025 | >90 | 117 | +0.02 | 1.13 | 0.72 | 0% | 0.06 | +0.7 |
| 2026 | 3-7 | 48 | +0.32 | 0.65 | 0.45 | 0% | 0.53 | +5.2 |
| 2026 | 8-14 | 82 | +0.07 | 0.72 | 0.33 | 0% | 0.47 | +2.8 |
| 2026 | 15-30 | 187 | +0.11 | 0.84 | 0.45 | 0% | 0.44 | +7.9 |
| 2026 | 31-90 | 500 | +0.14 | 1.00 | 0.55 | 0.6% | 0.18 | +9.9 |
| 2026 | >90 | 64 | +0.18 | 0.89 | 0.92 | 0% | 0.03 | +0.4 |

**Is the drift a low-volatility, large-z effect just before meetings? No.**
1. **The drift is not concentrated in the last days.** Most of it builds 15 to 90 days before the
   meeting: in 2026, +17.8 of +26.1; in 2025, +20.3 of +22.6; in 2024, +16.7 against negative
   short horizons.
2. **The own EWMA volatility is lower near meetings in 2026** (median 0.65 bp at 3-7 days against
   1.00 bp at 31-90 days). But the z scores are not larger:
   - mean |z| is 0.45 at 3-7 days against 0.55 at 31-90 days in 2026, and 0.24 against 0.67 in
     2025;
   - no z reaches the +/-5 cap within 14 days of a meeting.
3. **What changes near meetings is the weight.** The meeting's partition holds about half of the
   cell's volume in its last two weeks (mean weight 0.45 to 0.53, against about 0.2 at 31-90
   days). In 2026 the bp change per day is also larger (+0.32 bp a day at 3-7 days).
4. **2026 shows a genuine repricing.** The positive mean change at every horizon matches realised
   decisions that were more hawkish than priced (the move from cuts to the September hike).
   Demeaning cannot separate this from a pricing bias.

**A1's average USD position, and the part due to the drift** (`c_usd_position_drift.csv`):
- **Method.** Counterfactuals re-run A1 with the US MONETARY cell change demeaned:
  - **causally**: the expanding mean up to t-1, the D12 method (`strategy_a.py:55-59`);
  - **ex post**: the 2024-2026 mean, which uses look-ahead and is shown only as a bound.
- The fiscal leg is unchanged.

| Run | Mean USD position 2024-2025 | 2026 | Days long USD 2024-2025 / 2026 | Gross Sharpe 2024-2025 | 2026 | 2024-2026 |
|---|---|---|---|---|---|---|
| A1 | **+0.38** | **+0.35** | 60% / 60% | 0.89 | 0.85 | 0.88 |
| A1, MONETARY demeaned causally | +0.09 | -0.06 | 53% / 48% | 0.71 | **-0.07** | 0.49 |
| A1, MONETARY demeaned ex post (look-ahead) | +0.07 | -0.19 | 52% / 44% | 0.45 | -0.50 | 0.19 |
| A1 MONETARY only | +0.21 | +1.10 | 55% / 81% | 0.25 | 0.81 | 0.41 |
| A1 MONETARY only, demeaned causally | -0.23 | +0.49 | 43% / 63% | -0.08 | 0.35 | 0.04 |

**Reading.**
1. **A1 has a long-USD tilt**: +0.37 times NAV on average, long USD on 60% of days, in both
   periods.
2. **The drift explains most of the tilt.** Demeaning the MONETARY change causally cuts the mean
   USD position by 0.29 in 2024-2025 (from 0.38 to 0.09, about three quarters) and by 0.41 in
   2026 (from +0.35 to -0.06, all of it).
3. **The drift also explains most of A1's 2026 performance.** Without it, A1's 2026 gross Sharpe
   falls from 0.85 to -0.07; in 2024-2025 it falls from 0.89 to 0.71.
4. **What this does and does not say.**
   - Most of A1's 2026 gain comes from a persistent hawkish US MONETARY signal, held long USD.
   - Demeaning cannot separate a pricing bias in the decision partitions from a genuine trend in
     expectations (the move to a hike in 2026). Both are removed together.
   - This does not contradict the static / timing decomposition of D25
     (`results/strategy_a/decomposition_static_timing.csv`, `run_a.py:229-251`). D25's static
     position is the 2024-2025 average of A1's weights (about 0.38 long USD, `run_a.py:236`),
     applied to every period.
     - Over 2024-2026: static 0.8% a year, timing 8.4%.
     - On 2026 alone, with the 2024-2025 average: total 9.1%, static 1.5% (Sharpe 0.64), timing
       7.6%.
     - On 2026 alone, with the 2026 average (0.35 long USD, ex post): static 1.2%, timing 7.9%.
     - The drift acts through the timing of the sign, not through a constant long-USD premium.
5. **No change follows from this check.** The demeaned version is the D12 robustness variant
   already reported for A1 (`A1_theory_with_dollar_D12`, which also uses the probability panel).

### 3d. Cell-level standardisation of the fiscal signal, and the presidential market

These numbers were computed for this correction (scratchpad, not in the tables of the script).

**Window.** The scale is **expanding**, not rolling (`strategy_a.py:61-63`):
- the standard deviation of the smoothed cell signal $S$, over all calendar days since the cell's
  first active day;
- at least 20 values; lagged one day; used once the cell has 20 active days.

It is computed separately for each cell, so MONETARY and FISCAL each have unit scale by
construction.

**The 2024 election barely inflates the scale.** The scale $\mathrm{sd}(S_{\text{FIS}})$:

| Date | All contracts | Without `presidential-election-winner-2024` | Without the five 2024 presidential events | US MONETARY scale |
|---|---|---|---|---|
| 2024-11-05 | 0.244 | 0.217 | 0.206 | 0.234 |
| 2024-11-10 | 0.248 | 0.221 | 0.205 | 0.233 |
| 2025-12-31 | 0.322 | 0.318 | 0.332 | 0.216 |
| 2026-09-24 | 0.307 | 0.304 | 0.316 | 0.216 |

- **Why the election day hardly moves it.** Each contract's z is capped at 5, and the cell signal
  is smoothed (half-life 5 days). On 2024-11-06, $S_{\text{FIS}}$ was 0.63; its peak in the sample
  is 1.80, on 2025-09-27, during the 2025 shutdown.
- **The election market's effect on the scale is spread over its whole life.** It raises the scale
  by about 12% through 2024, but only about 1% by 2026.
- **The 2025 shutdown episode is what inflates the fiscal scale.** It goes from 0.21 to 0.32
  during 2025, while the monetary scale stays near 0.22. This compresses $Z_{\text{FIS}}$ in 2026.

**Effective weight of FISCAL relative to MONETARY in A1**, by year:

| Year | Mean \|Z_MON\| | Mean \|Z_FIS\| | Ratio FIS / MON | Ratio of std | Days FISCAL sets the sign | Days MONETARY sets the sign | Ratio FIS / MON without the presidential market |
|---|---|---|---|---|---|---|---|
| 2024 | 0.92 | 0.75 | 0.82 | 0.78 | 14.9% | 22.5% | 0.68 |
| 2025 | 0.71 | 0.76 | 1.06 | 1.70 | 17.2% | 31.4% | 1.12 |
| 2026 | 0.79 | 0.55 | 0.70 | 0.68 | 21.5% | 35.1% | 0.71 |

The two terms have the same nominal weight. FISCAL's effective weight is about 0.8 of
MONETARY's in 2024, 1.1 in 2025 and 0.7 in 2026. The 2026 compression comes from the 2025
shutdown, not from the 2024 election.

**The presidential market's leave-one-event-out result is fragile, not informative.**
- Removing `presidential-election-winner-2024` lowers A1's net Sharpe from 0.43 to 0.30
  (`results/robustness/strategy_a.csv`).
- It changes the sign of $y$ on 36 days in 2024, none in 2025 and **one day in 2026**.
- That day is 2026-01-29: $y$ is -0.016 with the market and +0.002 without, because the monetary
  and fiscal terms (-1.39 and +1.37) nearly cancel.
- A1's return of 2026-01-30 (+1.7% against -1.7%) accounts for +3.3 points of the difference. That
  is the whole of the market's 2026 contribution.
- **A sign-only rule makes single-event robustness checks sensitive to near-zero days.**

---

## 4. Signal construction, as numbered equations

The full derivation, with every code location, is in `results/notes/strategy_a_explained.md`,
section A. Summary with locations:

**Eligibility, contract level** (`src/pm/contracts.py:164-169`, `config/config.yaml:42-48`).
A contract-day is eligible if:
- trailing 7-day USD volume >= 50,000;
- 3 to 365 days to close;
- price in [0.03, 0.97] for binaries; for partitions, at least 2 priced buckets and bucket prices
  summing to 0.5 to 1.5.

The same USD 50k is used by the coverage rule (`src/pm/coverage.py:52-66`), which counts a
cell-weekday as covered if one contract is eligible. Only markets with a direction or in a
partition enter the panel (`contracts.py:55-62`).

1. **Snapshot price and staleness** (`src/data/pm_panel.py:59-95`, `contracts.py:101, 163`). The
   snapshot is the last trade strictly before 16:00 London, forward-filled; no VWAP, no mid.
   Stale if there is no trade in the 6 hours before the snapshot:

$$ p_{c,t} = \text{last Yes price in } [16{:}00_{t-1}, 16{:}00_t) \text{ London}, \qquad \text{fresh}_{c,t} = \mathbf 1\{16{:}00_t - \text{lastTrade}_{c,t} \le 6\text{h}\}. $$

2. **Value** (`contracts.py:116-156`). Binary: $v = p$. Deadline binary (D18):
   $v = -\ln(1 - \mathrm{clip}(p, 0.001, 0.999))/\tau$, with $\tau = \max(\text{ttr}, 3)/365.25$.
   Partition:

$$ v = \sum_b p_b x_b \Big/ \sum_b p_b. $$

   Units of the partitions:
   - **bp**: MONETARY, 197 contracts: meeting decision in bp; -25 x number of cuts; rate level;
   - **pp**: INFLATION, 98: CPI bucket midpoint;
   - **pct**: TRADE_TARIFFS, 16: tariff-rate bucket midpoint.

   Open-ended buckets get the threshold +/- half the median bucket width (`classify.py:440-488`).
3. **Daily-scaled change** between fresh snapshots at most 7 days apart (D19; `src/pm/indices.py:45-50`):

$$ \Delta_{c,t} = (v_{c,t} - v_{c,t'})/\sqrt{t - t'}. $$

4. **EWMA volatility** (`indices.py:54-67`): **span 60** (half-life about 20.8 changes) of
   $\Delta^2$, **lagged by one change** (`.shift(1)`), so only changes strictly before t are used.
   Before 5 earlier changes, the scale is a causal fallback: the expanding median $|\Delta|$ of the
   same unit, before t, x 1.4826.
5. **Standardised signed change** (`indices.py:68`):

$$ z_{c,t} = \mathrm{clip}(s_c \Delta_{c,t}/\sigma_{c,t}, -5, 5). $$

6. **Aggregation within a cell**, with weights equal to the trailing 7-day volume, including day
   t's pre-snapshot volume (`indices.py:78-84`). There is no re-standardisation at the index
   level:

$$ d_{k,t} = \sum_c \text{vol7d}_{c,t} z_{c,t} \Big/ \sum_c \text{vol7d}_{c,t}, \qquad I_{k,t} = \sum_{u\le t} d_{k,u}. $$

7. **Smoothing** (`src/strategies/strategy_a.py:53-60`, `config.yaml:60-61`): EWMA with
   **half-life 5 calendar days**, inactive days entered as 0:

$$ S_{k,t} = \mathrm{EWMA}_{hl=5}(d_{k,\cdot}). $$

8. **Equal-risk scaling** (`strategy_a.py:61-64`): $Z_{k,t} = S_{k,t}/\mathrm{sd}(S_{k,u \le t-1})$,
   expanding, from 20 active days (0 before).
9. **Fiscal regime** (D15; `strategy_a.py:71-80`, `src/strategies/run_a.py:29-40`):
   $R_t = \mathbf 1\{\mathrm{corr}_{60}(\Delta y^{10}_{US}, \Delta\text{USD})_{t-1} < 0\}$.
10. **A1 forecast**, common to the 9 pairs (`strategy_a.py:103-113, 150-151`):

$$ y_t = -Z_{\text{MON},t} - (1 - 2R_t)\, Z_{\text{FIS},t}. $$

11. **Raw position** (`strategy_a.py:166-175`):

$$ \text{raw}_{i,t} = y_t/\sigma^2_{i,t}, $$

    where $\sigma^2_{i,t}$ is the EWMA variance (span 60) of the pair's excess return up to t.
12. **Volatility target** (`src/backtest/engine.py:24-45`): scale to 10% a year with the EWMA
    covariance (span 60) up to t.
13. **Caps** (`engine.py:46-56`, `config.yaml:73-74`):
    - each pair is capped at 30% of the pre-cap gross;
    - the gross is capped at 3x;
    - volatility is not re-targeted after a cap.
14. **No-trade band** of 10% (`engine.py:89-100`).
15. **Execution** at the New York close of t, return on t+1 (`engine.py:114-134`):

$$ r_{t+1} = \sum_i w_{i,t}\, rx_{i,t+1} - \text{costs}. $$

16. **Consequence**: since $y_t$ is common to all pairs, the volatility target removes its size:

$$ w_{i,t} = \mathrm{sign}(y_t)\,\kappa_t/\sigma^2_{i,t}. $$

    A1 is long or short the USD against a fixed inverse-variance G10 basket; only the sign of
    $y_t$ matters.
