# Hand-labelling guide: classification validation sample

## Why this exists

Every prediction-market contract used in the project is classified by deterministic rules
(regular expressions, a country resolver and a few lookup tables; no LLM). The rules decide which
contracts enter the theme indices, in which currency zone, and with which sign. If they are
wrong, the signals are wrong.

This sample measures how often the rules are right. It contains 200 markets drawn at random from
events with at least USD 10k of volume, stratified by the theme the rules predicted: 30
MONETARY, 25 INFLATION, 40 FISCAL_POLITICAL, 25 TRADE_TARIFFS, 40 GEOPOLITICS and 40 OTHER. The
OTHER stratum checks for macro contracts the rules missed. Accuracy is reported per field
(theme, zone, direction) in `results/RESULTS.md`. The rules are frozen: the score is reported
as it comes out and nothing is tuned on it.

## Ground rules

- **Blind.** Do not open `validation_key.csv` (the rules' answers) before all 200 lines are done.
- **No LLM, no lookup of the rules' output.** Your own judgement is the reference.
- Use only the title and the event name. When the market is unclear, use your best reading and
  write a note.
- About 1 hour for two people. Take two files each, then go through the doubtful lines together.

## What to fill

Files: `validation_sheet_1.csv` to `validation_sheet_4.csv`, 50 rows each (items 1-50, 51-100,
101-150, 151-200), so that the work can be split between labellers. Fill these four files, not
`validation_sheet.csv` (the scoring step merges the four files when they exist). Do not change any
other column, the row order or the file names. Save as CSV (UTF-8).

| Column | What to write |
|---|---|
| `label_theme` | one theme from the list below |
| `label_zone` | the zone code(s), separated by `\|`; empty if no listed zone applies |
| `label_direction` | `+1`, `-1`, `0` or `B` |
| `notes` | optional: anything doubtful |

When `label_theme` is OTHER, zone and direction are not scored: leave them empty.

## 1. Theme

Ask: through which macro channel could this market move a currency?

| Theme | Covers |
|---|---|
| `MONETARY` | central-bank decisions, the policy-rate path, number of cuts or hikes, central-bank leadership (chair nominations, departures), FOMC dissents |
| `INFLATION` | CPI, PCE, PPI and other price-index prints or ranges, for any country |
| `FISCAL_POLITICAL` | national elections and government composition (head of state or government, control of the national legislature), government collapse, budgets, shutdowns, debt, fiscal laws; social issues are merged here |
| `TRADE_TARIFFS` | tariffs imposed or removed, trade deals, retaliation, sector tariffs |
| `GEOPOLITICS` | wars, strikes, invasions, ceasefires, peace deals, sanctions, shipping disruptions (e.g. Hormuz), nuclear events, regime survival under military pressure |
| `OTHER` | no clear macro channel: sports, entertainment, court cases without a macro stake, sub-national or municipal elections, single-seat primaries, commodity or gas prices, labour data such as jobless claims |

Labour-market data (payrolls, unemployment, jobless claims) has no theme of its own: label it
`OTHER`.

## 2. Zone

Use **only** these codes, in capitals. Order does not matter; the set must be complete.

| Group | Codes |
|---|---|
| G10 zones | `US`, `EA`, `JP`, `UK`, `CH`, `AU`, `NZ`, `CA`, `NO`, `SE` |
| China | `CN` |
| Emerging markets (ISO codes) | `BR` Brazil, `MX` Mexico, `CO` Colombia, `CL` Chile, `PE` Peru, `ZA` South Africa, `TR` Turkey, `PL` Poland, `HU` Hungary, `CZ` Czech Republic, `ID` Indonesia, `IN` India, `KR` South Korea, `TW` Taiwan, `TH` Thailand, `PH` Philippines, `MY` Malaysia |
| Global | `GLOBAL` |

Rules:
- **Euro area countries are `EA`, never their own code.** Germany, France, Italy, Spain, the
  Netherlands, Belgium, Austria, Portugal, Ireland, Finland, Greece, Slovakia, Slovenia,
  Luxembourg, the Baltics, Croatia, Cyprus and Malta are all `EA`. The ECB is `EA`.
- **Countries outside the list have no code** (Russia, Ukraine, Israel, Iran, Venezuela,
  Argentina, Kosovo, Egypt, ...). If no listed zone applies, leave `label_zone` empty.
- **Central-bank markets**: the central bank's zone only (Fed = `US`, Bank of Japan = `JP`,
  Banxico = `MX`, Bank of Korea = `KR`, ...).
- **Macro data with no country named** (CPI, PCE, Fed funds, US-style tickers on these US
  venues): `US`.
- **GEOPOLITICS: always `GLOBAL`**, plus every *directly involved* zone among `US`, `EA`, `JP`,
  `UK`, `CN`, `CA`, `AU`, `NO`, `CH`. Emerging-market zones are not tagged for geopolitics:
  the EM strategy uses the global index. Example: a US strike on a country outside the list is
  `GLOBAL|US`; a war between two countries outside the list is `GLOBAL`.
- **TRADE_TARIFFS**: the markets are about US tariffs, so `US` plus the counterpart zone if one
  is named (e.g. tariffs on Canada: `US|CA`; tariffs on the EU: `US|EA`; a blanket tariff:
  `US`). A trade deal between two non-US countries: their zones only.
- **FISCAL_POLITICAL and INFLATION**: the zone of the country concerned (an election in a euro
  area country is `EA`; an election or inflation print in a country outside the list has no
  code).

## 3. Direction

Does a **higher Yes price** mean a higher value of the theme index?

| Theme | Higher index means |
|---|---|
| MONETARY | more hawkish: higher expected policy rate (a hike, fewer cuts, rate above a threshold) |
| INFLATION | higher expected inflation |
| FISCAL_POLITICAL | more fiscal expansion or more fiscal risk (deficit-raising party wins, larger deficit, government falls, shutdown) |
| TRADE_TARIFFS | more trade restriction (tariff imposed or raised = `+1`; removed, lowered or deal = `-1`) |
| GEOPOLITICS | more escalation (strike, invasion, sanctions imposed = `+1`; ceasefire, peace deal, normalisation = `-1`) |

Values:
- `+1`: Yes moves the index up (e.g. "Fed cuts by 50 bp?" is `-1`; "CPI above 3.0%?" is `+1`).
- `-1`: Yes moves the index down.
- `0`: ambiguous (e.g. an election winner with no clear fiscal stance, a leader leaving with no
  obvious policy consequence).
- `B`: the market is **one bucket of a set of mutually exclusive outcomes**: one decision option
  among several (hike 25 / hold / cut 25 ...), one range ("between 2.9% and 3.1%", "exactly
  0.2%"), one count ("4 cuts in 2026"). A threshold market ("above 3.0%?", "more than 0.1%?")
  is not a bucket: give it `+1` or `-1`.

## When you are done

From the `230gb-pm-fx/` folder:

```
.venv/Scripts/python.exe -m src.pm.validation score
.venv/Scripts/python.exe -c "from src.report import summary_md; summary_md.build()"
```

The first command merges the four files (`validation_sheet_merged.csv`), then writes
`validation_scores.csv` (accuracy for theme, zone and direction) and `validation_merged.csv` (line by
line, to review disagreements). The second puts the scores in
section 1 of `results/RESULTS.md`.
