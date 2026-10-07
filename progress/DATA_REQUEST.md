# Market data request: currencies, forwards and risk series (Bloomberg)

**Needed by:** today, Saturday 3 October 2026 (results are presented on Thursday 8 October)

## Purpose

The project tests two currency trading strategies that use prediction-market data (Polymarket, Kalshi) as signals:
- one strategy trades the major currencies against the US dollar;
- the other trades a basket of emerging-market currencies.

The prediction-market data is already available. The missing piece is market prices, ideally from a Bloomberg terminal: daily spot and 1-month forward rates for the currencies, 10-year government bond yields, and a few standard risk series.

All requested series are daily. Nothing intraday is needed.

## Date range

| | Start | End |
|---|---|---|
| **Minimum (required)** | 1 June 2023 | latest available, at least 24 September 2026 |
| **Recommended** | 1 January 2010 for the emerging currencies (spot and forwards) and the risk series; 1 June 2023 for everything else | latest available |

- **Why 1 June 2023:** the signals start on 1 January 2024. The extra six months are used to estimate volatilities and correlations before the first signal.
- **Why 2010 for emerging markets and risk series:** the longer history documents the crash risk of the emerging-market carry portfolio, which is the starting point of the second strategy.

## Series to pull

**Priority 1** is required for the results. **Priority 2** improves them but is optional.

| Priority | Block | Instruments | Fields | Start date |
|---|---|---|---|---|
| 1 | Major currencies, spot | EUR, JPY, GBP, CHF, AUD, NZD, CAD, NOK, SEK against USD | bid, ask, last | 1 Jun 2023 |
| 1 | Major currencies, 1-month forward | same nine currencies | forward points (or outright), bid, ask | 1 Jun 2023 |
| 1 | Emerging currencies, spot | BRL, MXN, COP, CLP, PEN, ZAR, TRY, PLN, HUF, CZK, IDR, INR, KRW, TWD, THB, PHP, MYR, CNH against USD | bid, ask, last | 1 Jan 2010 (1 Jun 2023 if 2010 is not practical) |
| 1 | Emerging currencies, 1-month forward | same 18 currencies: **non-deliverable forwards (NDF)** for BRL, COP, CLP, PEN, IDR, INR, KRW, TWD, PHP, MYR; deliverable forwards for the others | outright or points, bid, ask | same as the spot |
| 1 | 10-year government yields | United States, Germany, United Kingdom, Japan | last | 1 Jun 2023 |
| 1 | Risk series | VIX, Brent front-month future, MSCI World total return, S&P 500 total return, dollar index (DXY or Bloomberg Dollar Spot Index) | last | 1 Jan 2010 |
| 2 | 10-year government yields | France, Italy | last | 1 Jun 2023 |
| 2 | Carry indices | any standard G10 or EM FX carry index available on the terminal | last | 1 Jan 2010 |
| 2 | NDF fixings | BRL PTAX, RBI reference rate (INR), KRW and TWD onshore fixings, JISDOR (IDR) | last | same as the EM spot |

### Suggested tickers

These are suggestions; any correct terminal equivalent is fine.
- **Spot**: `EURUSD Curncy`, `USDJPY Curncy`, `USDBRL Curncy`, and so on.
- **Deliverable forward points**: `EUR1M Curncy`, `JPY1M Curncy`, `MXN1M Curncy`, and so on.
- **NDF outrights**: `BCN1M Curncy` (BRL), `IRN1M Curncy` (INR), `KWN1M Curncy` (KRW), `NTN1M Curncy` (TWD), `IHN1M Curncy` (IDR), `CHN1M Curncy` (CLP), `CLN1M Curncy` (COP), `PSN1M Curncy` (PEN), `PPN1M Curncy` (PHP), `MRN1M Curncy` (MYR).
- **Yields**: `USGG10YR Index`, `GDBR10 Index`, `GUKG10 Index`, `GJGB10 Index`.
- **Risk**: `VIX Index`, `CO1 Comdty`, `NDDUWI Index`, `SPXT Index`, `DXY Index`.

## Time of day (important)

The signals are measured at **16:00 London**.
- **Preferred:** 16:00 London fixing series for spot and forwards (Bloomberg BFIX, or the WM/Reuters 4pm fix), if available.
- **Otherwise:** the standard daily close (`PX_LAST`) is fine, provided **the closing time used is stated**.
- **Yields:** 10-year yields should ideally be taken at the same time of day as the currencies.

## Format and delivery

- **Accepted formats:**
  - an Excel workbook with BDH outputs, one sheet per block;
  - a CSV with four columns: `date, ticker, field, value`.
- **Example formula:** `=BDH("EURUSD Curncy","PX_BID,PX_ASK,PX_LAST","2023-06-01","2026-09-30")`.
- **Missing values:** holidays and missing days should be left empty, not filled with previous values, so that gaps stay visible.
- **Delivery:** send the file to Romain Almeida, or place it in the project folder `230gb-pm-fx/data/raw/market/`.
- **Licensing:** the data is used only for this course project and is not redistributed; the replication package documents how to obtain it.

Questions about tickers or fields can go to Romain Almeida.
