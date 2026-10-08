"""Check that the numbers written in presentation/index.html (slides 1 to 6) match results/.

Usage: python3 presentation/build_piero_slides.py   (prints OK or the mismatches)
"""
import csv
from pathlib import Path

R = Path(__file__).resolve().parents[1] / "results"
rows = lambda f: list(csv.DictReader(open(R / f, encoding="utf-8")))
bad = []


def check(name, got, want, tol=0.006):
    if abs(got - want) > tol:
        bad.append(f"{name}: results {got:.3f} vs slide {want}")


# Slide 3: funnel
cs = rows("site_data/classification_summary.csv")
check("markets", sum(int(r["markets"]) for r in cs), 80203, 0)
check("macro", sum(int(r["markets"]) for r in cs if r["theme"] != "OTHER"), 29704, 0)

# Slide 4: coverage, USD 50k
cov = {(r["zone"], r["theme"]): float(r["share_train"]) * 100 for r in rows("coverage_cells.csv")}
for key, v in {("US", "MONETARY"): 93.9, ("GLOBAL", "GEOPOLITICS"): 76.7, ("US", "FISCAL_POLITICAL"): 68.5,
               ("US", "GEOPOLITICS"): 52.6, ("CN", "GEOPOLITICS"): 33.1, ("US", "TRADE_TARIFFS"): 30.8,
               ("US", "INFLATION"): 25.0, ("EA", "FISCAL_POLITICAL"): 7.6, ("UK", "FISCAL_POLITICAL"): 7.6,
               ("JP", "MONETARY"): 3.1}.items():
    check("coverage " + "/".join(key), cov[key], v, 0.06)
check("cells passing at 60%", sum(v >= 60 for v in cov.values()), 3, 0)

# Slide 5: daily t-stats (A1), hourly t-stats, weekend t-stats
d = {(r["model"], r["horizon"], r["regressor"]): float(r["t"]) for r in rows("strategy_a/diagnostics.csv")}
for reg, vals in {"MONETARY": [4.02, 0.75, 1.02], "FISCAL_POLITICAL": [0.33, 0.93, 1.92]}.items():
    for h, v in zip(["0", "1", "5"], vals):
        check(f"daily {reg} h{h}", d[("A1_contemporaneous" if h == "0" else "A1_predictive", h, reg)], v)
hourly = [-1.31, 1.41, -0.82, 1.48, -1.38, 1.30, 5.80, 2.64, 1.63, -0.06, 0.13, -0.90, -1.33]
ll = [r for r in rows("leadlag/event_study.csv") if r["study"] == "FX top 1% -> PM US/MONETARY"]
for r, v in zip(sorted(ll, key=lambda r: int(r["hour"])), hourly):
    se = (float(r["ci_high"]) - float(r["ci_low"])) / (2 * 1.96)
    check(f"hourly h{r['hour']}", float(r["mean"]) / se, v)
wk = {r["regressor"]: float(r["t"]) for r in rows("weekend/weekend_gap_regressions.csv")
      if r["model"] == "A1+GEO_weekend_gap_london"}
for reg, v in {"MONETARY": 0.00, "FISCAL_POLITICAL": 0.59, "SPILL_GLOBAL_GEOPOLITICS": -0.62}.items():
    check("weekend " + reg, wk[reg], v)

# Slide 6: A vs B correlation
ab = [r for r in rows("risk/a_vs_b_correlation.csv") if r["a"] == "A1_theory_with_dollar"][0]
check("corr A1 vs B", float(ab["return_corr"]), -0.04, 0.006)

print("OK: every number on slides 1 to 6 matches results/" if not bad else "\n".join(["MISMATCH"] + bad))
