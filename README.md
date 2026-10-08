# Prediction-market signals for global FX strategies (MFE 230GB, Fall 2026)

Replication package for the final project of MFE 230GB (Currency Markets).

**Presentation (October 8, 2026): [open the slides](https://raw.githack.com/Romain-Alm/230gb-pm-fx/main/presentation/index.html)**.
Arrow keys or space to move, `N` for speaker notes, `F` for full screen. Source:
`presentation/index.html`; its numbers are read from `results/` and checked by
`python3 presentation/build_piero_slides.py`.

We build continuous macro theme indices from Polymarket and Kalshi contracts (monetary policy,
inflation, fiscal and political outcomes, trade and tariffs, geopolitics) and use them in two
strategies:

- **Strategy A (G10).** Only US cells pass the coverage rule (DECISIONS D13), so the primary rule
  (A1) is a dollar signal: US MONETARY and US FISCAL news, with theory-given signs and a
  regime-dependent fiscal sign (D2, D15), drive a G10 basket against USD. Variants A2 and A3 and
  the "+S" spillover versions are pre-declared (D14, D17).
- **Strategy B (EM).** An EM carry portfolio (1-month forwards and NDFs; de facto floating
  currencies from the Ilzetzki-Reinhart-Rogoff classification, D23) with a prediction-market
  geopolitical overlay that cuts exposure on escalation and confirmed shocks. Benchmarked against
  the same rule driven by VIX.

Where to read the results:
- `results/RESULTS.md`: every number, with a reading guide, the status of each result
  (pre-registered or a posteriori) and the caveats. Generated from the result files.
- `DECISIONS.md`: every choice not fixed by `PROJECT_SPEC.md`, dated, logged before the backtest it
  affects (D1 to D31, then the final freeze).
- `notebooks/01_prediction_market_layer.ipynb`, `notebooks/02_strategies_tests_results.ipynb`
  : step-by-step walk-through, executed.
- `results/figures/` (analysis figures), `results/figures/slides/` (presentation figures),
  `results/site_data/` (every table and series for the web page, with its own README).

## Environment

- Python **3.13.13** (Windows 10/Server 2025; any OS should work, paths are relative).
- Exact package versions: `requirements.txt` (pinned from the working environment).

```
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt     # Linux/macOS: .venv/bin/python
.venv/Scripts/python.exe -m pytest tests                        # 58 tests (spec 12); 34 are skipped without the confidential inputs
```

## Reproduce: one command

**Confidential inputs.** Part of the data and code is confidential and not in this repository
(next section): the prediction-market data and the panels derived from them, and the
classification code of the Kairos project. With this repository alone, the `pm` stage cannot run
and the stages after it have no prediction-market input; every output of the full run is in
`results/`. With the data and code in place:

```
.venv/Scripts/python.exe run_all.py
```

This runs every stage in order: `pm` (prediction-market layer), `strategies`, `robustness`, `risk`,
`figures` (figures, slide figures, `site_data/`, `RESULTS.md`). Each stage can be run alone with
`--stage <name>`; `--skip-metadata` reuses the market-metadata scan. All parameters are in
`config/config.yaml` (fixed seed 230, relative paths).

Expected runtime on the project machine (shared server):

| Stage | Runtime |
|---|---|
| `pm` | about 25 minutes (12 for the one-time metadata scan) |
| `strategies` | about 1 minute |
| `robustness` | about 25 minutes (100 placebo draws per test) |
| `risk` | about 1 minute |
| `figures` | about 1 minute |
| **Total** | **about 55 minutes** |

The notebooks are rebuilt and executed with `.venv/Scripts/python.exe notebooks/build_notebooks.py`.
The hand-labelled classification check is scored with `python -m src.pm.validation score`
(guide: `ai_log/classification/LABELLING_GUIDE.md`).

## Data

**Some data are confidential and cannot be shared.** Licensed and confidential inputs are not in
this repository:
- the prediction-market data (Probalytics, accessed through the Kairos industry project, a
  separate project of the team; using other projects is allowed by the assignment) and every
  panel derived from them at contract level (`data/processed/`, not versioned);
- the licensed market data (Bloomberg, WRDS) and the downloaded public data (`data/raw/`, not
  versioned).

What is shared: the code of this project, the hand-coded inputs (`data/manual/`), and every result
(`results/`, including the aggregated theme indices and the geopolitical signals in
`results/site_data/`).

| Data | Used for | Source and access |
|---|---|---|
| Prediction markets (trades, market metadata), 2024-01-01 to 2026-09-24 | all signals | Probalytics archive and live export (licensed, see below) |
| FX spot, 1M forwards and NDFs, MSCI World TR, S&P 500 TR, DXY, Brent | returns, carry, costs, risk | Bloomberg terminal (licensed) |
| VIX | VIX benchmark, risk | Cboe via WRDS (licensed) or public Cboe history |
| 10-year government yields (US, DE, UK, JP) | fiscal regime indicator (D15) | official public sources |
| Hourly FX candles | weekend gap test (D24), lead-lag (D26) | Dukascopy (public) |
| De facto exchange-rate regimes | Strategy B universe (D23) | Ilzetzki, Reinhart and Rogoff (public) |
| FRED, ECB reference rates | preliminary run on free data only (D22) | public |
| Hand-coded inputs | party fiscal stances, debt table, EM screen | `data/manual/` (sources in each file) |

### Prediction markets (Probalytics)

- The pipeline reads the Probalytics trades tape and market metadata from the Kairos data estate
  (`KAIROS_DATA_ROOT`, default `D:/haas-mfe-g9-cg/kairos-data`; paths in `config/config.yaml`,
  schemas in `data/SCHEMA.md`). Access is read-only.
- The data are confidential: licensed to the Kairos industry project, they cannot be shared or
  redistributed, nor can the contract-level panels built from them.
- **Fallback without Probalytics**: the same trades can be collected from the venues' public APIs
  and written in the schema of `data/SCHEMA.md`:
  - Kalshi: `https://api.elections.kalshi.com/trade-api/v2` (endpoints `/markets` and
    `/markets/trades`);
  - Polymarket: Gamma API `https://gamma-api.polymarket.com` (markets and events) and Data API
    `https://data-api.polymarket.com/trades` (trades).
  Coverage and timestamps of a fresh pull may differ slightly from the archive.

### Bloomberg

BDH with default options (daily, no fill), fields `PX_BID`, `PX_ASK`, `PX_LAST`, from 2010-01-01
(EM and risk series) or 2023-06-01 (G10) to the latest date.

| Block | Tickers |
|---|---|
| G10 spot | `EURUSD`, `GBPUSD`, `AUDUSD`, `NZDUSD`, `USDJPY`, `USDCHF`, `USDCAD`, `USDNOK`, `USDSEK` (`Curncy`) |
| G10 1M forward points | `EUR1M`, `GBP1M`, `AUD1M`, `NZD1M`, `JPY1M`, `CHF1M`, `CAD1M`, `NOK1M`, `SEK1M` (`Curncy`) |
| EM spot | `USDBRL`, `USDMXN`, `USDCOP`, `USDCLP`, `USDPEN`, `USDZAR`, `USDTRY`, `USDPLN`, `USDHUF`, `USDCZK`, `USDIDR`, `USDINR`, `USDKRW`, `USDTWD`, `USDTHB`, `USDPHP`, `USDMYR`, `USDCNH` (`Curncy`) |
| EM deliverable 1M points | `MXN1M`, `ZAR1M`, `TRY1M`, `PLN1M`, `HUF1M`, `CZK1M`, `THB1M`, `CNH1M` (`Curncy`) |
| EM NDF 1M points | `BCN1M` (BRL), `CLN1M` (COP), `CHN1M` (CLP), `PSN1M` (PEN), `IHN1M` (IDR), `IRN1M` (INR), `KWN1M` (KRW), `NTN1M` (TWD), `PPN1M` (PHP), `MRN1M` (MYR) (`Curncy`) |
| Risk | `CO1 Comdty`, `NDDUWI Index`, `SPXT Index`, `DXY Index` |

- Forward tickers return **points**. Outright = spot + points / scale, bid with bid and ask with
  ask. Scales: 1 for KRW, IDR, PHP, TWD, COP, CLP; 100 for JPY, HUF, THB, INR; 1,000 for CZK;
  10,000 for all others.
- The loader reads a long file `date, ticker, field, value` in `data/raw/market/`, with the
  ticker names of `config/market_series.yaml` (e.g. `EURUSD` with fields `bid`, `ask`, `last`;
  `EURUSD_1M_FWD` with outright `bid`, `ask`). An optional QC file in `data/raw/market_qc/` lists
  observations removed before use (D28). The data team's delivery README, with the exact build,
  checks and close times, is kept with the raw data.
- No series is a 16:00 London fix: close times and the execution lag they imply are in D28.

### Other sources

| Source | Series | Access |
|---|---|---|
| Cboe VIX | daily close | WRDS `cboe.cboe` (column `vix`), or the public history at `https://www.cboe.com/tradable_products/vix/vix_historical_data/` |
| US Treasury | Daily Treasury Par Yield Curve Rates, 10 Yr | `https://home.treasury.gov/resource-center/data-chart-center/interest-rates` |
| Deutsche Bundesbank | Svensson zero-coupon 10Y, series `BBSIS.D.I.ZST.ZI.EUR.S1311.B.A604.R10XX.R.A.A._Z._Z.A` | `https://www.bundesbank.de/en/statistics/time-series-databases` |
| Bank of England | 10-year nominal par yield, series `IUDMNPY` | `https://www.bankofengland.co.uk/boeapps/database/` |
| Ministry of Finance Japan | JGB constant-maturity yield, 10Y (`jgbcme`) | `https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate/index.htm` |
| Dukascopy | hourly bid/ask candles, G10 and deliverable EM | public; `.venv/Scripts/python.exe -m src.data.download_free duka` writes `data/raw/intraday/` (resumable cache) |
| Ilzetzki-Reinhart-Rogoff | `ERA_Classification_Monthly_1940-2019.xlsx` | `https://www.ilzetzki.com/irr-data`; put in `data/raw/irr/`; the coded screen is `data/manual/em_exclusions.csv` |
| FRED (preliminary run only) | VIX, Brent, US 10Y, dollar index, S&P 500, OECD rates | `python -m src.data.download_free fred`; use your own API key in the git-ignored `config/secrets.local.yaml` (`fred_api_key: <key>`); without a key the public CSV endpoint is used |
| ECB (preliminary run only) | euro reference rates | `python -m src.data.download_free ecb` |

The preliminary run on free data (D22) is `run_preliminary_free.py`; its results are in
`results/preliminary_free/` and are superseded by `results/`.

## Code from another project (Kairos, not included)

The contract classification uses the geographic entity resolver of the Kairos project, a separate
project of the team (using other projects is allowed by the assignment). This code is confidential
and **not included**: it is expected in `src/pm/vendor/` (`geo_registry.py`, `people_generated.py`),
which is not versioned. It is rule-based and calls no LLM or network service. Without it,
`src/pm/classify.py` cannot be imported: the classification tests are skipped and the `pm` stage
cannot run; the tests that need the processed panels are skipped too.

## Repository

```
config/            config.yaml (all parameters), market_series.yaml (raw-data mapping)
data/              SCHEMA.md; manual/ hand-coded inputs; processed/ and raw/ confidential or licensed (not included)
src/data/          prediction-market metadata and daily panel; market-data loader; free-data downloads
src/pm/            classification (rules), contract panel, coverage, theme indices, shocks, weekend
                   changes, hourly indices, validation (vendor/: Kairos code, not included)
src/strategies/    strategy_a.py, strategy_b.py, run_a.py, run_b.py, diagnostics.py, weekend_test.py,
                   leadlag.py, d30_checks.py
src/backtest/      engine (timing, volatility target, caps, no-trade band, costs), metrics, robustness
src/risk/          betas, downside beta, episodes, conditional performance, liquidity, concentration,
                   A vs B, leverage
src/report/        figures, slide figures, site data, RESULTS.md generator
tests/             spec 12 tests (look-ahead, DST, causal inclusion, bracket EV, hazard, timing, costs)
notebooks/         two executed walk-through notebooks and their builder
results/           tables, figures, RESULTS.md (generated)
ai_log/            AI use and the classification validation
progress/          progress notes, plan and data request
```

## Main conventions

- **Snapshot**: 16:00 London. A prediction-market value at t is the last trade strictly before
  the snapshot. Stored timestamps are UTC; DST is handled per date.
- **Execution**: FX prices are Bloomberg closes. A signal of day t trades at the New York close
  of t (G10, Latin America); at the Asian close of t+1 for Asian currencies (KRW in B) (D28).
- **FX excess return**: `rx(t+1) = s(t+1) - s(t) + carry(t)/252`, with `s` the log USD price of
  the currency and `carry = (s - f) x 12` from the 1-month forward or NDF.
- **Signals are causal**: volatilities, z-scores and filters use data up to t-1, or up to t where
  the spec says so.
- **Costs**: half the delivered 1-month forward bid/ask spread (causal 20-day median), doubled
  when VIX is above its expanding 90th percentile in B; sensitivity 0.5x to 3x.
- **Options and leverage**: no options. Leverage comes only from the 10% volatility target.
  Strategy A caps gross exposure at 3x capital and any pair at 30% of gross; Strategy B has no
  cap in its rule. Realised exposures and how often the caps bind are in `RESULTS.md`
  (sections 4 and 5) and `results/risk/leverage.csv`.

## AI use

- **Code**: written with Claude Code (Anthropic) in the project folder, reviewed by the team.
  What was generated, file by file and phase by phase, with the decisions it relates to:
  `ai_log/code_generation.md`.
- **No LLM is called by the pipeline**: contract classification is rule-based (D1) and checked
  against a hand-labelled random sample (`ai_log/classification/`).
- **Design and review conversations** held outside Claude Code (date, purpose, decisions they led
  to): `ai_log/design_conversations.md`.
