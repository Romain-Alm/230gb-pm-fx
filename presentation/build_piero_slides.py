"""Inline the data of Piero's opening slides (1 to 6) into presentation/index.html.

Reads the result files of SLIDES_PIERO.md section 2 (read-only), computes the derived numbers,
checks them against the expected values (tolerance: last displayed digit) and rewrites two
things in index.html:
  - the data block <script id="deck-data"> (window.DECK_DATA = {...}), read by the charts and controls;
  - the text of every element with data-k="<key>" (the numbers quoted in the slide text).
Markup, styles and scripts of index.html are edited by hand, and teammates append their own
<section class="slide"> blocks: this script never touches them. It also refuses to write a deck
that contains an em dash. Run from anywhere:

    python3 presentation/build_piero_slides.py
"""
from __future__ import annotations

import html
import json
import math
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
DECK = ROOT / "presentation" / "index.html"

# (zone, theme) of the three kept cells, the key used in the deck, and the label on the slides.
CELLS = [("US", "MONETARY", "mon", "US monetary"),
         ("US", "FISCAL_POLITICAL", "fis", "US fiscal-political"),
         ("GLOBAL", "GEOPOLITICS", "geo", "Global geopolitics")]
ZONE = {"US": "US", "GLOBAL": "Global", "CN": "China", "KR": "Korea", "EA": "Euro area", "UK": "UK",
        "JP": "Japan", "MX": "Mexico", "CA": "Canada", "CH": "Switzerland", "AU": "Australia",
        "NZ": "New Zealand", "NO": "Norway", "SE": "Sweden", "BR": "Brazil", "TW": "Taiwan", "IN": "India"}
THEME = {"MONETARY": "Monetary", "FISCAL_POLITICAL": "Fiscal-political", "GEOPOLITICS": "Geopolitics",
         "TRADE_TARIFFS": "Tariffs", "INFLATION": "Inflation"}
G10_EX_US = {"EA", "JP", "UK", "CH", "AU", "NZ", "CA", "NO", "SE"}
GATE, HEAT_ROWS = 0.60, 15  # 15 rows (spec: 14) so that Japan · Monetary, named on the slide, is shown

# HARDCODED (SLIDES_PIERO.md section 2). The first five are checked against the text of
# results/RESULTS.md below; the 2024-08-02 dollar move comes from the A1 P&L/weights files.
HARD = {"panel": 9103, "bn_kalshi": 2.28, "bn_poly": 8.88, "drift_raw": 0.079, "drift_raw_t": 2.9,
        "drift_hz": 0.06, "drift_hz_t": 2.1, "ex_usd": -0.8, "ex_eur": 1.1, "ex_jpy": 1.9, "ex_chf": 1.6}
RESULTS_MD_PATTERNS = [r"Contracts in the panel: 9,103",
                       r"\| kalshi \| 50,281 \| [\d,]+ \| 2\.28 \|",
                       r"\| polymarket \| 29,922 \| [\d,]+ \| 8\.88 \|",
                       r"US MONETARY would be 0\.079 sd per day \(t = 2\.9\)",
                       r"\| US/MONETARY \| \d+ \| [\d.]+ \| 0\.06 \| 2\.1\d \|"]

FAIL: list[str] = []


def expect(name, got, want, dec=None):
    ok = got == want if dec is None else abs(got - want) <= 10 ** -dec + 1e-9
    if not ok:
        FAIL.append(f"{name}: got {got!r}, expected {want!r}")


def num(x, dec=0, sign=False):
    """Slide formatting: thousands separator, true minus sign."""
    s = f"{abs(x):,.{dec}f}"
    return ("−" if x < 0 and float(s.replace(",", "")) else "+" if sign and x > 0 else "") + s


def r(x, dec=2):
    return round(float(x), dec)


# ---- S1. Liquid contracts per day in the three kept cells, quarterly mean of calendar days
ti = pd.read_csv(RES / "site_data/theme_indices.csv", usecols=["day", "zone", "theme", "n_contracts", "vol7d", "d_vw"],
                 parse_dates=["day"])
days = pd.date_range(ti.day.min(), ti.day.max())
seg = {}
for zone, theme, key, _ in CELLS:
    s = ti[(ti.zone == zone) & (ti.theme == theme)].set_index("day").n_contracts
    expect(f"S1 {key}: one row per calendar day", s.index.equals(days), True)
    seg[key] = s.groupby(s.index.to_period("Q")).mean()
seg = pd.DataFrame(seg)
shown = seg.round(1)                     # stacked segments as displayed
total = shown.sum(axis=1).round(1)       # displayed total = sum of the displayed segments
quarters = [str(q) for q in seg.index]
want_s1 = [2.7, 3.7, 18.1, 31.5, 9.1, 16.6, 14.0, 19.3, 41.8, 45.2, 38.0]
expect("S1 quarters", quarters, [f"{y}Q{q}" for y in (2024, 2025, 2026) for q in (1, 2, 3, 4)][:11])
for q, got, exact, want in zip(quarters, total, seg.sum(axis=1), want_s1):
    expect(f"S1 total {q}", got, want, 1)
    expect(f"S1 unrounded total {q} within rounding of the segments", abs(exact - want) <= 0.15, True)

# ---- S3. Funnel
cs = pd.read_csv(RES / "site_data/classification_summary.csv")
macro = cs[cs.theme != "OTHER"]
by_pf = cs.groupby("platform").markets.sum()
n = {"all": int(cs.markets.sum()), "kalshi": int(by_pf["kalshi"]), "poly": int(by_pf["polymarket"]),
     "macro": int(macro.markets.sum()), "usable": int(macro.usable.sum()), "panel": HARD["panel"]}
c50 = pd.read_csv(RES / "coverage_cells.csv")
c10 = pd.read_csv(RES / "coverage_cells_v10k.csv")
n["pass"] = int(c50.keep.sum())
for k, want in {"all": 80203, "kalshi": 50281, "poly": 29922, "macro": 29704, "usable": 11276, "pass": 3}.items():
    expect(f"S3 {k}", n[k], want)
expect("S3 panel below usable (brackets collapsed)", n["panel"] < n["usable"], True)
results_md = (RES / "RESULTS.md").read_text(encoding="utf-8")
for pat in RESULTS_MD_PATTERNS:
    expect(f"HARDCODED source text /{pat}/ in results/RESULTS.md", bool(re.search(pat, results_md)), True)

ex = pd.read_csv(RES / "site_data/classification_examples.csv")
EXAMPLES = [("Will the upper bound of the federal funds rate be above 3.50% following the Fed's Apr 28, 2027 meeting?",
             "US", "MONETARY", 1),
            ("Russia x Ukraine ceasefire by January 31, 2026?", "GLOBAL", "GEOPOLITICS", -1),
            ("Will the Republican Party win the NJ-08 House seat?", "US", "FISCAL_POLITICAL", 0)]
MEANING = {("MONETARY", 1): "hawkish", ("MONETARY", -1): "dovish",
           ("GEOPOLITICS", 1): "escalation", ("GEOPOLITICS", -1): "de-escalation"}
examples = []
for title, *want in EXAMPLES:
    row = ex[ex.title == title]
    expect(f"S3 example in file: {title[:40]}", len(row), 1)
    if len(row):
        row = row.iloc[0]
        got = [row.zones, row.theme, int(row.direction)]
        expect(f"S3 example labels: {title[:40]}", got, want)
        examples.append({"title": title, "zone": ZONE.get(row.zones, row.zones), "theme": row.theme.replace("_", "-"),
                         "dir": int(row.direction), "meaning": MEANING.get((row.theme, int(row.direction)), ""),
                         "rule": f"{row.theme_rule} · {row.direction_rule}"})

# ---- S4. Coverage gate
def passing(df, g=GATE):
    return df[df.share_train >= g - 1e-9]


for name, df, want in (("50k", c50, 3), ("10k", c10, 5)):
    expect(f"S4 {name} cells passing at {GATE}", len(passing(df)), want)
    expect(f"S4 {name} passing = keep flag", set(passing(df).index), set(df.index[df.keep]))
p50 = passing(c50).set_index(["zone", "theme"]).share_train
expect("S4 50k passing cells", p50.round(3).to_dict(),
       {("US", "MONETARY"): 0.939, ("GLOBAL", "GEOPOLITICS"): 0.767, ("US", "FISCAL_POLITICAL"): 0.685})
below = c50[c50.share_train < GATE].sort_values("share_train", ascending=False).iloc[0]
expect("S4 next cell below the gate", (below.zone, below.theme, below.share_train), ("US", "GEOPOLITICS", 0.526))
same_lo, same_hi = math.ceil(below.share_train * 100 + 1e-9), math.floor(p50.min() * 100 + 1e-9)
expect("S4 same-three range", (same_lo, same_hi), (53, 68))
p10 = passing(c10).set_index(["zone", "theme"]).share_train
expect("S4 10k extra cells", {k: v for k, v in p10.items() if k not in p50},
       {("CN", "GEOPOLITICS"): 0.746, ("US", "GEOPOLITICS"): 0.642})
g10 = c10[c10.zone.isin(G10_EX_US)].sort_values("share_train", ascending=False)
expect("S4 best non-US G10 cell at 10k", list(g10.iloc[0][["zone", "theme", "share_train"]]), ["UK", "FISCAL_POLITICAL", 0.314])
expect("S4 second non-US G10 cell at 10k", list(g10.iloc[1][["zone", "theme", "share_train"]]), ["EA", "FISCAL_POLITICAL", 0.310])
uk = c50.set_index(["zone", "theme"]).loc[("UK", "FISCAL_POLITICAL")]
expect("S4 UK fiscal share_test at 50k", uk.share_test, 0.55, 2)

cq = pd.read_csv(RES / "site_data/coverage_quarterly.csv")
cq["q"] = pd.PeriodIndex(pd.to_datetime(cq.quarter), freq="Q").astype(str)
expect("S4 heatmap quarters", sorted(cq.q.unique()), quarters)
cq = cq.set_index(["zone", "theme", "q"])
s10 = c10.set_index(["zone", "theme"]).share_train
heat = []
for _, c in c50.sort_values("share_train", ascending=False, kind="mergesort").head(HEAT_ROWS).iterrows():
    k = (c.zone, c.theme)
    heat.append({"label": f"{ZONE.get(c.zone, c.zone)} · {THEME.get(c.theme, c.theme)}", "cell": "_".join(k),
                 "s50": r(c.share_train, 3), "s10": r(s10.get(k, 0.0), 3), "test50": r(c.share_test, 3),
                 "q": [r(cq.share_days_covered.get((*k, q), 0.0), 3) for q in quarters],
                 "n": [int(cq.n_contracts.get((*k, q), 0)) for q in quarters]})
expect("S4 Japan monetary among the rows", any(h["cell"] == "JP_MONETARY" for h in heat), True)


def cell_list(df):
    return [{"label": f"{ZONE.get(z, z)} · {THEME.get(t, t)}", "s": r(s, 3)}
            for z, t, s in df.sort_values("share_train", ascending=False)[["zone", "theme", "share_train"]].values]


# ---- S5a. Daily horizons
dg = pd.read_csv(RES / "strategy_a/diagnostics.csv")
dg = dg[((dg.model == "A1_contemporaneous") & (dg.horizon == 0)) | ((dg.model == "A1_predictive") & dg.horizon.isin([1, 5, 20]))]
dg = dg.set_index(["regressor", "horizon"]).t
s5a = {k: [r(dg[(reg, h)]) for h in (0, 1, 5, 20)] for k, reg in (("mon", "MONETARY"), ("fis", "FISCAL_POLITICAL"))}
for k, want in {"mon": [4.02, 0.75, 1.02, -0.46], "fis": [0.33, 0.93, 1.92, 3.35]}.items():
    for h, got, w in zip((0, 1, 5, 20), s5a[k], want):
        expect(f"S5a {k} h{h}", got, w, 2)

# ---- S5b. Hourly event studies, t = mean / (CI width / (2 x 1.96))
ll = pd.read_csv(RES / "leadlag/event_study.csv")
ll["t"] = ll["mean"] / ((ll.ci_high - ll.ci_low) / (2 * 1.96))
hours = list(range(-6, 7))
s5b = {}
for zone, theme, key, _ in CELLS:
    out = {}
    for d, study in (("pm", f"FX top 1% -> PM {zone}/{theme}"), ("fx", f"PM {zone}/{theme} top 1% -> FX dollar basket")):
        st = ll[ll.study == study].set_index("hour").reindex(hours)
        expect(f"S5b {study}: hours -6 to +6", bool(st.t.notna().all()), True)
        out[d] = {"t": [r(v) for v in st.t], "n": [int(v) for v in st.n_events.fillna(0)]}
    s5b[key] = out
for d, want in {"pm": {-3: 1.48, -2: -1.38, -1: 1.30, 0: 5.80, 1: 2.64, 2: 1.63, 3: -0.06},
                "fx": {-3: 0.96, -2: 0.46, -1: 1.49, 0: 2.50, 1: 0.61, 2: -0.21}}.items():
    for h, w in want.items():
        expect(f"S5b mon {d} h{h}", s5b["mon"][d]["t"][hours.index(h)], w, 2)

# ---- S5c. Weekend gap
wk = pd.read_csv(RES / "weekend/weekend_gap_regressions.csv")
s5c = {}
for key, model in (("london", "A1+GEO_weekend_gap_london"), ("ny", "A1+GEO_weekend_gap_ny")):
    m = wk[wk.model == model].set_index("regressor")
    s5c[key] = {"t": [r(m.t[g]) for g in ("MONETARY", "FISCAL_POLITICAL", "SPILL_GLOBAL_GEOPOLITICS")],
                "n": int(m.n_obs.iloc[0])}
for key, want, n_obs in (("london", [0.00, 0.59, -0.62], 1278), ("ny", [1.27, -0.64, 0.74], 1272)):
    for i, w in enumerate(want):
        expect(f"S5c {key} t[{i}]", s5c[key]["t"][i], w, 2)
    expect(f"S5c {key} n_obs", s5c[key]["n"], n_obs)
max_abs_t = max(abs(t) for v in s5c.values() for t in v["t"])
bound = math.ceil(max_abs_t * 10) / 10
expect("S5c bound on |t|", bound, 1.3, 1)

# ---- S5 example day: 2024-08-02, largest dovish move of US MONETARY
mon = ti[(ti.zone == "US") & (ti.theme == "MONETARY")].set_index("day").d_vw
expect("S5 example d_vw on 2024-08-02", r(mon["2024-08-02"], 1), -5.0, 1)
expect("S5 example is the most dovish day", str(mon.idxmin().date()), "2024-08-02")

# ---- S6. Correlation of A1 and PM-timed B
ab = pd.read_csv(RES / "risk/a_vs_b_correlation.csv").set_index("a")
corr = r(ab.loc["A1_theory_with_dollar", "return_corr"])
expect("S6 A/B return correlation", corr, -0.04, 2)

# ---- Deck data and slide text
DATA = {
    "cells": [{"key": k, "label": lab} for _, _, k, lab in CELLS],
    "s1": {"quarters": quarters, "seg": {k: shown[k].tolist() for k in shown}, "total": total.tolist(),
           "partial": quarters[-1], "end": str(days[-1].date())},
    "s3": {**n, "bn_kalshi": HARD["bn_kalshi"], "bn_poly": HARD["bn_poly"]},
    "examples": examples,
    "s4": {"quarters": quarters, "rows": heat, "all": {"50": cell_list(c50), "10": cell_list(c10)}, "gate": GATE},
    "s5a": {"horizons": ["Same day", "+1 day", "+5 days", "+20 days"], **s5a},
    "s5b": {"hours": hours, **s5b},
    "s5c": {"rows": [lab for *_, lab in CELLS], **s5c},
    "s5ex": {"d": r(mon["2024-08-02"], 1), "usd": HARD["ex_usd"], "eur": HARD["ex_eur"], "jpy": HARD["ex_jpy"], "chf": HARD["ex_chf"]},
}
TXT = {
    "n.all": num(n["all"]), "n.kalshi": num(n["kalshi"]), "n.poly": num(n["poly"]), "n.macro": num(n["macro"]),
    "n.usable": num(n["usable"]), "n.panel": num(n["panel"]), "n.pass": num(n["pass"]),
    "n.all_k": num(round(n["all"], -4)), "n.macro_k": num(round(n["macro"], -4)), "n.usable_k": num(round(n["usable"], -3)),
    "bn.total": num(HARD["bn_kalshi"] + HARD["bn_poly"], 1), "bn.total_int": num(HARD["bn_kalshi"] + HARD["bn_poly"]),
    "bn.kalshi": num(HARD["bn_kalshi"], 2), "bn.poly": num(HARD["bn_poly"], 2),
    "drift.raw": num(HARD["drift_raw"], 3), "drift.raw_t": num(HARD["drift_raw_t"], 1),
    "drift.hz": num(HARD["drift_hz"], 2), "drift.hz_t": num(HARD["drift_hz_t"], 1),
    "s1.end": days[-1].strftime("%b %-d"),
    "s4.lo": str(same_lo), "s4.hi": str(same_hi), "s4.uk10": num(100 * g10.iloc[0].share_train),
    "s4.uk_test": num(100 * uk.share_test),
    "s5a.mon0_int": num(s5a["mon"][0]), "s5a.mon1": num(s5a["mon"][1], 2),
    "s5a.mon5": num(s5a["mon"][2]),
    "s5.ex_d": num(mon["2024-08-02"]), "s5.ex_usd": num(abs(HARD["ex_usd"]), 1),
    "s5c.n": num(s5c["london"]["n"]), "s5c.bound": num(bound, 1),
    "s6.corr": num(corr, 2),
}

deck = DECK.read_text(encoding="utf-8")
blob = json.dumps(DATA, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
deck, n_json = re.subn(r'(<script id="deck-data">window\.DECK_DATA = ).*?(;</script>)',
                       lambda m: m.group(1) + blob + m.group(2), deck, flags=re.S)
expect("deck-data block present once", n_json, 1)
used = set()


def fill(m):
    key = m.group("k")
    used.add(key)
    if key not in TXT:
        FAIL.append(f'index.html uses data-k="{key}", which the build script does not define')
        return m.group(0)
    return m.group("open") + html.escape(TXT[key]) + m.group("close")


deck = re.sub(r'(?P<open><(?P<tag>[a-z0-9]+)\b[^>]*\bdata-k="(?P<k>[^"]+)"[^>]*>)[^<]*(?P<close></(?P=tag)>)', fill, deck)
for bad, name in (("—", "em dash"), ("–", "en dash")):
    if bad in deck:
        line = deck[:deck.index(bad)].count("\n") + 1
        FAIL.append(f"index.html contains an {name} (first on line {line})")

if FAIL:
    sys.exit("BUILD FAILED, nothing written:\n  " + "\n  ".join(FAIL))
DECK.write_text(deck, encoding="utf-8")
unused = sorted(set(TXT) - used)
print(f"OK: all checks passed; {len(used)} text keys filled, JSON {len(blob):,} bytes -> {DECK.relative_to(ROOT)}"
      + (f"\n(unused text keys: {', '.join(unused)})" if unused else ""))
