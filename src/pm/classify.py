"""Deterministic classification of prediction-market contracts (spec 4.2, DECISIONS D1).

For every candidate market we assign
  - theme: MONETARY, INFLATION, FISCAL_POLITICAL, TRADE_TARIFFS, GEOPOLITICS or OTHER
  - zones: list of zone codes (US, EA, JP, UK, CH, AU, NZ, CA, NO, SE, CN, EM ISO codes,
           GLOBAL), with an EA country sub-tag where relevant
  - geo_region (GEOPOLITICS only): MIDEAST, RUSSIA_UKRAINE, CHINA_TAIWAN, ASIA, LATAM,
           OTHER; oil_relevant flag for MIDEAST and RUSSIA_UKRAINE
  - direction: +1 if a higher Yes probability moves the theme index up (sign conventions,
           spec 4.4), -1 if down, 0 if ambiguous (excluded)
  - bucket fields for partition (mutually exclusive) events: `bucket_value` in the
           event's unit (bp change for policy decisions and cut counts, pp for inflation)

Evidence: theme rules on the event text (event slug words, Kalshi series title, market
title), zone from the Kairos geographic resolver `geo_registry.resolve` plus central
bank / institution maps, direction from fixed regex rules on the market title, election
outcomes from `data/manual/party_fiscal_stance.csv`. All rules are written before any
signal or backtest is computed. Every label carries the rule that produced it.

Output: data/processed/contracts_classified.parquet
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from src.common import connect, get_logger, load_config, rpath, sql_path
from src.pm.vendor import geo_registry

log = get_logger("classify")

RULES_VERSION = "rules-v1-2026-10-03"

# --------------------------------------------------------------------------------------
# Zones
# --------------------------------------------------------------------------------------
EA_MEMBERS = {
    "germany": "DE", "france": "FR", "italy": "IT", "spain": "ES", "netherlands": "NL",
    "belgium": "BE", "austria": "AT", "portugal": "PT", "ireland": "IE", "finland": "FI",
    "greece": "GR", "slovakia": "SK", "slovenia": "SI", "luxembourg": "LU", "estonia": "EE",
    "latvia": "LV", "lithuania": "LT", "croatia": "HR", "cyprus": "CY", "malta": "MT",
}
G10_ZONE = {
    "united states": "US", "japan": "JP", "united kingdom": "UK", "switzerland": "CH",
    "australia": "AU", "new zealand": "NZ", "canada": "CA", "norway": "NO", "sweden": "SE",
    "china": "CN",
}
# Emerging markets tracked for Strategy B (ISO codes as zone labels).
EM_ZONE = {
    "brazil": "BR", "mexico": "MX", "colombia": "CO", "chile": "CL", "peru": "PE",
    "south africa": "ZA", "turkey": "TR", "poland": "PL", "hungary": "HU",
    "czech republic": "CZ", "indonesia": "ID", "india": "IN", "south korea": "KR",
    "taiwan": "TW", "thailand": "TH", "philippines": "PH", "malaysia": "MY",
}
EA_TEXT = re.compile(r"(?i)\b(ecb|lagarde|euro ?area|eurozone|european central bank|euro zone)\b")
CB_ZONE = [  # central-bank surface -> zone (checked before the geo resolver for MONETARY)
    (r"\b(fed|fomc|federal reserve|fed funds|powell|warsh|hassett)\b", "US"),
    (r"\b(ecb|lagarde|european central bank)\b", "EA"),
    (r"\b(boj|bank of japan|ueda)\b", "JP"),
    (r"\b(boe|bank of england)\b", "UK"),
    (r"\b(snb|swiss national bank)\b", "CH"),
    (r"\b(rba|reserve bank of australia)\b", "AU"),
    (r"\b(rbnz|reserve bank of new zealand)\b", "NZ"),
    (r"\b(boc|bank of canada)\b", "CA"),
    (r"\b(norges bank)\b", "NO"),
    (r"\b(riksbank)\b", "SE"),
    (r"\b(pboc|people'?s bank of china)\b", "CN"),
    (r"\b(banxico|bank of mexico)\b", "MX"),
    (r"\b(copom|selic|central bank of brazil|brazil central bank)\b", "BR"),
    (r"\b(rbi|reserve bank of india|bank of india)\b", "IN"),
    (r"\b(bank of korea|bok)\b", "KR"),
]
CB_ZONE = [(re.compile("(?i)" + p), z) for p, z in CB_ZONE]
KALSHI_CB_SERIES = {
    "JAPAN": "JP", "ENGLAND": "UK", "EU": "EA", "AUSTRALIA": "AU", "CANADA": "CA",
    "NZ": "NZ", "MEXICO": "MX", "BRAZIL": "BR", "KOREA": "KR", "CHINA": "CN", "INDIA": "IN",
}
REGION = {
    "MIDEAST": {"iran", "israel", "palestine", "lebanon", "syria", "iraq", "yemen",
                "saudi arabia", "united arab emirates", "qatar", "kuwait", "bahrain", "oman",
                "jordan", "egypt"},
    "RUSSIA_UKRAINE": {"russia", "ukraine", "belarus", "moldova"},
    "CHINA_TAIWAN": {"china", "taiwan"},
    "ASIA": {"north korea", "south korea", "japan", "india", "pakistan", "philippines",
             "vietnam"},
    "LATAM": {"venezuela", "cuba", "colombia", "mexico", "panama", "brazil"},
}
MIDEAST_TEXT = re.compile(r"(?i)\b(hormuz|red sea|houthi|hamas|hezbollah|gaza|kharg|fordow|"
                          r"khamenei|netanyahu|west bank)\b")


def zone_of_country(c: str) -> tuple[str | None, str | None]:
    if c in G10_ZONE:
        return G10_ZONE[c], None
    if c in EA_MEMBERS:
        return "EA", EA_MEMBERS[c]
    if c in EM_ZONE:
        return EM_ZONE[c], None
    return None, None


# --------------------------------------------------------------------------------------
# Themes
# --------------------------------------------------------------------------------------
def _c(p: str) -> re.Pattern:
    return re.compile("(?i)" + p)


# Families with no macro channel, or measured outcomes that are not events of our themes.
EXCLUDE = _c(
    r"approval|approve rating|margin of victory|\bmov\b|vote (percentage|share)|% of the vote|"
    r"\bprimary\b|primaries|nominee|nomination|governor|mayor|state senate|attorney general|"
    r"secretary of|cabinet|pardon|executive order|truth social|attend|epstein|nobel|\bpope\b|"
    r"gas price|tsa|layoff|payroll|jobs (number|report)|unemployment|jobless|\bgdp\b|"
    r"recession|truflation|\bwear\b|tweet|\bsay\b|mention|launch a coin|meme|"
    r"\b(house|senate) race\b|district|county|swing state|closest state|deep blue|"
    r"redistricting|referendum margin|electoral college margin|popular vote margin|"
    r"(airfare|apparel|food|shelter|used car|gasoline|tobacco|egg).{0,20}(cpi|price|inflation)|"
    r"(cpi|inflation).{0,20}(airfare|apparel|food|shelter|used car|gasoline|tobacco|egg)"
)
NON_TRADE = _c(r"revenue|dividend|checks?\b|payments? of|fart|audibly|collect|generate")
THEME_RULES = [
    ("TRADE_TARIFFS", _c(r"tariff|trade (deal|war|agreement|talks)|export control|embargo|"
                         r"de minimis|usmca|section (232|301)")),
    ("MONETARY", _c(r"\bfed\b|fomc|federal reserve|fed funds|interest rates?|rate (cut|hike)|"
                    r"(cut|hike|raise|lower)s? (interest )?rates|basis points|\bbps\b|"
                    r"central bank|\becb\b|lagarde|bank of (japan|england|canada|korea|mexico|"
                    r"india|australia|china)|\bboj\b|\bboe\b|\bsnb\b|swiss national bank|"
                    r"riksbank|norges bank|reserve bank|\brba\b|\brbnz\b|banxico|copom|selic|"
                    r"monetary policy|policy rate|cbdecision|ratecut")),
    ("INFLATION", _c(r"\bcpi\b|inflation|\bpce\b|\bppi\b|consumer price")),
    ("GEOPOLITICS", _c(r"\bwar\b|cease-?fire|truce|peace (deal|agreement|talks|treaty|plan)|"
                       r"invade|invasion|military|\bstrikes?\b|airstrike|\bbomb|missile|"
                       r"nuclear|attack|troops|blockade|annex|sanction|hostage|hamas|hezbollah|"
                       r"houthi|gaza|hormuz|red sea|\bnato\b|martial law|\bcoup\b|drone|"
                       r"escalat|airspace|enriched uranium|kharg|fordow|conflict|"
                       r"(us|u\.s\.|israel|iran|russia|ukraine|china|taiwan) x ")),
    ("FISCAL_POLITICAL", _c(r"election|elected|prime minister|chancellor|\bpresident|"
                            r"parliament|dissol|no[- ]confidence|confidence vote|impeach|"
                            r"resign|\bout (as|by|before|in)\b|leav(e|ing) (office|power)|"
                            r"shut ?down|debt (ceiling|limit|brake)|budget|deficit|fiscal|"
                            r"\btax|reconciliation|big beautiful bill|coalition|balance of power|"
                            r"control (of )?the (house|senate)|inaugurated|"
                            r"(house|senate) (winner|control|majority)|"
                            r"pmleave|leavestarmer|government funding|fund the government")),
]
# Kalshi series that pin the theme directly (checked before text rules).
KALSHI_SERIES_THEME = [
    (r"^(KX)?(FED|FEDDECISION|RATECUT|RATECUTCOUNT|FEDHIKE|FEDRATEMIN|FEDFUNDSYEAR|"
     r"FEDCHGCOUNT|FEDMEET)$", "MONETARY"),
    (r"^KXCBDECISION", "MONETARY"),
    (r"^(KX)?(ECB|BOJDECISION)$", "MONETARY"),
    (r"^(KX)?(A?CPI(CORE)?(YOY)?|CPICOREYOY|ECONSTATCPI(YOY|CORE|COREYOY)?|USCPIYEAR|"
     r"[A-Z]{2}CPIYOY[A-Z]*|[A-Z]{2}CPIPREL|CPIEU|EZCPIYOYF|LCPIMAX(YOY)?|LCPIMIN|LCPIYOY|"
     r"PCE|PCECORE|CPICN|CHINACPI|CHCPIYOY|JPMOMINF)$", "INFLATION"),
    (r"TARIFF", "TRADE_TARIFFS"),
    (r"^(KX)?(GOVSHUT|GOVTSHUTDOWN|GOVSHUTLENGTH|GOVTSHUTLENGTH|SHUTDOWNBY|SHUTDOWNBYDATE|"
     r"DEBTLIMITINCREASE|DEBTBRAKE|NUMSHUTDOWNS|GOVTFUND|GOVTFULLFUND|DHSFUND)$",
     "FISCAL_POLITICAL"),
    (r"^(PRES|POPVOTE|CONTROLH|CONTROLS|POWER|PRESPARTYFULL|KXBALANCEPOWERCOMBO|"
     r"KXPRESPARTY|KXCONTROLH|KXCONTROLS)$", "FISCAL_POLITICAL"),
    (r"PMLEAVE$|^KXLEAVESTARMER$|^KX(CANADA|AUS|NORWAY|FRENCH|UK)PM$|^KXCHANCELLOR$|"
     r"^KXJPPMHOC$|^KXNEXTCHANCELLOR$", "FISCAL_POLITICAL"),
    (r"HORMUZ|IRANAGREEMENT|USIRANMOU|^KXUKRAINE$", "GEOPOLITICS"),
]
KALSHI_SERIES_THEME = [(re.compile(p), t) for p, t in KALSHI_SERIES_THEME]

# --------------------------------------------------------------------------------------
# Directions (applied to the market title, after lower-casing)
# --------------------------------------------------------------------------------------
UP_LEVEL = _c(r"\b(above|more than|greater than|at least|exceed|higher than|or (more|higher|"
              r"above)|over \d)|\d\+|≥|>")
DOWN_LEVEL = _c(r"\b(below|less than|under|lower than|or (less|lower|below))\b|≤|<")
BETWEEN = _c(r"between\s*(-?\d+(?:\.\d+)?)%?\s*(?:and|-|to)\s*(-?\d+(?:\.\d+)?)%?|"
             r"(-?\d+(?:\.\d+)?)%?\s*(?:-|to)\s*(-?\d+(?:\.\d+)?)%")
# Exact-value buckets: "annual inflation increase by 2.4%", "upper bound ... be 1.5%".
EXACT_PCT = _c(r"\b(?:increase|rise|be|by|at)\s+(?:by\s+)?(-?\d+(?:\.\d+)?)\s*%")

ENDS_HOSTILITIES = (r"\b(war|conflict|action|operations?|fighting|hostilities|blockade|strikes)\b"
                    r".{0,40}\bends?\b|\bend of (the )?(war|conflict|military|operations?|"
                    r"blockade|fighting|hostilities)|\bends? (the )?(war|conflict|fighting)")
DEESCALATE = _c(r"cease-?fire|truce|peace|agreement|\bdeal\b|negotiat|talks|diplomatic|\bmeet|"
                r"summit|\bsign|returns? to normal|lifted|reopen|withdraw|release|normaliz|"
                r"recogni[sz]e|extend|extension|continues? through|" + ENDS_HOSTILITIES)
ESCALATE = _c(r"strike|attack|invade|invasion|military (action|engagement|operation)|"
              r"forces enter|ground (offensive|operation)|troops|missile|bomb|airstrike|war\b|"
              r"close[sd]? (its |the )?(strait|airspace)|closes|blockade|nuclear (test|weapon)|"
              r"destroy|seize|no longer under|declare war|mobiliz|escalat|sanction|annex|"
              r"martial law|drone")
CEASEFIRE_BREAK = _c(r"(cease-?fire|truce).{0,30}\b(broken|break|breaks|collapse[sd]?|violat\w*|"
                     r"ends?|ended)\b")
TRANSIT_NORMAL = _c(r"(transit|traffic|shipping).{0,120}\b(above|normal)")

TARIFF_UP = _c(r"impose|in effect|take effect|announce|increase|raise|above|more than|at least|"
               r"new tariff|tariffs? on|hike|reciprocal|retaliat|in favou?r of trump|uphold")
TARIFF_DOWN = _c(r"lower|reduce|remove|lift|pause|suspend|end\b|cut|exempt|refund|block|"
                 r"strike down|struck down|illegal|unlawful|invalid|rule against|deal|"
                 r"agreement|below|less than|repeal|roll ?back|undo|disapprove|kill")

FISCAL_UP = _c(r"shut ?down|no[- ]confidence|dissol|snap election|early election|resign|"
               r"\bout\b|leav(e|es|ing)|collapse|fall\b|impeach|default|deficit (above|over|"
               r"more)|tax cut")
FISCAL_DOWN = _c(r"(raise|increase|suspend)s? (the )?debt (ceiling|limit)|debt (ceiling|limit) "
                 r"(raised|increase)|shutdown end|end (the )?shutdown|government (is )?funded|"
                 r"fund(s|ed)? the government|funding bill (pass|become)|budget (pass|approved)")

DECISION_DELTA = [  # (regex on lower title, bp change); first match wins
    (_c(r"(decrease|cut|lower|reduce)s?\w*.{0,40}?(50|75|100)\+? ?(bps|basis)"), None),
    (_c(r"(decrease|cut|lower|reduce)s?\w*.{0,40}?25\+? ?(bps|basis)"), -25),
    (_c(r"(increase|hike|raise)s?\w*.{0,40}?(50|75|100)\+? ?(bps|basis)"), None),
    (_c(r"(increase|hike|raise)s?\w*.{0,40}?25\+? ?(bps|basis)"), 25),
    (_c(r"no change|unchanged|maintain|\bhold\b|keep (interest )?rates|pause"), 0),
]
KALSHI_DECISION_SUFFIX = {"HOLD": 0, "H0": 0, "C25": -25, "C26": -50, "C25P": -50, "C50": -50,
                          "C75": -75, "H25": 25, "H26": 50, "H25P": 50, "H50": 50}
WORD_NUM = {"zero": 0, "no": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
            "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}
CUT_COUNT = _c(r"(?:will )?(\d+|zero|no|one|two|three|four|five|six|seven|eight|nine|ten)\+? "
               r"(?:fed )?(?:rate )?cuts?|cut (?:interest )?rates (\d+|zero|no|one|two|three|"
               r"four|five|six|seven|eight|nine|ten) times?|no fed rate cuts")


def _decision_delta(title: str, platform_id: str, series: str | None) -> float | None:
    if series and (series.startswith("KXCBDECISION") or "FEDDECISION" in series):
        suf = platform_id.rsplit("-", 1)[-1].upper()
        if suf in KALSHI_DECISION_SUFFIX:
            return float(KALSHI_DECISION_SUFFIX[suf])
    t = title.lower()
    for rx, val in DECISION_DELTA:
        m = rx.search(t)
        if m:
            if val is None:
                num = int(re.search(r"(50|75|100)", m.group(0)).group(1))
                sign = -1 if re.search(r"decrease|cut|lower|reduce", m.group(0)) else 1
                return float(sign * num)
            return float(val)
    return None


def _cut_count(title: str) -> float | None:
    t = title.lower()
    if re.search(r"no fed rate cuts|no (rate )?cuts", t):
        return 0.0
    m = CUT_COUNT.search(t)
    if not m:
        return None
    tok = next(g for g in m.groups() if g)
    return float(WORD_NUM.get(tok, tok) if not tok.isdigit() else int(tok))


def _bracket_mid(title: str) -> float | None:
    """Bucket midpoint for 'between X and Y' buckets, or the value of an exact-value bucket."""
    m = BETWEEN.search(title)
    if m:
        a, b = [g for g in m.groups() if g is not None][:2]
        return (float(a) + float(b)) / 2.0
    if UP_LEVEL.search(title) or DOWN_LEVEL.search(title):
        return None
    m = EXACT_PCT.search(title)
    return float(m.group(1)) if m else None


def _level_threshold(title: str) -> float | None:
    m = re.search(r"(-?\d+(?:\.\d+)?)\s*%", title)
    return float(m.group(1)) if m else None


# --------------------------------------------------------------------------------------
# Main classification
# --------------------------------------------------------------------------------------
def _theme(row) -> tuple[str, str]:
    if re.search(r"(?i)tariff", row.text) and NON_TRADE.search(row.text):
        return "OTHER", "exclude:tariff-non-restriction"
    if row.platform == "kalshi" and row.series:
        for rx, th in KALSHI_SERIES_THEME:
            if rx.search(row.series):
                return th, f"series:{row.series}"
    text = row.text
    if re.search(r"(?i)tariff", text) and NON_TRADE.search(text):
        return "OTHER", "exclude:tariff-non-restriction"
    if EXCLUDE.search(text):
        return "OTHER", "exclude:" + EXCLUDE.search(text).group(0)
    for th, rx in THEME_RULES:
        m = rx.search(text)
        if m:
            return th, "text:" + m.group(0)
    return "OTHER", "no-rule"


def _zones(row, theme: str, geo: dict) -> tuple[list[str], str | None, str | None]:
    """Return (zones, ea_country, geo_region)."""
    text = row.text
    zones, ea_sub = [], None
    if theme == "MONETARY":
        if row.platform == "kalshi" and row.series.startswith("KXCBDECISION"):
            z = KALSHI_CB_SERIES.get(row.series.replace("KXCBDECISION", ""))
            return ([z] if z else []), None, None
        for rx, z in CB_ZONE:
            if rx.search(text):
                return [z], None, None
    if EA_TEXT.search(text):
        zones.append("EA")
    for c in geo["countries"]:
        z, sub = zone_of_country(c)
        if z and z not in zones:
            zones.append(z)
        if sub and ea_sub is None:
            ea_sub = sub
    if theme == "GEOPOLITICS":
        cs = set(geo["countries"])
        region = None
        for r, members in REGION.items():
            if cs & members:
                region = r
                break
        if region is None and MIDEAST_TEXT.search(text):
            region = "MIDEAST"
        # Conflicts are global risk events; G10/CN zones keep their own tag as well.
        zones = [z for z in zones if z in {"US", "EA", "JP", "UK", "CN", "CA", "AU", "NO", "CH"}]
        return ["GLOBAL"] + [z for z in zones if z != "GLOBAL"], ea_sub, region or "OTHER"
    # Un-located macro markets on these US-centric venues are US markets ("U.S." is not
    # matched by the resolver). Only applied when no country at all was resolved.
    if not zones and not geo["countries"] and theme in {"MONETARY", "INFLATION",
                                                         "FISCAL_POLITICAL", "TRADE_TARIFFS"}:
        zones = ["US"]
    if theme == "TRADE_TARIFFS" and "US" not in zones:
        # 2024-2026 tariff markets are about US tariffs (imposed by or on the US).
        zones = ["US"] + zones
    return zones, ea_sub, None


def _direction(row, theme: str, stance: pd.DataFrame) -> tuple[int, str]:
    t = row.title.lower() if isinstance(row.title, str) else ""
    if theme == "MONETARY":
        if re.search(r"chair|nominat|confirm|governor|leav|fire|dissent|wikipedia|emergency meeting|"
                     r"\bqt\b|balance sheet|\bout\b", t):
            return 0, "monetary:personnel-or-meta"
        if re.search(r"\b(cut|decrease|lower|reduce|ease)", t):
            return -1, "monetary:cut"
        if re.search(r"\b(hike|increase|raise|tighten)", t):
            return 1, "monetary:hike"
        if UP_LEVEL.search(t):
            return 1, "monetary:rate-above"
        if DOWN_LEVEL.search(t):
            return -1, "monetary:rate-below"
        return 0, "monetary:none"
    if theme == "INFLATION":
        if not re.search(r"\d", t):
            return 0, "inflation:no-level"
        if BETWEEN.search(t) or (EXACT_PCT.search(t) and not UP_LEVEL.search(t)
                                 and not DOWN_LEVEL.search(t)):
            return 0, "inflation:bucket"
        if DOWN_LEVEL.search(t):
            return -1, "inflation:below"
        if UP_LEVEL.search(t):
            return 1, "inflation:above"
        return 0, "inflation:none"
    if theme == "TRADE_TARIFFS":
        if BETWEEN.search(t):
            return 0, "tariff:bucket"
        if TARIFF_DOWN.search(t):
            return -1, "tariff:down:" + TARIFF_DOWN.search(t).group(0)
        if TARIFF_UP.search(t) or re.search(r"tariff", t):
            return 1, "tariff:up"
        return 0, "tariff:none"
    if theme == "GEOPOLITICS":
        if CEASEFIRE_BREAK.search(t):
            return 1, "geo:ceasefire-break"
        if re.search(r"\bout\b|regime fall|leadership change|successor|head of state|"
                     r"supreme leader|in power", t):
            return 0, "geo:leadership"
        if TRANSIT_NORMAL.search(t):
            return -1, "geo:transit-normal"
        if DEESCALATE.search(t):
            return -1, "geo:deescalate:" + DEESCALATE.search(t).group(0)
        if ESCALATE.search(t):
            return 1, "geo:escalate:" + ESCALATE.search(t).group(0)
        return 0, "geo:none"
    if theme == "FISCAL_POLITICAL":
        for r in stance.itertuples():
            if re.search(r.pattern, t, flags=re.I) and re.search(r.context, row.text, flags=re.I):
                return int(r.sign), f"stance:{r.label}"
        # Date buckets of a shutdown end ("end October 19-22") carry no clear sign.
        if re.search(r"shutdown end (on )?(january|february|march|april|may|june|july|august|"
                     r"september|october|november|december)", t):
            return 0, "fiscal:end-date-bucket"
        if FISCAL_DOWN.search(t):
            return -1, "fiscal:down"
        if FISCAL_UP.search(t):
            return 1, "fiscal:up"
        return 0, "fiscal:none"
    return 0, "other"


def classify(markets: pd.DataFrame, stance: pd.DataFrame,
             geo_cache: dict | None = None) -> pd.DataFrame:
    df = markets.copy()
    for col in ("series", "series_title", "event_text", "title", "event_key"):
        df[col] = df[col].fillna("").astype(str)
    df["text"] = df["event_text"] + " | " + df["series_title"] + " | " + df["title"]
    out = []
    geo_cache = {} if geo_cache is None else geo_cache
    for row in df.itertuples(index=False):
        theme, theme_rule = _theme(row)
        if theme == "OTHER":
            zones, ea_sub, region = [], None, None
            direction, dir_rule = 0, "other"
        else:
            # Resolved per market: in multi-country events the country varies by market.
            key = (row.event_text, row.title)
            if key not in geo_cache:
                geo_cache[key] = geo_registry.resolve(row.event_text, row.title, [])
            zones, ea_sub, region = _zones(row, theme, geo_cache[key])
            direction, dir_rule = _direction(row, theme, stance)
        dec = _decision_delta(row.title, row.platform_id, row.series) if theme == "MONETARY" else None
        cuts = _cut_count(row.title) if theme == "MONETARY" and dec is None else None
        level = None
        if theme == "MONETARY" and dec is None and cuts is None and not UP_LEVEL.search(row.title) \
                and not DOWN_LEVEL.search(row.title):
            m = EXACT_PCT.search(row.title)
            level = float(m.group(1)) * 100.0 if m else None   # policy-rate level bucket, bp
        mid = _bracket_mid(row.title) if theme in {"INFLATION", "TRADE_TARIFFS"} else None
        out.append(dict(
            platform=row.platform, platform_id=row.platform_id, event_key=row.event_key,
            theme=theme, theme_rule=theme_rule, zones=zones, ea_country=ea_sub,
            geo_region=region, oil_relevant=region in {"MIDEAST", "RUSSIA_UKRAINE"},
            direction=direction, direction_rule=dir_rule,
            decision_bp=dec, cut_count=cuts, rate_level_bp=level, bracket_mid=mid,
            level_threshold=(_level_threshold(row.title)
                             if theme in {"INFLATION", "TRADE_TARIFFS"} else None),
        ))
    lab = pd.DataFrame(out)
    lab = _mark_partitions(lab)
    lab["rules_version"] = RULES_VERSION
    return lab


def _mark_partitions(lab: pd.DataFrame) -> pd.DataFrame:
    """Flag mutually exclusive bucket events and set a common unit per bucket.

    MONETARY decision events: >= 2 markets with a parsed bp change and >= 2 distinct
    values -> unit 'bp', bucket_value = bp change. Cut-count events: >= 2 markets with
    distinct counts -> unit 'bp', bucket_value = -25 x count. Policy-rate level buckets
    -> unit 'bp', bucket_value = level. INFLATION and TRADE_TARIFFS brackets: >= 2
    bucket markets -> unit 'pp' (inflation) or 'pct' (tariff rate), bucket_value = bucket
    midpoint; open-ended above/below buckets get threshold +/- half the median width.
    """
    lab["partition"] = False
    lab["unit"] = None
    lab["bucket_value"] = np.nan

    def _set(index, unit, values):
        lab.loc[index, "partition"] = True
        lab.loc[index, "unit"] = unit
        lab.loc[index, "bucket_value"] = values

    for _, g in lab.groupby("event_key", sort=False):
        th = g["theme"].iloc[0]
        if th == "MONETARY":
            dec = g["decision_bp"].dropna()
            cuts = g["cut_count"].dropna()
            lvl = g["rate_level_bp"].dropna()
            if len(dec) >= 2 and dec.nunique() >= 2:
                _set(dec.index, "bp", dec)
            elif len(cuts) >= 2 and cuts.nunique() >= 2:
                _set(cuts.index, "bp", -25.0 * cuts)
            elif len(lvl) >= 2 and lvl.nunique() >= 2:
                _set(lvl.index, "bp", lvl)
        elif th in {"INFLATION", "TRADE_TARIFFS"}:
            mids = g["bracket_mid"].dropna()
            if len(mids) >= 2 and mids.nunique() >= 2:
                unit = "pp" if th == "INFLATION" else "pct"
                width = float(np.median(np.diff(np.sort(mids.unique()))))
                _set(mids.index, unit, mids)
                for i in g.index.difference(mids.index):
                    thr = lab.at[i, "level_threshold"]
                    if thr is None or pd.isna(thr):
                        continue
                    if lab.at[i, "direction"] == 1:
                        _set([i], unit, thr + width / 2)
                    elif lab.at[i, "direction"] == -1:
                        _set([i], unit, thr - width / 2)
    # Within a partition the bucket value carries the sign; the per-market direction is not used.
    lab.loc[lab["partition"], "direction"] = 0
    lab.loc[lab["partition"], "direction_rule"] = "partition-bucket"
    return lab


def build(cfg: dict | None = None) -> pd.DataFrame:
    cfg = cfg or load_config()
    proc, manual = rpath("processed", cfg), rpath("manual", cfg)
    con = connect()
    markets = con.execute(f"""
        SELECT m.platform, m.platform_id, m.event_key, m.series, m.series_title, m.event_text,
               m.title, m.created_at, m.closes_at, m.resolves_at, m.resolution_resolved_at,
               m.winning_outcome
        FROM read_parquet('{sql_path(proc / "pm_markets.parquet")}') m
        WHERE (m.platform, m.platform_id) IN (
            SELECT DISTINCT platform, platform_id FROM read_parquet('{sql_path(proc / "pm_daily.parquet")}'))
    """).df()
    stance = pd.read_csv(manual / "party_fiscal_stance.csv", comment="#")
    log.info("classifying %d traded candidate markets", len(markets))
    cache_path = proc / "geo_cache.pkl"
    geo_cache = pd.read_pickle(cache_path) if cache_path.exists() else {}
    lab = classify(markets, stance, geo_cache)
    pd.to_pickle(geo_cache, cache_path)
    lab = markets[["platform", "platform_id", "title", "created_at", "closes_at", "resolves_at",
                   "resolution_resolved_at", "winning_outcome"]].merge(lab, on=["platform", "platform_id"])
    lab.to_parquet(proc / "contracts_classified.parquet", index=False)
    summary = (lab.assign(signed=(lab["direction"] != 0) | lab["partition"])
               .groupby("theme").agg(markets=("platform_id", "size"),
                                     events=("event_key", "nunique"),
                                     usable=("signed", "sum")))
    log.info("classification summary:\n%s", summary)
    return lab


if __name__ == "__main__":
    build()
