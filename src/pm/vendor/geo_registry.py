# Vendored copy (unchanged below this header) of D:/haas-mfe-g9-cg/Kairos_Project/Arb/Cross_Venue/geo_registry.py
# Copied 2026-10-03, source sha1 prefix bc1cde168545. Kept verbatim for reproducibility.
# =============================================================================
# kairos_geo_registry.py
#
# Unified, venue-agnostic geo/entity registry + deterministic resolver.
# Replaces the 5 overlapping tables of taxonomy5 AND absorbs the richer
# geopolitics dictionary. Gazetteer-first (no spaCy): the corpus recon proved
# the non-templated long tail is 0.4% and entirely known entities.
#
# CANONICAL RULE (single, frozen): canonical = lowercase English common name
# ("united states", "united kingdom", "south korea"). Every short code,
# demonym, city, abbreviation, periphrase resolves TO a canonical via ALIAS.
# This is the cross-venue join key; determinism is non-negotiable.
#
# Layers:
#   COUNTRIES     base ISO layer  (canonical -> meta: iso2, counts_specific)
#   ALIAS         surface -> canonical  (codes, abbreviations, demonyms)
#   CITY          city/region surface -> (country, city_label, subdivision?)
#   US_STATES     state name/abbrev -> canonical state (subdivision)
#   CHOKEPOINTS   strait/canal -> country (+ geopolitics booster)
#   ORGS          multilateral orgs (org signal for politics-vs-geo)
#   SEAS_REGIONS  maritime/land regions -> optional country, generic signal
#   PEOPLE        person -> {country, domain}
#   INSTITUTIONS  institution -> {country, domain}
#   PERIPHRASE    "white house" -> country
# =============================================================================

import re

# -----------------------------------------------------------------------------
# 0. COUNTRIES — base ISO layer. canonical (lowercase common name) -> meta.
#    counts_specific=False for supranational/region pseudo-entities so they
#    never trigger the ">=2 specific countries => geopolitics" rule.
# -----------------------------------------------------------------------------
_ISO = """
us united states|gb united kingdom|fr france|de germany|it italy|es spain|
pt portugal|ie ireland|nl netherlands|be belgium|lu luxembourg|ch switzerland|
at austria|se sweden|no norway|dk denmark|fi finland|is iceland|pl poland|
cz czech republic|sk slovakia|hu hungary|ro romania|bg bulgaria|gr greece|
hr croatia|si slovenia|rs serbia|ba bosnia and herzegovina|me montenegro|
mk north macedonia|al albania|xk kosovo|md moldova|ua ukraine|by belarus|
ru russia|ee estonia|lv latvia|lt lithuania|ge georgia|am armenia|az azerbaijan|
tr turkey|cy cyprus|mt malta|li liechtenstein|mc monaco|ad andorra|sm san marino|
cn china|tw taiwan|jp japan|kr south korea|kp north korea|mn mongolia|
in india|pk pakistan|bd bangladesh|lk sri lanka|np nepal|bt bhutan|mv maldives|
af afghanistan|sg singapore|my malaysia|id indonesia|th thailand|vn vietnam|
ph philippines|kh cambodia|la laos|mm myanmar|bn brunei|tl timor-leste|
sa saudi arabia|ae united arab emirates|qa qatar|kw kuwait|bh bahrain|om oman|
ye yemen|ir iran|iq iraq|il israel|ps palestine|jo jordan|lb lebanon|sy syria|
eg egypt|
za south africa|ng nigeria|ke kenya|et ethiopia|gh ghana|sn senegal|ci ivory coast|
ma morocco|dz algeria|tn tunisia|ly libya|sd sudan|ss south sudan|so somalia|
ao angola|tz tanzania|cd congo|cg republic of the congo|cm cameroon|mz mozambique|
zm zambia|zw zimbabwe|ug uganda|rw rwanda|bi burundi|ml mali|ne niger|td chad|
bf burkina faso|gn guinea|bj benin|tg togo|sl sierra leone|lr liberia|mr mauritania|
gm gambia|gw guinea-bissau|cf central african republic|ga gabon|
er eritrea|dj djibouti|mg madagascar|mw malawi|bw botswana|na namibia|ls lesotho|
sz eswatini|mu mauritius|
ca canada|mx mexico|gt guatemala|hn honduras|sv el salvador|ni nicaragua|
cr costa rica|pa panama|cu cuba|do dominican republic|ht haiti|jm jamaica|
tt trinidad and tobago|bs bahamas|bz belize|
br brazil|ar argentina|cl chile|co colombia|pe peru|ve venezuela|ec ecuador|
bo bolivia|py paraguay|uy uruguay|gy guyana|sr suriname|
au australia|nz new zealand|pg papua new guinea|fj fiji|gl greenland|
kz kazakhstan|uz uzbekistan|tm turkmenistan|kg kyrgyzstan|tj tajikistan
"""
COUNTRIES = {}
_CANON_BY_ISO = {}
for chunk in _ISO.replace("\n", "").split("|"):
    chunk = chunk.strip()
    if not chunk:
        continue
    iso, name = chunk.split(" ", 1)
    COUNTRIES[name] = {"iso2": iso, "counts_specific": True}
    _CANON_BY_ISO[iso] = name

# supranational / regional pseudo-entities (project but don't count as specific)
for grp in ["european union", "europe", "middle east", "asia pacific",
            "persian gulf", "latin america", "africa", "asia"]:
    COUNTRIES[grp] = {"iso2": None, "counts_specific": False}

# -----------------------------------------------------------------------------
# 1. ALIAS — surface form -> canonical. Short codes, abbreviations, demonyms.
#    Built to swallow BOTH your dict's values ('us','uk','uae') and taxonomy5's
#    ('usa'), plus demonyms the recon flagged ('russian' -> russia).
# -----------------------------------------------------------------------------
ALIAS = {
    # short codes / taxonomy5 legacy
    "us": "united states", "usa": "united states", "u.s.": "united states",
    "u.s.a.": "united states", "america": "united states",
    "uk": "united kingdom", "u.k.": "united kingdom", "britain": "united kingdom",
    "great britain": "united kingdom", "england": "united kingdom",
    "scotland": "united kingdom",
    "uae": "united arab emirates", "emirates": "united arab emirates",
    "arab emirates": "united arab emirates",
    "eu": "european union",
    "korea": "south korea", "korea republic": "south korea",
    "gulf": "persian gulf", "gulf states": "persian gulf", "asia pac": "asia pacific",
    "bosnia": "bosnia and herzegovina",
    # demonyms (recon: "Russian Parliamentary Election" missed by \brussia\b)
    "american": "united states", "americans": "united states",
    "russian": "russia", "russians": "russia", "chinese": "china",
    "british": "united kingdom", "iranian": "iran", "iranians": "iran",
    "israeli": "israel", "israelis": "israel",
    "ukrainian": "ukraine", "ukrainians": "ukraine",
    "japanese": "japan", "german": "germany", "germans": "germany",
    "french": "france", "indian": "india", "indians": "india",
    "pakistani": "pakistan", "pakistanis": "pakistan",
    "north korean": "north korea", "north koreans": "north korea",
    "south korean": "south korea", "south koreans": "south korea",
    "saudi": "saudi arabia", "saudis": "saudi arabia",
    "taiwanese": "taiwan", "lebanese": "lebanon",
    "syrian": "syria", "syrians": "syria", "kuwaiti": "kuwait",
    "turkish": "turkey", "palestinian": "palestine", "palestinians": "palestine",
}


def canon(surface):
    """Normalize any surface form to a canonical country name (or None)."""
    s = surface.lower().strip()
    if s in COUNTRIES:
        return s
    return ALIAS.get(s)


# -----------------------------------------------------------------------------
# 2. CITY -> (country, city_label). Values run through canon() so your 'us'
#    codes normalize automatically. A handful also imply a subdivision.
# -----------------------------------------------------------------------------
_CITY_RAW = {
    "new york": "us", "ny": "us", "nyc": "us", "washington": "us", "chicago": "us",
    "san francisco": "us", "los angeles": "us", "boston": "us", "houston": "us",
    "dallas": "us", "miami": "us", "seattle": "us", "atlanta": "us", "austin": "us",
    "denver": "us", "detroit": "us", "wall street": "us", "silicon valley": "us",
    "permian basin": "us", "gulf coast": "us", "minneapolis": "us",
    "los angeles county": "us",
    "ottawa": "canada", "alberta": "canada",
    "riyadh": "saudi arabia", "jeddah": "saudi arabia", "neom": "saudi arabia",
    "dubai": "uae", "abu dhabi": "uae", "fujairah": "uae", "doha": "qatar",
    "tel aviv": "israel", "jerusalem": "israel", "haifa": "israel",
    "gaza": "palestine", "gaza strip": "palestine", "the gaza strip": "palestine",
    "gaza city": "palestine", "west bank": "palestine",
    "tehran": "iran", "isfahan": "iran", "kharg island": "iran",
    "bandar abbas": "iran", "chabahar": "iran", "jask": "iran", "natanz": "iran",
    "fordow": "iran", "bushehr": "iran", "arak": "iran",
    "istanbul": "turkey", "ankara": "turkey", "bosphorus": "turkey",
    "cairo": "egypt", "suez canal": "egypt", "baghdad": "iraq", "erbil": "iraq",
    "basra": "iraq", "kuwait city": "kuwait", "manama": "bahrain", "muscat": "oman",
    "amman": "jordan", "beirut": "lebanon", "damascus": "syria",
    "moscow": "russia", "saint petersburg": "russia", "novorossiysk": "russia",
    "siberia": "russia", "kamchatka": "russia",
    "kyiv": "ukraine", "odesa": "ukraine", "lviv": "ukraine", "kharkiv": "ukraine",
    "dnipro": "ukraine", "donbas": "ukraine", "donetsk": "ukraine",
    "luhansk": "ukraine", "kerch": "ukraine", "sevastopol": "ukraine",
    "zaporizhzhia": "ukraine", "mariupol": "ukraine", "crimea": "ukraine",
    "tbilisi": "georgia", "batumi": "georgia", "yerevan": "armenia",
    "baku": "azerbaijan",
    "beijing": "china", "shanghai": "china", "shenzhen": "china",
    "guangzhou": "china", "hangzhou": "china", "chengdu": "china", "wuhan": "china",
    "tianjin": "china", "chongqing": "china", "hong kong": "china", "macau": "china",
    "xinjiang": "china", "greater bay area": "china", "qingdao": "china",
    "taipei": "taiwan", "hsinchu": "taiwan", "kaohsiung": "taiwan", "tainan": "taiwan",
    "london": "uk", "edinburgh": "uk", "frankfurt": "germany", "berlin": "germany",
    "munich": "germany", "hamburg": "germany", "paris": "france", "lyon": "france",
    "zurich": "switzerland", "davos": "switzerland", "geneva": "switzerland",
    "basel": "switzerland", "milan": "italy", "rome": "italy",
    "amsterdam": "netherlands", "rotterdam": "netherlands", "the hague": "netherlands",
    "brussels": "belgium", "antwerp": "belgium", "madrid": "spain",
    "barcelona": "spain", "dublin": "ireland", "stockholm": "sweden",
    "copenhagen": "denmark", "oslo": "norway", "helsinki": "finland",
    "warsaw": "poland", "vienna": "austria", "lisbon": "portugal", "athens": "greece",
    "prague": "czech republic", "budapest": "hungary", "chisinau": "moldova",
    "tallinn": "estonia", "riga": "latvia", "vilnius": "lithuania", "narva": "estonia",
    "tokyo": "japan", "osaka": "japan", "kyoto": "japan", "seoul": "south korea",
    "busan": "south korea", "pyongyang": "north korea", "singapore": "singapore",
    "mumbai": "india", "new delhi": "india", "bengaluru": "india", "chennai": "india",
    "hyderabad": "india", "jakarta": "indonesia", "bali": "indonesia",
    "kuala lumpur": "malaysia", "bangkok": "thailand", "hanoi": "vietnam",
    "ho chi minh city": "vietnam", "manila": "philippines", "karachi": "pakistan",
    "islamabad": "pakistan", "dhaka": "bangladesh", "colombo": "sri lanka",
    "johannesburg": "south africa", "cape town": "south africa",
    "pretoria": "south africa", "lagos": "nigeria", "abuja": "nigeria",
    "nairobi": "kenya", "casablanca": "morocco", "rabat": "morocco",
    "algiers": "algeria", "accra": "ghana", "dakar": "senegal",
    "addis ababa": "ethiopia", "luanda": "angola", "abidjan": "ivory coast",
}
CITY = {}
for surf, code in _CITY_RAW.items():
    c = canon(code)
    if c:
        CITY[surf] = c

# -----------------------------------------------------------------------------
# 3. US_STATES (subdivision) — name + postal abbrev -> canonical state.
#    'georgia'/'washington' are COLLISIONS: resolved by context in resolve().
# -----------------------------------------------------------------------------
US_STATES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI",
    "south carolina": "SC", "south dakota": "SD", "tennessee": "TN", "texas": "TX",
    "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
}
_ABBR_TO_STATE = {v: k for k, v in US_STATES.items()}
STATE_COLLISIONS = {"georgia", "washington"}  # also country / city / DC

# -----------------------------------------------------------------------------
# 4. strategic_zones SPLIT by type (they behave differently downstream)
# -----------------------------------------------------------------------------
ORGS = {"g7", "g20", "brics", "opec+", "opec", "nato", "eu", "asean", "gcc",
        "quad", "aukus", "un", "imf", "wto", "five eyes", "sco"}

CHOKEPOINTS = {  # -> country ; also boosts geopolitics
    "strait of hormuz": "iran", "hormuz": "iran", "bab-el-mandeb": "yemen",
    "bab el mandeb": "yemen", "suez canal": "egypt", "panama canal": "panama",
    "strait of malacca": "malaysia", "taiwan strait": "taiwan",
    "strait of gibraltar": "spain", "dardanelles": "turkey", "bosphorus": "turkey",
    "bab el-mandeb": "yemen",
}
CHOKEPOINTS = {k: canon(v) for k, v in CHOKEPOINTS.items()}

SEAS_REGIONS = {  # maritime/land regions: optional country, generic geo signal
    "black sea": "ukraine", "red sea": None, "south china sea": None,
    "baltic sea": None, "caspian sea": None, "persian gulf": None,
    "arabian sea": None, "north sea": None, "arctic circle": None,
    "sahel": None, "horn of africa": None, "kurdistan": None, "kashmir": None,
    "south caucasus": None, "west bank": "palestine", "the west bank": "palestine",
}
SEAS_REGIONS = {k: (canon(v) if v else None) for k, v in SEAS_REGIONS.items()}

# -----------------------------------------------------------------------------
# 5. PEOPLE (leaders + central bankers) with domain, and INSTITUTIONS.
# -----------------------------------------------------------------------------


_LEADERS = {"trump", "bessent", "rubio", "vance", "witkoff", "kushner", "putin",
            "lavrov", "peskov", "zelensky", "khamenei", "araghchi", "pezeshkian",
            "netanyahu", "xi", "macron", "merz", "starmer", "meloni", "tusk",
            "von der leyen", "kallas", "modi", "sharif", "kim jong un"}
_BANKERS = {"powell", "goolsbee", "bowman", "warsh", "daly", "barkin", "bostic",
            "waller", "kashkari", "musalem", "lagarde", "schnabel", "guindos",
            "villeroy", "nagel", "rehn", "kazaks", "simkus", "kazimir", "wunsch",
            "bailey", "ramsden", "dhingra", "lombardelli", "ueda", "himino",
            "noguchi", "uchida", "takata", "nakagawa", "tamura", "schlegel",
            "tschudin", "bullock", "kent", "macklem", "kozicki", "conway",
            "hawkesby", "galipolo", "rhee", "thedeen", "kotecki"}
_FIG_RAW = {  # from figure_to_country
    'trump':'us','bessent':'us','rubio':'us','vance':'us','witkoff':'us','kushner':'us',
    'putin':'russia','lavrov':'russia','peskov':'russia','zelensky':'ukraine',
    'khamenei':'iran','araghchi':'iran','pezeshkian':'iran','netanyahu':'israel',
    'xi':'china','macron':'france','merz':'germany','starmer':'uk','meloni':'italy',
    'tusk':'poland','von der leyen':'eu','kallas':'eu','modi':'india','sharif':'pakistan',
    'kim jong un':'north korea','powell':'us','goolsbee':'us','bowman':'us','warsh':'us',
    'daly':'us','barkin':'us','bostic':'us','waller':'us','kashkari':'us','musalem':'us',
    'lagarde':'eu','schnabel':'eu','guindos':'eu','villeroy':'france','nagel':'germany',
    'rehn':'eu','kazaks':'eu','simkus':'eu','kazimir':'eu','wunsch':'eu','bailey':'uk',
    'ramsden':'uk','dhingra':'uk','lombardelli':'uk','ueda':'japan','himino':'japan',
    'noguchi':'japan','uchida':'japan','takata':'japan','nakagawa':'japan','tamura':'japan',
    'schlegel':'switzerland','tschudin':'switzerland','bullock':'australia','kent':'australia',
    'macklem':'canada','kozicki':'canada','conway':'new zealand','hawkesby':'new zealand',
    'galipolo':'brazil','rhee':'south korea','thedeen':'sweden','kotecki':'poland',
}
PEOPLE = {}
for name, code in _FIG_RAW.items():
    PEOPLE[name] = {"country": canon(code), "domain":
                    "central_bank" if name in _BANKERS else "head_of_state"}

PEOPLE["abbas araghchi"] = {"country": "iran", "domain": "head_of_state"}

from .people_generated import PEOPLE_GENERATED
# for surname, meta in PEOPLE_GENERATED.items():
#     PEOPLE.setdefault(surname, meta)   # n'écrase PAS tes entrées manuelles

_PEOPLE_BLACKLIST = {"al", "dan", "ben", "lee", "ahmed"}
for surname, meta in PEOPLE_GENERATED.items():
    if len(surname) < 4 or surname in _PEOPLE_BLACKLIST:
        continue
    PEOPLE.setdefault(surname, meta)


_INST_RAW = {
    'ustr':'us','fed':'us','pentagon':'us','congress':'us','senate':'us','capitol':'us',
    'state department':'us','treasury':'us','cia':'us','duma':'russia','idf':'israel',
    'mossad':'israel','knesset':'israel','pboc':'china','state council':'china',
    'bundesbank':'germany','bundestag':'germany','boe':'uk','rba':'australia','ecb':'eu',
    'boj':'japan','snb':'switzerland','boc':'canada','rbnz':'new zealand','bok':'south korea',
    'riksbank':'sweden','nbp':'poland','nbh':'hungary','cnb':'czech republic','cbrt':'turkey',
    'rbi':'india','bcb':'brazil','banxico':'mexico','norges':'norway',
}
_CB_INST = {'fed','ecb','boe','boj','snb','boc','rbnz','bok','riksbank','nbp','nbh',
            'cnb','cbrt','rbi','bcb','banxico','norges','pboc','bundesbank'}
INSTITUTIONS = {n: {"country": canon(c),
                    "domain": "central_bank" if n in _CB_INST else "government"}
                for n, c in _INST_RAW.items()}

PERIPHRASE = {'white house':'us','oval office':'us','kremlin':'russia',
              'downing street':'uk','elysee':'france'}
PERIPHRASE = {k: canon(v) for k, v in PERIPHRASE.items()}

# =============================================================================
# RESOLVER
# =============================================================================

# Precompute one big surface -> (kind, payload) map for longest-match scanning.
# kind in {country, city, state, chokepoint, org, region, person, institution, periphrase}
def _build_surface_index():
    idx = {}
    def add(surf, kind, payload):
        idx.setdefault(surf.lower(), []).append((kind, payload))
    for name in COUNTRIES:
        add(name, "country", name)
    for surf, c in ALIAS.items():
        add(surf, "country", c)
    for surf, c in CITY.items():
        add(surf, "city", c)
    for st in US_STATES:
        add(st, "state", st)
    for surf, c in CHOKEPOINTS.items():
        add(surf, "chokepoint", c)
    for o in ORGS:
        add(o, "org", o)
    for surf, c in SEAS_REGIONS.items():
        add(surf, "region", c)
    for name, meta in PEOPLE.items():
        add(name, "person", (name, meta))
    for name, meta in INSTITUTIONS.items():
        add(name, "institution", (name, meta))
    for surf, c in PERIPHRASE.items():
        add(surf, "periphrase", c)
    return idx

_SURFACE_INDEX = _build_surface_index()
# surfaces sorted longest-first (word count then char len) for longest-match
_SURFACES_SORTED = sorted(_SURFACE_INDEX.keys(),
                          key=lambda s: (-len(s.split()), -len(s)))

# case-sensitive US surfaces: the pronoun "us" is ALWAYS lowercase, so the
# case check alone disambiguates. "the US" (country) is uppercase and must
# pass; "tell us"/"join us" (pronoun) is lowercase and is rejected by case.
_US_CASE_SURFACES = {"us", "u.s."}


def _spans_for(surface, text_low):
    """Yield (start, end) match spans of `surface` as whole words in lowercased text."""
    for m in re.finditer(rf"\b{re.escape(surface)}\b", text_low):
        yield m.start(), m.end()


def resolve(event_title, question, tags):
    """Deterministic entity resolution over event_title | question + tags.
    Returns structured geo output. tags is a list[str]."""
    raw = f"{event_title} | {question}".strip(" |")
    low = raw.lower()
    tags_low = {str(t).lower().strip() for t in (tags or [])}
    us_elec_ctx = bool(tags_low & {"us election", "midterms", "elections", "house",
                                   "senate", "governor", "primaries"})

    occupied = [False] * len(low)      # char mask for longest-match arbitration
    hits = {"country": set(), "city": {}, "state": set(), "chokepoint": set(),
            "org": set(), "region": set(), "person": {}, "institution": {},
            "periphrase": set()}

    for surface in _SURFACES_SORTED:
        # case guard: bare "us"/"u.s." only if uppercase in the RAW text,
        # and never when preceded by a verb/article (pronoun).
        payloads = _SURFACE_INDEX[surface]
        for start, end in _spans_for(surface, low):
            if any(occupied[start:end]):
                continue  # a longer surface already claimed these chars
            if surface in _US_CASE_SURFACES:
                if raw[start:end] not in {"US", "U.S.", "U.S.A.", "U.S"}:
                    continue
            # collision arbitration (georgia = state|country, washington =
            # state|city|DC): context picks ONE interpretation, not both.
            active = payloads
            if surface in STATE_COLLISIONS:
                if us_elec_ctx:
                    active = [(k, p) for (k, p) in payloads if k == "state"]
                else:
                    active = [(k, p) for (k, p) in payloads if k != "state"]
            for kind, payload in active:
                if kind == "state":
                    hits["state"].add(payload)
                elif kind == "country":
                    hits["country"].add(payload)
                elif kind == "city":
                    hits["city"][surface] = payload
                    hits["country"].add(payload)
                elif kind == "chokepoint":
                    hits["chokepoint"].add(surface)
                    if payload:
                        hits["country"].add(payload)
                elif kind == "org":
                    hits["org"].add(payload)
                elif kind == "region":
                    hits["region"].add(surface)
                    if payload:
                        hits["country"].add(payload)
                elif kind == "person":
                    nm, meta = payload
                    hits["person"][nm] = meta
                    if meta["country"]:
                        hits["country"].add(meta["country"])
                elif kind == "institution":
                    nm, meta = payload
                    hits["institution"][nm] = meta
                    if meta["country"]:
                        hits["country"].add(meta["country"])
                elif kind == "periphrase":
                    hits["periphrase"].add(surface)
                    if payload:
                        hits["country"].add(payload)
            for i in range(start, end):
                occupied[i] = True

    # tags also carry countries AND orgs (event-scoped) -> fold them in
    for t in tags_low:
        c = canon(t)
        if c:
            hits["country"].add(c)
        if t in ORGS:
            hits["org"].add(t)

    # `countries` = REAL countries only (iso2 set). Regions / supranationals
    # (middle east, europe, eu, persian gulf) stay OUT of the list — they are
    # signals (org_signal / region), not join-key countries.
    countries = sorted(c for c in hits["country"] if COUNTRIES.get(c, {}).get("iso2"))
    pair, pair_provenance = infer_pair(countries)
    hot_dyad = pair is not None and frozenset(pair) in HOT_DYADS
    org_signal = bool(hits["org"]) or bool(hits["chokepoint"])

    subdivision = sorted(hits["state"])[0] if hits["state"] else None
    city = sorted(hits["city"].keys())[0] if hits["city"] else None

    return {
        "countries": countries,
        "country_pair": pair,               # sorted, deterministic, non-ordered
        "pair_provenance": pair_provenance,  # "explicit" | "inferred" | None
        "hot_dyad": hot_dyad,               # salience flag (metadata only)
        "org_signal": org_signal,           # feeds politics-vs-geo decision
        "subdivision": subdivision,         # US state (Kalshi-ready)
        "city": city,                       # canonical city surface
        "people": {k: v["domain"] for k, v in hits["person"].items()},
        "institutions": {k: v["domain"] for k, v in hits["institution"].items()},
        "chokepoints": sorted(hits["chokepoint"]),
    }


# =============================================================================
# TESTS
# =============================================================================
if __name__ == "__main__":
    T = [
        # (event, question, tags)
        ("Will China invade Taiwan by 2026?", "Will China invade Taiwan by end of 2026?",
         ["China", "Geopolitics", "Politics"]),
        ("Netanyahu out by...?", "Netanyahu out by end of 2026?", ["Israel", "Geopolitics"]),
        ("Russian Parliamentary Election", "Will United Russia win a majority?", ["Politics", "World"]),
        ("Will Powell cut rates in September?", "Fed cuts 25bps in September?", ["Fed", "Politics"]),
        ("Will the US strike Iran?", "US airstrike on Iran before August?", ["Geopolitics", "Iran"]),
        ("Will Macron tell us the truth?", "Macron statement before July?", ["Politics", "France"]),   # pronoun trap
        ("Georgia Senate Runoff", "Will the Democrat win the Georgia Senate seat?",
         ["US Election", "Senate", "Politics"]),                                                       # state
        ("Next President of Georgia", "Will the opposition win in Georgia?", ["Geopolitics", "World"]),# country (no US ctx)
        ("Strait of Hormuz blockade?", "Iran closes the Strait of Hormuz in 2026?", ["Oil", "Geopolitics"]),
        ("CA-28 House Election Winner", "Democratic", ["US Election", "House", "Midterms"]),
    ]
    for ev, q, tg in T:
        r = resolve(ev, q, tg)
        print(f"\n{ev[:50]}")
        print(f"   countries={r['countries']} pair={r['country_pair']} "
              f"org={r['org_signal']} sub={r['subdivision']} city={r['city']}")
        if r['people']:
            print(f"   people={r['people']}")

# =============================================================================
# HOT_DYADS + IMPLIED_ADVERSARY  (pair salience & editorial adversary inference)
#
# Design contract:
#   - HOT_DYADS is a *metadata* watchlist (arbitrage prioritization). It never
#     affects topic classification.
#   - IMPLIED_ADVERSARY infers a low-confidence pair for a lone country under
#     a clear venue-framing. It produces country_pair with
#     pair_provenance="inferred" but MUST NOT flip politics->geopolitics
#     (that stays on explicit signals: >=2 real countries, org, conflict verb).
# =============================================================================
HOT_DYADS = {
    frozenset({"australia", "china"}),
    frozenset({"bahrain", "iran"}),
    frozenset({"belarus", "poland"}),
    frozenset({"china", "india"}),
    frozenset({"china", "japan"}),
    frozenset({"china", "philippines"}),
    frozenset({"china", "taiwan"}),
    frozenset({"china", "united states"}),
    frozenset({"cuba", "united states"}),
    frozenset({"estonia", "russia"}),
    frozenset({"european union", "united states"}),
    frozenset({"finland", "russia"}),
    frozenset({"greenland", "united states"}),
    frozenset({"india", "pakistan"}),
    frozenset({"iran", "israel"}),
    frozenset({"iran", "kuwait"}),
    frozenset({"iran", "qatar"}),
    frozenset({"iran", "saudi arabia"}),
    frozenset({"iran", "united arab emirates"}),
    frozenset({"iran", "united states"}),
    frozenset({"iraq", "united states"}),
    frozenset({"israel", "lebanon"}),
    frozenset({"israel", "palestine"}),
    frozenset({"israel", "yemen"}),
    frozenset({"japan", "north korea"}),
    frozenset({"latvia", "russia"}),
    frozenset({"lithuania", "russia"}),
    frozenset({"north korea", "south korea"}),
    frozenset({"north korea", "united states"}),
    frozenset({"panama", "united states"}),
    frozenset({"russia", "ukraine"}),
    frozenset({"russia", "united states"}),
    frozenset({"united states", "venezuela"}),
}

# lone country -> default adversary (unambiguous venue-framings only)
IMPLIED_ADVERSARY = {
    "venezuela": "united states", "cuba": "united states",
    "taiwan": "china", "north korea": "united states",
    "greenland": "united states", "panama": "united states",
}


def infer_pair(countries):
    """Given the list of REAL countries present, return (pair, provenance).
    2 countries -> explicit; 1 country with a clear implied adversary ->
    inferred; else (None, None)."""
    if len(countries) == 2:
        return tuple(countries), "explicit"
    if len(countries) == 1:
        adv = IMPLIED_ADVERSARY.get(countries[0])
        if adv and adv != countries[0]:
            return tuple(sorted((countries[0], adv))), "inferred"
    return None, None
