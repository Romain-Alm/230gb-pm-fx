# Strategy A explained: signal chain, US fiscal cell, dollar momentum, 2026 drawdown

Diagnostics and documentation only (2026-10-07). Scope is frozen: no rule, variant or parameter
was changed; every series below is the frozen pipeline, decomposed or compared. Logged in
`DECISIONS.md` (2026-10-07, reporting/diagnostic).

- Script: `src/report/strategy_a_explained.py` (about one minute; `python -m src.report.strategy_a_explained`).
- Tables: `results/notes/strategy_a_explained/*.csv`; figure: `results/notes/strategy_a_explained/a1_2026_decomposition.png`.
- Code locations are `file:line` in the repository at the time of writing.
- "A1" is the primary A1 rule with dollar exposure (`A1_theory_with_dollar`). Returns are daily;
  "gross" is before trading costs. Periods: 2024-2025 (training), 2026 (2026-01-01 to 2026-09-24),
  2024-2026.

---

## A. Signal construction (what the code does)

### A.1 Contract eligibility

A market enters the contract panel if (`src/pm/contracts.py:55-62`):
- its theme is not `OTHER` and it has at least one zone;
- it has a direction (`direction <> 0`) **or** it belongs to a partition (bucket event).

A contract-day is **eligible** if all of the following hold (`src/pm/contracts.py:164-169`, thresholds in `config/config.yaml:42-48`):

| Condition | Rule | Location |
|---|---|---|
| Volume | trailing 7-day USD volume `vol7d >= 50,000` | `contracts.py:165`, `config.yaml:43` |
| Time to close | `3 <= ttr_days <= 365`, with `ttr` measured from the snapshot to `coalesce(closes_at, resolves_at)` | `contracts.py:131, 166`, `config.yaml:45-46` |
| Price band (binary and hazard) | `0.03 <= p <= 0.97` | `contracts.py:167`, `config.yaml:47-48` |
| Partition | at least 2 buckets with a price and sum of bucket prices in [0.5, 1.5] | `contracts.py:168` |

**Contract-level threshold vs coverage rule.** It is the same USD 50k threshold. The volume
rule applies to each contract-day. The coverage rule (`src/pm/coverage.py:52-66`) then counts a
cell-weekday as covered if at least one contract of the cell is eligible that day. A cell is
kept if it is covered on at least 60% of the 2024-2025 weekdays (`config.yaml:50-51`). A1 uses
the 50k panel (`src/strategies/run_a.py:68, 93`) and its two cells, US MONETARY and US
FISCAL_POLITICAL, both pass (94% and 69%).

Notes:
- **Partition volume.** For a partition, `vol7d` is the sum over its buckets (`contracts.py:149`).
- **Eligibility vs freshness.** Eligibility does not require a fresh price. Freshness is
  required separately to form a change (A.2).

**Direction requirement.** The direction comes from the rule-based classifier
(`src/pm/classify.py:334-394`). Within a partition the per-market direction is set to 0 and the
bucket value carries the sign (`classify.py:486-487`).

**Partition buckets** (`classify.py:440-488`):

| Theme | Partition condition | `bucket_value` | Unit |
|---|---|---|---|
| MONETARY, decision events | at least 2 markets with a parsed bp change, at least 2 distinct values | the bp change | bp |
| MONETARY, cut-count events | at least 2 distinct counts | -25 x count | bp |
| MONETARY, policy-rate level buckets | at least 2 levels | the level | bp |
| INFLATION, TRADE_TARIFFS | at least 2 bracket markets | the bracket midpoint; open-ended buckets get threshold +/- half the median bucket width | pp (inflation), pct (tariff rate) |

### A.2 Snapshot price

The snapshot price is the **last trade strictly before 16:00 Europe/London**. There is no VWAP
and no mid (`src/data/pm_panel.py:59-95`):
- **Yes price** (`pm_panel.py:61`): `px_yes = price if is_yes_side else 1 - price`. Only trades
  with `0 < price < 1` are kept.
- **Trade window** (`pm_panel.py:69-71`): a trade at local time before 16:00 belongs to that
  day's snapshot; a trade at or after 16:00 belongs to the next day. The window of day t is
  therefore [16:00 on t-1, 16:00 on t) London time. Daylight saving is handled per date by
  `timezone('Europe/London', ...)` (`pm_panel.py:63`).
- **Price kept** (`pm_panel.py:82`): `px_last = arg_max(px_yes, timestamp)`.
- **Volume-weighted price, not used.** A last-hour VWAP is computed (`pm_panel.py:83`) but no
  signal uses it. There is no order-book mid in the data.
- **Days without a trade** (`contracts.py:101`): the last price is forward-filled.

**Staleness window.** A contract-day is stale if its last trade is more than 6 hours before the
16:00 snapshot, that is before 10:00 London, or if it has never traded (`contracts.py:163`,
`config.yaml:40`). Stale rows are dropped before any change is formed (`src/pm/indices.py:41`).

**Partitions.** Each bucket price is the forward-filled last trade of that bucket. The partition
is fresh if **any** bucket traded within the 6 hours, because staleness uses `max(last_ts)` over
the buckets (`contracts.py:149`).

### A.3 Units bp / pp / pct (311 partition contracts)

The 311 unit-bearing contracts are bucket events, one contract per event, valued as an expected
value over the buckets. The value is renormalised by the sum of bucket prices
(`contracts.py:137-156`):

$$ V_{e,t} = \frac{\sum_b p_{b,t}\, x_b}{\sum_b p_{b,t}} \qquad (b \text{ buckets of event } e \text{ with a price}). $$

| Unit | Theme | Contracts in panel | Eligible at least once | Typical event (buckets: value) |
|---|---|---|---|---|
| bp | MONETARY | 197 | 66 | Fed decision at a meeting (`fed-decision-in-january`): 50+ bp cut: -50, 25 bp cut: -25, no change: 0, 25+ bp hike: +25. Value = expected bp change at that meeting. Cut-count events (`how-many-fed-rate-cuts-in-2026`): -25 x expected number of cuts. |
| pp | INFLATION | 98 | 19 | `march-inflation-us-annual`: "2.0% or less": 1.95, "2.1%": 2.1, ... Value = expected CPI print in pp. |
| pct | TRADE_TARIFFS | 16 | 6 | `us-tariff-rate-on-china-on-august-15`: "less than 25%": 10, "between 25% and 40%": 32.5, ..., "greater than 150%": 165. Value = expected tariff rate. |

Counts are in `a_units.csv` and `a_partition_cells.csv`. The rest of the panel:
- 5,818 binary markets are valued as probabilities;
- 2,974 deadline binaries are valued as implied hazard rates (D18):
  $-\ln(1-\min(\max(p,0.001),0.999))/\tau$, with $\tau = \max(\text{ttr}, 3)/365.25$ years
  (`contracts.py:116-129`). A binary is a deadline market if its title matches `DEADLINE_RE`
  (`contracts.py:30-33, 79-81`).

**In A1** (`a_units_in_a1_cells.csv`):
- **US MONETARY** has 110 contracts: 53 bp partitions carry 82% of the absolute index
  contribution, 33 hazard contracts 15% and 24 probability contracts 3%.
- **US FISCAL_POLITICAL** has 268 contracts and no partition: 216 probability contracts (62% of
  the absolute contribution) and 52 hazard contracts (38%).
- A1 uses no pp or pct contract (INFLATION and TRADE_TARIFFS are not A1 cells).

**Side effect of `DEADLINE_RE`.** Because the pattern matches "in 2026", some election outcome
markets are valued as hazard rates (for example "Will Republicans win the House in 2026?").

### A.4 EWMA volatility used for standardisation

Code: `src/pm/indices.py:37-75`; parameters in `config.yaml:53-55` and `indices.py:33-34`.

- **Change.** The change is taken between two **fresh** snapshots of the same contract at most 7
  days apart. A change spanning g days is divided by $\sqrt{g}$ (D19; `indices.py:45-50`).
- **Own variance.** EWMA with **span 60** (not a half-life; equivalent half-life about 20.8
  changes, `adjust=True`) of past squared changes, **shifted by one change**:
  `(dv**2).ewm(span=60).mean().shift(1)` within each contract (`indices.py:54`). The variance used
  at t uses only changes strictly before t, so sigma is lagged. The lag is one observation of the
  contract, which can be several calendar days.
- **Minimum history and fallback.**
  - Each contract has a change index k = 0, 1, 2, ... (`n_past`). The own volatility is used from
    k = 5 on, that is once 5 earlier changes exist (`MIN_OBS = 5`, `indices.py:34, 67`).
  - Before that, the scale is a causal fallback: the expanding median of |dv| over all contracts
    of the same unit, strictly before day t, times 1.4826 (`indices.py:55-65`).
  - So a contract contributes from its first change, which needs one previous fresh snapshot
    within 7 days. It uses the fallback scale for its first 5 changes.
- **Winsorisation** at +/-5 (`indices.py:68`, `config.yaml:55`).

### A.5 Aggregation within a cell

Code: `src/pm/indices.py:78-84, 97-119`.

- **Weights.** Volume weights: $w_{c,t} = \text{vol7d}_{c,t} / \sum_{c'} \text{vol7d}_{c',t}$ over
  the eligible contracts with a standardised change that day.
- **What `vol7d` covers.** It is the USD volume of days t-6 to t, where each day's volume is the
  24-hour window ending at that day's 16:00 snapshot (`contracts.py:103-104`, `pm_panel.py:87`).
  It therefore includes the pre-snapshot volume of day t.
- **Equal weights.** An equal-weighted change `d_ew` is also computed (`indices.py:82`); A1 does
  not use it.
- **No re-standardisation at the index level.** `d_vw` is the weighted mean of the contract z
  scores. It is set to 0 on days without contributions, and the index is its cumulative sum
  (`indices.py:114-117`).
- **Re-standardisation at the signal level** (A.6, step 9): the smoothed cell signal is divided by
  its own expanding standard deviation (equal risk across themes).

### A.6 From index change to A1 position, as equations

For contract c in cell k (US MONETARY = MON, US FISCAL_POLITICAL = FIS), currency pair i (the
nine G10 currencies against USD), snapshot day t:

1. **Snapshot price.** $p_{c,t}$ is the last Yes price traded in [16:00 on t-1, 16:00 on t)
   London, forward-filled. It is fresh if $\text{snap}_t - \text{lastTrade}_{c,t} \le 6\text{h}$
   (`pm_panel.py:59-95`, `contracts.py:101, 163`).
2. **Contract value** (`contracts.py:116-156`):

$$ v_{c,t} = \begin{cases} p_{c,t} & \text{binary} \\ -\ln\big(1-\mathrm{clip}(p_{c,t},0.001,0.999)\big)\,/\,\tau_{c,t} & \text{deadline binary (D18)} \\ \sum_b p_{b,t} x_b / \sum_b p_{b,t} & \text{partition} \end{cases} $$

3. **Eligibility** (`contracts.py:164-169`):

$$ E_{c,t} = \mathbf 1\{\text{vol7d}_{c,t} \ge 50\text{k},\ 3 \le \text{ttr}_{c,t} \le 365,\ \text{price band or partition condition}\}. $$

4. **Daily-scaled change** between fresh snapshots, with t' the previous fresh day of c and
   $t-t' \le 7$ (`indices.py:45-50`):

$$ \Delta_{c,t} = \frac{v_{c,t} - v_{c,t'}}{\sqrt{t-t'}}. $$

5. **Lagged own volatility** over the contract's earlier changes (`indices.py:54-67`):

$$ \sigma^2_{c,t} = \mathrm{EWMA}_{\text{span }60}\big(\Delta^2_{c,\cdot}\big) \text{ (earlier changes only)}, $$

   or the unit fallback if c has fewer than 5 earlier changes.
6. **Signed standardised change**, with $s_c \in \{-1,+1\}$ the contract sign; $s_c = +1$ for
   partitions (`indices.py:68`):

$$ z_{c,t} = \mathrm{clip}\big(s_c\,\Delta_{c,t}/\sigma_{c,t},\,-5,\,5\big). $$

7. **Cell change**, over eligible contracts with a change (zero if none), and **index**
   (`indices.py:78-84, 116`):

$$ d_{k,t} = \frac{\sum_c \text{vol7d}_{c,t}\, z_{c,t}}{\sum_c \text{vol7d}_{c,t}}, \qquad I_{k,t} = \sum_{u \le t} d_{k,u}. $$

8. **Smoothing.** EWMA with half-life 5 calendar days. Days without an active contract enter as
   0 (`strategy_a.py:53-60`, `config.yaml:60-61`):

$$ S_{k,t} = \mathrm{EWMA}_{\text{hl }5}\big(d_{k,\cdot}\,\mathbf 1\{\text{active}\}\big)_t. $$

9. **Equal-risk scaling** (`strategy_a.py:61-64`, `MIN_ACTIVE = 20` at `strategy_a.py:46`):

$$ Z_{k,t} = \frac{S_{k,t}}{\mathrm{sd}\{S_{k,u}: u \le t-1\}} \text{ if the cell has at least 20 active days before } t, \text{ else } 0. $$

   The standard deviation is expanding over calendar days since the cell's first active day,
   with at least 20 values.
10. **Fiscal regime** (D15; `strategy_a.py:71-80`, `run_a.py:29-40`). The US value is minus the
    mean log G10 spot, i.e. the dollar against an equal-weighted basket (`run_a.py:37`). R is the
    correlation of daily changes in US10Y and the US value over 60 trading days (at least 30
    observations), lagged one trading day; $R_t = 1$ (fiscal dominance) if $\rho_t < 0$. Missing
    values count as 0 (`strategy_a.py:101`).

$$ \rho_t = \mathrm{corr}_{60}\big(\Delta y^{10}_{US}, \Delta \text{USD}\big)_{t-1}, \qquad R_t = \mathbf 1\{\rho_t < 0\}. $$

    In the sample $R_t = 1$ on 12 days only, all between 8 May and 30 June 2025 (2.3% of
    2024-2025, none in 2026). In practice the fiscal sign is the monetary-dominance sign.
11. **A1 forecast**, identical for the nine pairs (foreign currency against USD). It is the
    foreign leg minus the US leg, with no foreign cell in A1 (`strategy_a.py:103-113, 150-151`;
    business days, signals forward-filled at `strategy_a.py:96`). Under monetary dominance a rise
    in the fiscal signal (more expansion) is USD-positive, so $y_t$ falls:

$$ y_t = -\,Z_{\text{MON},t} \;-\; (1 - 2R_t)\, Z_{\text{FIS},t}. $$

12. **Raw position**, with $\sigma^2_{i,t}$ the EWMA (span 60, at least 20 observations) variance
    of the pair's daily excess return up to the close of t (`strategy_a.py:166-175`):

$$ \text{raw}_{i,t} = y_t / \sigma^2_{i,t}. $$

13. **Volatility target.** $\Sigma_t$ is the EWMA covariance (span 60, uncentred, returns up to t;
    `engine.py:24-35`). Scale to 10% annual volatility (`engine.py:38-45`):

$$ w = \text{raw}\cdot\frac{0.10}{\sqrt{252\,\text{raw}^\top \Sigma_t\, \text{raw}}}. $$

14. **Caps** (`engine.py:46-56`, `config.yaml:73-74`):
    - **per pair, 30%:** each $|w_i|$ is clipped at $0.30\sum_j |w_j|$, where the gross is
      measured **before** clipping;
    - **gross, 3x:** if $\sum_j |w_j| > 3$, all weights are scaled down to a gross of 3;
    - volatility is **not** re-targeted after a cap.
15. **No-trade band** (`engine.py:89-100`, `config.yaml:75`): the previous weight is kept unless
    $|w^{\text{target}}_{i,t} - w_{i,t-1}| > 0.10\,|w_{i,t-1}|$, or either of the two weights is
    zero.
16. **Execution and P&L.** The trade is executed at the New York close of t (G10, D28). The cost is
    the causal 20-day median bid-ask half-spread of the 1-month forward (`market.py:123-130`,
    `engine.py:114-134`):

$$ r_{t+1} = \sum_i w_{i,t}\, rx_{i,t+1} \;-\; \sum_i |w_{i,t} - w_{i,t-1}|\, h_{i,t}, \qquad rx_{i,t+1} = s_{i,t+1} - s_{i,t} + \text{carry}_{i,t}/252. $$

17. **Consequence.** Because $y_t$ is common to all pairs, the volatility target cancels its
    magnitude. Before caps:

$$ w_{i,t} = \mathrm{sign}(y_t)\,\frac{\kappa_t}{\sigma^2_{i,t}}, \qquad \kappa_t \text{ set so that the volatility is } 10\%. $$

    **A1 is long or short the USD against a fixed inverse-variance G10 basket. Only the sign of
    $y_t$ matters, not its size.** This explains the following:
    - the mean gross exposure is 1.69 (2024-2025) and 1.84 (2026);
    - the net USD position jumps between about +2 and -2 (figure, middle panel);
    - there are 65 sign changes in 523 days in 2024-2025 and 36 in 191 days in 2026;
    - the position sign equals the signal sign on 100% of days (`b3_position_vs_signal_sign.csv`).

**A1 weekly** (reported variant) holds the A1 weights decided on the last trading day of each
week (`run_a.py:76-86, 186-189`).

---

## B. US FISCAL_POLITICAL cell content

### B.1 Shares by sub-type

**What the sub-types are.** They are diagnostic labels written for this note after reading the
cell content; they enter no rule. Each contract gets the first matching rule, applied to the
lower-case title plus event text (`strategy_a_explained.py`, `SUBTYPES`):

| Order | Sub-type | Rule (regex) |
|---|---|---|
| 1 | other (not US fiscal) | `trudeau\|poilievre\|ishiba\|first leader out\|infantino\|fifa\|kimmel\|moltbook` |
| 2 | government shutdown | `shut ?down\|funding bill\|back pay\|government funding\|dhs fund` |
| 3 | debt ceiling | `debt (ceiling\|limit)` |
| 4 | budget and tax bills | `budget\|reconciliation\|\btax\|big beautiful bill\|deficit\|appropriation` |
| 5 | appointments and departures | `resign\|fired\|impeach\|\bout as\b\|\bleaves?\b\|retire\|nominat\|confirm` |
| 6 | elections | `election\|presiden\|popular vote\|electoral college\|inaugurat\|balance of power\|win the (u.s. )?(house\|senate)\|control (the )?(house\|senate)\|house control\|senate control\|seats in the house\|midterm\|blue state\|drop out` |

The fallback label "other" catches no contract.

**What the measures are.**
- **Volume**: the USD volume on the cell's eligible contract-days with a change.
- **Absolute index contribution**: $\sum_t |w_{c,t} z_{c,t}|$, where $w_{c,t} z_{c,t}$ is the
  contract's share of the cell change $d_t$ (A.6 step 7).

**Results** (`b1_us_fiscal_subtypes.csv`; 268 contracts, 5,897 contract-days):

| Sub-type | Contracts | Share of contracts | Volume (USD m) | Share of volume | Share of absolute contribution |
|---|---|---|---|---|---|
| elections | 130 | 48.5% | 1,439 | 96.4% | 59.8% |
| government shutdown | 109 | 40.7% | 44 | 2.9% | 31.9% |
| appointments and departures | 18 | 6.7% | 8 | 0.5% | 4.0% |
| other (not US fiscal) | 10 | 3.7% | 2 | 0.1% | 4.2% |
| debt ceiling | 1 | 0.4% | 0.03 | 0.0% | 0.1% |
| budget and tax bills | 0 | 0 | 0 | 0 | 0 |

**No budget or tax-bill market reaches the cell.** 484 US FISCAL_POLITICAL markets mention
budget, reconciliation, tax or deficit in their title:
- **462 carry no direction** (`fiscal:none`). The classifier's lists only cover `tax cut` in
  `FISCAL_UP` and `budget (pass|approved)` in `FISCAL_DOWN` (`classify.py:202-207`), so titles
  such as "Will reconciliation bill be passed by July 4?" or "Will Trump sign the Reconciliation
  bill on July 8?" match neither. Unsigned markets are dropped from the panel (`contracts.py:61`).
- **The 8 with a direction never reach USD 50k**: their maximum `vol7d` is USD 13.6k.
- 14 others are neutralised by the stance table (2028 race, removal of the incumbent).

**Volume weighting dampens elections.** Elections are 96% of the volume but 60% of the absolute
contribution. The weights are normalised within each day, and each z score is standardised by the
contract's own volatility. On the many days without a large election market (2025 and early
2026), the shutdown markets are most of the cell and carry its whole change, however small their
volume.

**The largest single contract.** "Will Donald Trump win the 2024 US Presidential Election?" alone
accounts for 24.8% of the cell's absolute contribution.

### B.2 Direction rules by sub-type

Code: `classify.py:381-394`, applied in this order:
1. the party-stance table `data/manual/party_fiscal_stance.csv` (first match on the title, with a
   context pattern on the event text; loaded at `classify.py:503`);
2. date buckets of a shutdown end get no sign;
3. `FISCAL_DOWN` gives -1 (`classify.py:205-207`);
4. `FISCAL_UP` gives +1 (`classify.py:202-204`);
5. otherwise no sign.

**What +1 means.** The convention is spec 4.4: +1 is a more expansionary fiscal outcome or a
higher fiscal risk. Under the monetary-dominance regime (A.6 step 11) a rise in the cell signal is
USD-positive.

Rules within each sub-type (`b2_rules_by_subtype.csv`; titles from `b_us_fiscal_contracts.csv`):

| Sub-type | Rule, sign | What a positive signed change means | Example titles (assigned sign) |
|---|---|---|---|
| elections, presidency 2024 | `stance:us_trump_2024`, +1 (55 contracts, 29.1% of the absolute contribution) | higher odds of a Trump or Republican presidency, read as a larger deficit (CRFB 2024: Trump platform adds more to deficits) | "Will Donald Trump win the 2024 US Presidential Election?" (+1); "Will Donald Trump be inaugurated?" (+1); "Will Donald Trump or another Republican win the Presidency?" (+1) |
| elections, presidency 2024 | `stance:us_harris_2024`, -1 (49 contracts, 4.9%) | the same, measured from the Harris side: lower Harris odds raise the signal | "Will Kamala Harris win the 2024 US Presidential Election?" (-1); "Will Kamala Harris or another Democrat win the Presidency?" (-1); "Kamala Harris wins the popular vote?" (-1) |
| elections, Congress | `stance:us_house_senate_r` +1 (13 contracts, 12.4%) and `stance:us_house_senate_d` -1 (8 contracts, 12.4%) | higher odds of Republican control of a chamber (extension of deficit-financed tax cuts) | "Will Republicans win the House in 2026?" (+1); "Will Democrats win the House in 2026?" (-1); "Will House Control be Republican AND Senate Control be Republican for Feb 2027?" (+1) |
| elections, other | `stance:us_sweep_r` +1, `stance:us_sweep_d` -1, `fiscal:up` +1 (3 drop-out markets) | unified Republican control; candidate drop-out read as political instability | "2024 Balance of Power: R Prez R Senate R House" (+1); "2024 Balance of Power: D Prez, D Senate, D House" (-1); "Will Kamala Harris drop out of presidential race?" (+1) |
| government shutdown | `fiscal:up` +1 (93 contracts, 27.9%); `fiscal:down` -1 (16 contracts, 4.0%) | higher odds or a longer duration of a shutdown, read as higher fiscal risk; funding or an end of the shutdown lowers it | "Will the government be shut down on January 31?" (+1); "Will the federal government shut down for more than 40 days?" (+1); "Will DHS funding bill become law before Apr 1, 2026?" (-1); "Will the Government shutdown end by November 15?" (-1) |
| debt ceiling | `fiscal:down` -1 (1 contract) | lower odds of a debt-limit increase or suspension | "Debt ceiling raised or suspended by inauguration?" (-1) |
| appointments and departures | `fiscal:up` +1 (18 contracts, 4.0%), through `resign` or `\bout\b` in `FISCAL_UP` | higher odds of an official leaving office, read as political instability | "Will Biden announce resignation by July 31?" (+1); "Will Mitch McConnell resign his office early?" (+1); "Will Mike Waltz resign before May 1, 2025?" (+1) |
| other (not US fiscal) | `fiscal:up` +1 (10 contracts, 4.2%) | as above, but these are not US fiscal markets | "Poilievre out as leader of Conservatives in 2025?" (+1); "Will Shigeru Ishiba be the first leader out in 2025?" (+1); "Gianni Infantino out as FIFA President by December 31?" (+1) |

#### Sign of "Trump wins" (2024 presidential election and inauguration markets)

**+1.** The rule is `stance:us_trump_2024` (`party_fiscal_stance.csv`, row `us_trump_2024`). With
the US regime in monetary dominance on every day around the election (`b2_election_window.csv`),
a rise in Trump odds raises $Z_{\text{FIS}}$, lowers $y_t$ and makes A1 **long USD**.

What happened around election day:
- On 2024-11-06, $Z_{\text{FIS}}$ jumped from 0.09 to 2.60.
- A1 flipped from short USD (net -2.03) to long USD (net +1.63) at the 6 November close.
- The jump in the odds happened during the US night of 5 to 6 November, before the 16:00 London
  snapshot of 6 November. A1 was therefore short USD over the dollar's election-day rally:
  -2.6% gross on the return of 6 November.
- It then held long USD into the partial reversal of 7 November: -1.6%.
- This is the timing pattern of the lead-lag test (D26): FX moves first or at the same time.

#### Sign review: questionable signs on reading

These are reported for the validation; no rule was changed (`b2_sign_review.csv`).

1. **Departures carry +1 even where the stance file meant them to be neutral.** The stance file
   neutralises a Biden exit (`us_biden_exit_neutral`, pattern `biden.{0,40}(drop|out|...)`), but
   the titles "Will Biden announce resignation...", "Will Biden resign..." and "Biden resigns from
   presidency..." do not match that pattern. They fall to the generic `FISCAL_UP` (`resign`) rule
   and get +1. The same goes for other resignations and drop-outs.
   - 21 contracts, 5.0% of the absolute contribution.
2. **Not US fiscal markets.** The zone resolver finds no country for these titles, so the
   un-located-market default assigns them to the US (`classify.py:323-327`): Trudeau, Poilievre,
   Ishiba, FIFA, a TV host, a tech product. All carry +1.
   - 10 contracts, 4.2% of the absolute contribution.
3. **Kalshi `POWER` combinations with a Democratic presidency get +1.** The neutral row
   `us_mixed_power_neutral` expects "prez" and does not match the Kalshi wording "Presidency". The
   title contains "Republican", so it falls to `us_trump_2024`. Example: "Will the Democratic
   party win the House, the Republican party win the Senate, and the Democratic party win the
   Presidency?" (+1). Likewise "Will Harris win the Electoral College and Trump win the Popular
   Vote?" gets +1 because "trump" matches first.
   - 3 contracts, below 0.1% of the contribution.
4. **Kalshi wordings of uncertain sign.** "Will the federal government shut down for fewer than
   92 days?" (+1) and "Will federal employees receive back pay after the government shutdown?"
   (+1) have an ambiguous sign. Their weight is negligible.

### B.3 A1 gross P&L: election contracts vs the rest of the cell

**Why there is no additive split.** A1 keeps only the sign of $y_t$ (A.6 step 17), so a split of
the P&L in proportion to the terms of $y_t$ is not meaningful. The shares explode when $y_t$ is
near zero; a first computation gave +261% a year for MONETARY and -251% a year for FISCAL, which
cancel. Two decompositions are reported instead.

#### (i) Leave-one-out counterfactuals

A1 is rebuilt with one component removed and compared with the full A1:
- for the elections, the US fiscal cell is re-aggregated (A.6 steps 7 to 9, same code) from the
  non-election contracts;
- for the rest of the cell, it is re-aggregated from the election contracts only.

(`b3_leave_one_out.csv`, `b3_counterfactuals.csv`; annualised gross mean return)

| Component removed | Period | A1 | A1 without it | Marginal contribution | Gross Sharpe, A1 / without |
|---|---|---|---|---|---|
| Election contracts | 2024-2025 | 9.2% | 12.6% | **-3.4%** | 0.89 / 1.26 |
| Election contracts | 2026 | 9.1% | 8.7% | +0.4% | 0.85 / 0.81 |
| Election contracts | 2024-2026 | 9.2% | 11.5% | **-2.4%** | 0.88 / 1.13 |
| Rest of the fiscal cell | 2024-2025 | 9.2% | 4.0% | +5.3% | 0.89 / 0.38 |
| Rest of the fiscal cell | 2026 | 9.1% | 8.9% | +0.2% | 0.85 / 0.83 |
| Rest of the fiscal cell | 2024-2026 | 9.2% | 5.3% | +3.9% | 0.88 / 0.51 |
| Whole US FISCAL cell | 2024-2026 | 9.2% | 4.2% (MONETARY only) | +5.0% | 0.88 / 0.41 |
| US MONETARY cell | 2024-2026 | 9.2% | 0.7% (FISCAL only) | +8.5% | 0.88 / 0.07 |

Reading:
- **Elections hurt A1** in 2024-2025 (-3.4% a year), and are neutral in 2026.
- **The rest of the cell helped** in 2024-2025 (+5.3% a year). It consists of shutdown and
  departure markets, plus the 4.2% of non-US contracts.
- **Standalone fiscal signals.** The fiscal leg alone loses money in 2026 (gross Sharpe -1.08).
  This holds whichever contracts build it: elections only -0.52, without elections -0.85
  (`b3_counterfactuals.csv`).
- **Caveat.** These are a posteriori decompositions of a frozen rule, not variants. The
  "A1 without elections" figure (gross Sharpe 1.13) must not be read as a better rule: the
  election sub-type was defined after seeing the data.

#### (ii) Decisive term

Each day is classified by which term sets the sign of $y_t$. The A1 gross return of the next day
is summed by class (`b3_decisive_terms.csv`):

| Days on which | 2024-2025: share of days, cumulative gross | 2026: share of days, cumulative gross |
|---|---|---|
| MONETARY and FISCAL agree | 54.5%, +9.4% | 43.5%, -1.1% |
| MONETARY sets the sign against FISCAL | 26.8%, +4.2% | 35.1%, **+7.9%** |
| FISCAL sets the sign against MONETARY | 14.7%, +5.5% | 21.5%, +0.1% |
| y = 0 (before the signals start) | 3.8%, 0 | 0 |

**In 2026, A1's gain comes from days on which the monetary term overrides the fiscal term.**

---

## C. Dollar momentum diagnostic (not a strategy, not a variant)

Definitions:
- **USD basket return**: $b_t = -\frac{1}{9}\sum_i \Delta \ln S_{i,t}$, the dollar against the
  equal-weighted G10 basket, from the New York close of t-1 to the New York close of t.
- **A1 signal**: $u_t = -y_t$ at 16:00 London on t; positive means long USD.

### C.1 Correlations

Pearson correlations (`c1_correlations.csv`):

| Period | n | corr($u_t$, $b_t$) same day | corr(sign $u_t$, $b_t$) | corr($u_t$, $b_{t-1}$) | corr($u_t$, $b_{t-4..t}$) | corr($u_t$, $b_{t+1}$) |
|---|---|---|---|---|---|---|
| 2024-2025 | 523 | 0.096 | 0.065 | 0.116 | 0.210 | 0.039 |
| 2026 | 191 | 0.162 | 0.131 | 0.174 | 0.204 | 0.056 |
| 2024-2026 | 714 | 0.105 | 0.082 | 0.123 | 0.203 | 0.041 |

Reading:
- **Same day.** The same-day correlation is positive but small. The same-day window runs to the
  New York close, after the 16:00 London snapshot.
- **Past returns.** The signal is more correlated with the dollar's past moves (previous day 0.12,
  past five days 0.20) than with its next-day move (0.04), which is what A1 trades. The PM signal
  partly follows dollar news.

### C.2 Momentum benchmarks

Time-series momentum on the dollar basket:
- the forecast is common to all pairs: the sign of the foreign-basket excess return over the past
  1 or 5 days, known at the New York close of t (long USD if the dollar rose);
- it then goes through **A1's construction**: positions $y/\sigma^2$, 10% volatility target,
  caps, no-trade band, execution at the close of t, return on t+1.

Note that momentum uses information up to the New York close, after the 16:00 London snapshot
used by A1. This favours the benchmark.

Results (`c2_benchmarks.csv`):

| Series | 2024-2025 gross Sharpe | 2026 | 2024-2026 | 2024-2026 net Sharpe |
|---|---|---|---|---|
| TSMOM 1-day | -1.12 | -0.87 | -1.05 | -2.46 |
| TSMOM 5-day | -0.80 | +0.16 | -0.54 | -1.13 |
| A1 | 0.89 | 0.85 | 0.88 | 0.43 |
| A1 weekly | 1.08 | 0.69 | 0.97 | 0.75 |

**Dollar momentum lost money** at both horizons over the sample: daily dollar moves mean-reverted.

### C.3 Regressions on the momentum benchmarks

Specification: $r^{A1}_t = \alpha + \beta\, r^{\text{TSMOM}}_t + \varepsilon_t$, daily gross
returns. Errors are Newey-West with lag $\lfloor 4(T/100)^{2/9}\rfloor$ (4 to 6). Alpha is
annualised (x 252). Results are in `c3_regressions.csv`; the last column is the share of days on
which the two USD positions have the same sign.

| Strategy | Benchmark | Period | beta (t) | alpha a year (t) | corr | same USD sign |
|---|---|---|---|---|---|---|
| A1 | TSMOM 1d | 2024-2025 | 0.20 (2.00) | 11.5% (1.93) | 0.20 | 55% |
| A1 | TSMOM 1d | 2026 | -0.19 (-1.45) | 7.3% (0.56) | -0.19 | 52% |
| A1 | TSMOM 1d | 2024-2026 | 0.09 (1.00) | 10.1% (1.78) | 0.09 | 55% |
| A1 | TSMOM 5d | 2024-2025 | 0.21 (2.08) | 10.9% (1.83) | 0.21 | 56% |
| A1 | TSMOM 5d | 2026 | 0.12 (0.74) | 8.9% (0.70) | 0.12 | 58% |
| A1 | TSMOM 5d | 2024-2026 | 0.19 (2.17) | 10.2% (1.83) | 0.18 | 56% |
| A1 weekly | TSMOM 1d | 2024-2025 | 0.10 (0.95) | 12.1% (1.70) | 0.10 | 54% |
| A1 weekly | TSMOM 1d | 2026 | 0.17 (1.12) | 9.0% (0.68) | 0.17 | 55% |
| A1 weekly | TSMOM 1d | 2024-2026 | 0.12 (1.37) | 11.3% (1.80) | 0.12 | 54% |
| A1 weekly | TSMOM 5d | 2024-2025 | 0.09 (0.81) | 11.7% (1.66) | 0.10 | 56% |
| A1 weekly | TSMOM 5d | 2026 | 0.35 (2.68) | 6.8% (0.56) | 0.35 | 59% |
| A1 weekly | TSMOM 5d | 2024-2026 | 0.17 (1.75) | 10.9% (1.77) | 0.17 | 57% |

**Reading.**
- **Loading on momentum.** A1 has a modest positive loading on 5-day dollar momentum: beta 0.19,
  t 2.2 over 2024-2026. The two USD positions agree on 56% of days.
- **Momentum does not explain A1's return.** The benchmark lost money while A1 made money, and
  the alpha (about 10% a year) is close to A1's raw mean.
- **Significance.** The alpha t statistic (about 1.8) is the same as A1's own, so A1's
  performance is not significant at 5% with or without the momentum control.
- **A1 weekly in 2026** loads more on 5-day momentum (beta 0.35, t 2.7).

---

## D. A1 in the Iran war (Feb-Apr 2026) and its worst drawdown

The two windows:
- **Iran war**: the episode of `src/risk/risk.py:16`, 2026-02-26 to 2026-04-10, 32 trading days.
- **Worst drawdown**: peak 2026-03-03, trough 2026-07-30, 108 trading days, not recovered by the
  end of the sample. It is -14.1% net and -11.3% gross, the first row of
  `results/risk/worst_drawdowns.csv` for A1.

Tables: `d1_windows.csv` (summary), `d2_weekly.csv` (weekly path), `d3_largest_moves.csv`,
`d4_index_levels.csv`. Figure: `a1_2026_decomposition.png`.

### D.1 Position, regime and returns over each window

| | Iran war (2026-02-26 to 2026-04-10) | Worst drawdown (2026-03-03 to 2026-07-30) |
|---|---|---|
| A1 return, gross / net | -7.0% / -7.7% | -11.3% / -14.2% |
| Days long USD / short USD | 62.5% / 37.5% | 53.7% / 46.3% |
| Mean net USD position (share of NAV) | +0.38 | +0.07 |
| Sign changes of the USD position | 6 | 23 |
| Days in the fiscal-dominance regime | 0% | 0% |
| Days on which MONETARY and FISCAL have the same sign | 31% | 47% |
| Days on which \|MONETARY\| > \|FISCAL\| | 56% | 46% |
| Counterfactual: A1 with MONETARY only, gross | +3.2% | -1.3% |
| Counterfactual: A1 with FISCAL only, gross | -8.7% | -5.4% |
| A1 gross on days when the terms agree | -2.8% | -3.3% |
| A1 gross on days when MONETARY sets the sign | +0.6% | -3.7% |
| A1 gross on days when FISCAL sets the sign | -5.1% | -5.1% |

### D.2 What drove the signal

**Iran war.** The two terms pointed in opposite directions:
- **US MONETARY**: the index rose by 3.7 over the window (hawkish repricing; mean $Z_{\text{MON}}$
  +0.53), which favours the USD.
- **US FISCAL**: the index fell by 3.0 (mean $Z_{\text{FIS}}$ -0.34), which under monetary
  dominance favours the other currencies. Its largest moves came from the 2026 shutdown markets
  (`d3_largest_moves.csv`):

| Day | Cell change | Main contracts |
|---|---|---|
| 2026-03-20 | -1.97 | "Will DHS funding bill become law before Apr 1, 2026?" (sign -1, z -4.8); "shut down for at least 60 / 90 days between Feb 7 and Dec 31, 2026" (z -5) |
| 2026-03-24 | -3.28 | DHS funding bill before Apr 1 (z -5); shutdown of at least 43 / 45 days (z -4.9 / -5) |
| 2026-03-28 | +4.14 | shutdown of at least 60 / 50 days (z +5 / +4.4); DHS funding bill before Jun 1 (z +5) |
| 2026-04-02 | -1.80 | shutdown of at least 60 / 90 days (z -4.2 / -4.0) |

- **Who set the position.** The monetary term set the sign on 56% of days: A1 was long USD on
  62.5% of days.
- **Where the loss came from.** The 7.0% gross loss came mostly from the days on which the fiscal
  (shutdown) term set the sign (-5.1%). The MONETARY-only counterfactual made +3.2% over the same
  window.
- **No geopolitical input.** A1 has no geopolitical input by construction (D17). The war enters
  A1 only through the US rate and fiscal markets.

**Worst drawdown.** The position whipsawed between two signals close to zero:
- **Sign changes.** The USD position changed sign 23 times in 108 days, each time between about
  +2 and -2 times NAV (figure, middle panel).
- **Two near-zero terms.** The two terms had the same sign on fewer than half of the days, and
  neither dominated: $|Z_{\text{MON}}| > |Z_{\text{FIS}}|$ on 46% of days. The mean $Z$ was +0.31
  (MONETARY) and -0.09 (FISCAL).
- **Costs.** The whipsaw adds costs: net -14.2% against gross -11.3%.
- **Largest US MONETARY moves**, June to July 2026, all on the July FOMC decision partitions
  (Polymarket `fed-decision-in-july-181` and Kalshi `KXFEDDECISION-26JUL`) and on "Fed rate hike
  in 2026?":

| Day | Cell change |
|---|---|
| 2026-06-15 | -2.33 |
| 2026-06-18 | +4.55 (first snapshot after the 16-17 June FOMC meeting) |
| 2026-07-02 | -2.16 |
| 2026-07-08 | +1.68 |
| 2026-07-14 | -4.06 |
| 2026-07-22 | +2.24 |
| 2026-07-28 | +1.56 |

  Over the window the monetary index rose by 9.1 (hawkish), but with large reversals.
- **US FISCAL moves**, May to July, came from the 2026 House and Senate control markets: +3.28 on
  2026-05-08, -2.67 on 2026-06-26, -1.86 on 2026-07-25 ("Will Republicans / Democrats win the
  House in 2026?", "Will the Democratic Party control the House after the 2026 Midterm
  elections?").
- **Losses by class.** The loss is spread over all three classes of days (agree -3.3%, MONETARY
  sets the sign -3.7%, FISCAL sets the sign -5.1%). Both standalone counterfactuals lost money
  too (MONETARY only -1.3%, FISCAL only -5.4%).

### D.3 Summary

- In 2026, the US FISCAL term of A1 is a losing input: gross Sharpe -1.08 on its own. It is mostly
  shutdown markets in February to April and midterm markets from May.
- The US MONETARY term carries A1: gross Sharpe 0.81 on its own in 2026.
- The Iran-war loss and the drawdown come from:
  1. the fiscal term overriding or offsetting the monetary term;
  2. a sign-only rule, which turns small changes in the sum of two near-zero terms into full
     reversals of a roughly 2x NAV dollar position.
- No change follows from this note (frozen scope).
