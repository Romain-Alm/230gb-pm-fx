"""The HTML page's data against results/RESULTS.md, and the page's style rule (no em dash).

Every headline number of the page (brief section 8) is rebuilt from `window.DATA` with the
formatting of `summary_md.py` and looked up in RESULTS.md, so the page and the report cannot
drift apart. Momentum numbers, which RESULTS.md does not carry, are checked against the note
that reports them. Skipped without the definitive results.
"""
from __future__ import annotations

import pytest

from src.common import ROOT
from src.report.summary_md import PERIOD_LABEL, _ci, _fmt

SITE = ROOT / "results" / "site_data"
RESULTS = ROOT / "results" / "RESULTS.md"
NOTE = ROOT / "results" / "notes" / "strategy_a_explained.md"
SRC = ROOT / "src" / "report" / "site"
EM_DASH = "\u2014"

pytestmark = pytest.mark.skipif(not (SITE / "strategy_a_performance.csv").exists() or not RESULTS.exists(),
                                reason="definitive results not available")


@pytest.fixture(scope="module")
def data():
    from src.report.build_site import assemble_data
    return assemble_data()


@pytest.fixture(scope="module")
def md():
    return RESULTS.read_text(encoding="utf-8")


def row(*cells) -> str:
    return "| " + " | ".join(str(c) for c in cells) + " |"


def _assert_in(md: str, needle: str, what: str):
    assert needle in md, f"{what}: {needle!r} not found in RESULTS.md"


# ------------------------------------------------------------------ data and coverage
def test_pm_summary_and_classification(data, md):
    for r in data["pm_summary"]["rows"]:
        _assert_in(md, row(r["platform"], f"{r['markets']:,}", f"{r['market_days']:,}", _fmt(r["volume_usd_bn"], "volume_bn")),
                   "PM summary")
    for r in data["classification"]["by_theme"]:
        _assert_in(md, row(r["theme"], f"{r['markets']:,}", f"{r['events']:,}", f"{r['usable']:,}"), "classification")


def test_coverage_cells(data, md):
    cells = {(c["zone"], c["theme"]): c for c in data["coverage"]["cells"]}
    for key in (("US", "MONETARY"), ("GLOBAL", "GEOPOLITICS"), ("US", "FISCAL_POLITICAL"), ("US", "GEOPOLITICS"),
                ("UK", "FISCAL_POLITICAL"), ("JP", "MONETARY")):
        c = cells[key]
        _assert_in(md, row(c["zone"], c["theme"], _fmt(c["share_train"], "share_train"), _fmt(c["share_test"], "share_test"),
                           f"{c['n_contracts']:,}", f"{c['n_events']:,}"), f"coverage {key}")
    assert data["coverage"]["n_kept"] == sum(1 for c in data["coverage"]["cells"] if c["keep"])
    _assert_in(md, f"Cells that pass the coverage rule: {data['coverage']['n_kept']}", "number of kept cells")


# ------------------------------------------------------------------ timing
def test_panel_tstats(data, md):
    for r in data["timing"]["tstats"]:
        if r["model"].startswith(("A1_predictive", "A1_contemporaneous", "A2_predictive", "A2_contemporaneous")):
            _assert_in(md, row(r["model"], r["horizon"], r["regressor"], _fmt(r["coef"], "coef"), _fmt(r["t"], "t"),
                               f"{r['n_obs']:,}"), f"t-stat {r['model']} {r['regressor']} {r['horizon']}")


def test_weekend_gap(data, md):
    w = data["timing"]["weekend"]
    _assert_in(md, f"maximum |t| {w['max_abs_t']:.1f}, null result", "weekend max |t|")
    for r in w["rows"]:
        _assert_in(md, row(r["model"], r["regressor"], _fmt(r["coef"], "coef"), _fmt(r["t"], "t"), f"{r['n_obs']:,}"),
                   f"weekend row {r['model']} {r['regressor']}")
    assert w["n_pair_weekends"] == next(r["n_obs"] for r in w["rows"] if r["model"] == "A1+GEO_weekend_gap_london")


# ------------------------------------------------------------------ performance tables
def _perf_row(r: dict) -> str:
    return row(r["strategy"], PERIOD_LABEL[r["period"]], _fmt(r["sharpe"], "sharpe"), _fmt(r["sharpe_t"], "sharpe_t"),
               _ci([r["sharpe_ci90_low"]], [r["sharpe_ci90_high"]])[0], _fmt(r["ann_mean"], "ann_mean"),
               _fmt(r["ann_vol"], "ann_vol"), _fmt(r["max_drawdown"], "max_drawdown"))


def test_strategy_a_performance(data, md):
    rows = data["strategy_a"]["performance"]
    assert len(rows) == 3 * len({r["strategy"] for r in rows})
    shown = [r for r in rows if f"| {r['strategy']} |" in md]   # RESULTS.md prints the gross rows of A1 and A2 only
    assert {r["strategy"] for r in shown} >= {"A1_theory_with_dollar", "A1_theory_with_dollar_gross", "A2_theory_with_dollar",
                                              "A2_theory_with_dollar_gross", "A2_theory_dollar_neutral", "A1+S_theory_with_dollar",
                                              "A1_theory_with_dollar_weekly", "A1_gated20_frozen"}
    for r in shown:
        _assert_in(md, _perf_row(r), f"A performance {r['strategy']} {r['period']}")


def test_strategy_b_performance(data, md):
    rows = data["strategy_b"]["performance"]
    for r in rows:
        _assert_in(md, _perf_row(r), f"B performance {r['strategy']} {r['period']}")


# ------------------------------------------------------------------ strategy A checks
def test_d30_phase_and_effective_sample(data, md):
    for s in data["strategy_a"]["d30"]["summary"]:
        _assert_in(md, row(PERIOD_LABEL[s["period"]], _fmt(s["published"], "sharpe"), _fmt(s["mean"], "sharpe"),
                           _fmt(s["min"], "sharpe"), _fmt(s["max"], "sharpe"), f"{s['n_positive']} / {s['n']}",
                           f"{s['rank']} / {s['n']}"), f"D30 phase summary {s['period']}")
    for r in data["strategy_a"]["d30"]["effective_sample"]:
        if r["offset"] == 0:
            _assert_in(md, row(r["period"], r["n"], _fmt(r["t"], "t")), f"D30 effective sample {r['period']}")


def test_static_timing_and_gate(data, md):
    for r in data["strategy_a"]["robustness"]["static_timing"]:
        _assert_in(md, row(r["strategy"], r["part"], PERIOD_LABEL[r["period"]], _fmt(r["sharpe"], "sharpe"),
                           _fmt(r["sharpe_t"], "sharpe_t")), f"static/timing {r['strategy']} {r['part']} {r['period']}")
    g = data["strategy_a"]["robustness"]["gate"]
    for r in g["rows"]:
        _assert_in(md, row(r["variant"], r["regressor"], _fmt(r["coef"], "coef"), _fmt(r["t"], "t"), f"{r['n_obs']:,}",
                           "yes" if r["passes_gate"] else "no"), f"gate {r['variant']} {r['regressor']}")
    assert g["n_pass"] == 0


def test_fiscal_regime(data, md):
    for r in data["strategy_a"]["fiscal_regime_days"]:
        if r["zone"] == "US" and r["year"] >= 2024:
            _assert_in(md, f"{r['year']}: {100 * r['share']:.1f}%", f"fiscal regime share {r['year']}")


def test_placebos_and_leave_one_out_a(data, md):
    p = data["strategy_a"]["robustness"]["placebo"]
    for v, label in (("A1", "A1 with dollar"), ("A2", "A2 with dollar")):
        _assert_in(md, f"**Strategy A, {label}**: the actual Sharpe beats {100 * p[v]['share_beaten']:.0f}% of the "
                       f"{p[v]['n']} placebo draws (a).", f"placebo share {v}")
        _assert_in(md, row("placebo_a_shuffle", p[v]["n"], _fmt(p[v]["mean_draw"], "x"), _fmt(p[v]["min_draw"], "x"),
                           _fmt(p[v]["max_draw"], "x")), f"placebo distribution {v}")
    for r in data["strategy_a"]["robustness"]["leave_one_out"]:
        if r["variant"] == "A1":
            _assert_in(md, row(r["event"], _fmt(r["sharpe"], "sharpe"), _fmt(r["max_drawdown"], "max_drawdown")),
                       f"leave-one-out {r['event']}")


def test_momentum_matches_its_tables(data):
    """RESULTS.md does not carry the momentum diagnostic; its tables under results/notes/ are the source."""
    import pandas as pd
    c2 = pd.read_csv(ROOT / "results" / "notes" / "strategy_a_explained" / "c2_benchmarks.csv")
    c3 = pd.read_csv(ROOT / "results" / "notes" / "strategy_a_explained" / "c3_regressions.csv")
    bm = {(r["series"], r["period"]): r for r in data["strategy_a"]["robustness"]["momentum_benchmarks"]}
    for _, r in c2.iterrows():
        assert bm[(r["series"], r["period"])]["gross_sharpe"] == pytest.approx(r["gross_sharpe"])
    rg = {(r["strategy"], r["benchmark"], r["period"]): r for r in data["strategy_a"]["robustness"]["momentum_regressions"]}
    for _, r in c3.iterrows():
        assert rg[(r["strategy"], r["benchmark"], r["period"])]["beta"] == pytest.approx(r["beta"])
    assert bm[("TSMOM 1d", "2024-2026")]["gross_sharpe"] < 0 and bm[("TSMOM 5d", "2024-2026")]["gross_sharpe"] < 0


# ------------------------------------------------------------------ strategy B checks
def test_key_month_and_without_event(data, md):
    k = data["strategy_b"]["key_month"]
    _assert_in(md, row("pm_timed", f"{100 * k['total']:.2f}", f"{100 * k['gain']:.2f}", f"{100 * k['others']:.2f}"),
               "gap decomposition")
    _assert_in(md, f"of which {100 * k['gain']:+.1f} points in the single month {k['month']}", "best month")
    _assert_in(md, f"`{k['event']}` ({k['contracts']} contract(s))", "event removed")
    for r in k["rows"]:
        _assert_in(md, row(r["strategy"], _fmt(r["sharpe"], "sharpe"), _fmt(r["ann_mean"], "ann_mean"),
                           _fmt(r["max_drawdown"], "max_drawdown")), f"D29 row {r['strategy']}")


def test_long_history_exposure_and_shocks(data, md):
    lh = data["strategy_b"]["long_history"]
    _assert_in(md, row(f"{lh['n_days']:,}", _fmt(lh["sharpe"], "sharpe"), _fmt(lh["ann_mean"], "ann_mean"),
                       _fmt(lh["ann_vol"], "ann_vol"), _fmt(lh["max_drawdown"], "max_drawdown"), _fmt(lh["skew"], "skew"),
                       _fmt(lh["excess_kurtosis"], "excess_kurtosis")), "long history")
    e = data["strategy_b"]["exposure_summary"]
    _assert_in(md, f"mean {e['mean_w']:.2f}; days with w < 1: {e['days_reduced']} of {e['n_days']}; shock days: {e['shock_days']}",
               "exposure summary")
    _assert_in(md, f"VIX timing: mean {e['vix_mean_w']:.2f}, shock days: {e['vix_shock_days']}", "VIX exposure summary")
    shocks = data["strategy_b"]["geo"]["confirmed_shocks"]
    _assert_in(md, f"{len(shocks)} confirmed", "number of confirmed shocks")
    for s in shocks:
        _assert_in(md, row(s["day"], _fmt(s["d"], "d"), _fmt(s["d_early"], "d"), f"{int(s['n_contracts']):,}"), f"shock {s['day']}")
    assert e["shock_days"] == len(shocks)


def test_composition_and_universe(data, md):
    comp = {c["currency"]: c for c in data["strategy_b"]["composition"]}
    assert set(comp) == {"BRL", "MXN", "COP", "CLP", "ZAR", "KRW"}
    primary = [u["ccy"] for u in data["strategy_b"]["universe"] if u["primary_universe"]]
    assert set(primary) == set(comp)
    for u in data["strategy_b"]["universe"]:
        _assert_in(md, row(u["ccy"], _fmt(u["irr_fine_code"], "x"), u["irr_label"], "yes" if u["primary_universe"] else "no"),
                   f"universe {u['ccy']}")


# ------------------------------------------------------------------ risk
def test_risk_tables(data, md):
    R = data["risk"]
    strategies = sorted({r["strategy"] for r in R["episodes"]})
    for ep in sorted({r["episode"] for r in R["episodes"]}):
        vals = {r["strategy"]: r["cum_return"] for r in R["episodes"] if r["episode"] == ep}
        _assert_in(md, row(ep, *[_fmt(vals[s], "cum_return") for s in strategies]), f"episode {ep}")
    for r in R["betas"]:
        _assert_in(md, row(r["strategy"], r["factor"], _fmt(r["beta"], "beta"), _fmt(r["t"], "t"), _fmt(r["corr"], "corr")),
                   f"beta {r['strategy']} {r['factor']}")
    for r in R["downside"]:
        _assert_in(md, row(r["strategy"], r["market"], _fmt(r["beta"], "beta"), _fmt(r["downside_beta"], "downside_beta"),
                           r["n_down"], _fmt(r["mean_return_down_days_bp"], "bp")), f"downside beta {r['strategy']} {r['market']}")
    for r in R["worst_drawdowns"]:
        if r["strategy"] in ("A1_theory_with_dollar", "base_carry", "pm_timed"):
            _assert_in(md, row(r["peak"], r["trough"], r["recovery"] or "ongoing", _fmt(r["depth"], "depth"),
                               f"{int(r['duration_days'])}", r["tag"]), f"worst drawdown {r['strategy']} {r['peak']}")
    hhi = {(r["strategy"], r["dimension"]): r["hhi"] for r in R["concentration"]}
    for (s, dim), h in hhi.items():
        _assert_in(md, row(s, dim, _fmt(h, "hhi")), f"concentration {s} {dim}")
    for r in R["a_vs_b"]:
        _assert_in(md, row(r["a"], _fmt(r["return_corr"], "c"), _fmt(r["weekly_return_corr"], "c"), _fmt(r["drawdown_corr"], "c")),
                   f"A vs B {r['a']}")


def test_conditional_performance(data, md):
    R = data["risk"]
    strategies = sorted({r["strategy"] for r in R["conditional"]})
    bucket_label = {("VIX tercile", "q1"): "VIX tercile: low tercile", ("VIX tercile", "q2"): "VIX tercile: middle tercile",
                    ("VIX tercile", "q3"): "VIX tercile: high tercile",
                    ("half-spread tercile", "q1"): "low spreads", ("half-spread tercile", "q2"): "middle spreads",
                    ("half-spread tercile", "q3"): "high spreads"}
    for (cond, b), label in bucket_label.items():
        vals = {r["strategy"]: r["sharpe"] for r in R["conditional"] if r["conditioner"] == cond and r["bucket"] == b}
        _assert_in(md, row(label, *[_fmt(vals[s], "sharpe") for s in strategies]), f"conditional {label}")


# ------------------------------------------------------------------ robustness
def test_robustness_b(data, md):
    Q = data["robustness"]
    p = Q["placebo_b"]
    _assert_in(md, f"**Strategy B (PM timing)**: the actual Sharpe beats {100 * p['share_beaten']:.0f}% of the {p['n']} "
                   "placebo draws (a).", "placebo share B")
    _assert_in(md, row("placebo_b_random_contracts", 1, *[_fmt(p["random_contracts"], "x")] * 3), "random contracts B")
    for r in p["leave_one_out"]:
        _assert_in(md, row(r["event"], _fmt(r["sharpe"], "sharpe"), _fmt(r["max_drawdown"], "max_drawdown")), f"B leave-one-out {r['event']}")
    for name, h in Q["posthoc"].items():
        _assert_in(md, f"**{name}**: the actual Sharpe beats {100 * h['share_beaten']:.0f}% of the {h['n']} placebo draws (a).",
                   f"posthoc placebo {name}")
    for r in Q["grid_b"]:
        _assert_in(md, row(_fmt(r["shock_k"], "k"), int(r["rerisk_days"]), _fmt(r["shock_cut"], "cut"), _fmt(r["sharpe"], "sharpe"),
                           _fmt(r["ann_mean"], "ann_mean"), _fmt(r["max_drawdown"], "max_drawdown")), f"grid {r}")
    for r in Q["cost_b"]:
        _assert_in(md, row(_fmt(r["cost_multiplier"], "m"), _fmt(r["sharpe"], "sharpe"), _fmt(r["ann_mean"], "ann_mean"),
                           _fmt(r["max_drawdown"], "max_drawdown")), f"cost sensitivity {r['cost_multiplier']}")
    chosen = Q["grid_b_chosen"]
    assert any(r["shock_k"] == chosen["shock_k"] and r["rerisk_days"] == chosen["rerisk_days"]
               and r["shock_cut"] == chosen["shock_cut"] for r in Q["grid_b"])
    sub = {(r["strategy"], r["period"]): r["sharpe"] for r in Q["subperiods"]}
    for s in ("A1_theory_with_dollar", "A2_theory_with_dollar", "base_carry", "pm_timed"):
        _assert_in(md, row(s, *[_fmt(sub[(s, y)], "sharpe") for y in ("2024", "2025", "2026")]), f"subperiods {s}")


def test_cost_a_matches_performance(data):
    perf = {(r["strategy"], r["period"]): r["sharpe"] for r in data["strategy_a"]["performance"]}
    for r in data["robustness"]["cost_a"]:
        col = {"A1": "A1_theory_with_dollar", "A2": "A2_theory_with_dollar"}[r["variant"]] + ("" if r["multiplier"] == 1 else "_cost0.5x")
        assert r["sharpe"] == perf[(col, "full")]


# ------------------------------------------------------------------ worked example of the signal chain
def test_walkthrough_follows_the_pipeline(data):
    import math
    W = data["walk"]
    m = data["meta"]
    assert W["contract"]["eligible_days"] >= 100 and W["contract"]["sign"] in (-1, 1)
    # hazard transform, as in contracts.py: -ln(1 - p) / tau, tau floored at the inclusion limit, in years
    for d, px, ttr, hz in zip(W["hazard_example"]["dates"], W["hazard_example"]["px"], W["hazard_example"]["ttr_days"], W["hazard_example"]["hazard"]):
        if px is None or hz is None:
            continue
        p = min(max(px, 0.001), 0.999)
        tau = max(ttr, m["min_days_to_resolution"]) / 365.25
        assert abs(hz - (-math.log(1 - p) / tau)) < 2e-3 * max(1.0, abs(hz)), d   # page values are rounded to 4 decimals
    # standardised change and aggregation, as in indices.py
    rows = W["contract_rows"]
    assert 10 <= len(rows) <= 12
    for r in rows:
        z = max(-m["winsor_sd"], min(m["winsor_sd"], r["sign"] * r["dv"] / r["sd"]))
        assert abs(r["z"] - z) < 1e-6, r["day"]
        assert 0 < r["weight_share"] <= 1 and abs(r["contribution"] - r["z"] * r["weight_share"]) < 1e-9
        assert abs(r["contribution"]) <= abs(r["d_vw"]) + 1e-9 or r["n_contracts"] > 1
    for a, b in zip(rows, rows[1:]):
        if (pd_days(b["day"]) - pd_days(a["day"])) == 1:
            assert abs((b["index_vw"] - a["index_vw"]) - b["d_vw"]) < 1e-6
    # Strategy A chain: y = -Z_MON - (1 - 2R) Z_FIS, and the realised USD position has the opposite sign of y
    for r in W["cell_a"]:
        assert abs(r["y"] - (-r["Z_mon"] - (1 - 2 * r["R"]) * r["Z_fis"])) < 1e-9, r["day"]
        if abs(r["y"]) > 1e-6:
            assert r["usd_position"] * r["y"] < 0, r["day"]
        if r["sd_mon"]:
            assert abs(r["Z_mon"] - r["s_mon"] / r["sd_mon"]) < 1e-6
    # the full chain of Strategy A, used by the scrolling introduction, obeys the same equation and sign relation
    c = W["chain_a"]
    assert len(c["dates"]) == data["strategy_a"]["performance"][0]["n_days"] or len(c["dates"]) >= 700
    for i in range(len(c["dates"])):
        if c["y"][i] is None:
            continue
        assert abs(c["y"][i] - (-c["Z_mon"][i] - (1 - 2 * c["R"][i]) * c["Z_fis"][i])) < 5e-3, c["dates"][i]
        if abs(c["y"][i]) > 0.01 and c["usd_position"][i] is not None and abs(c["usd_position"][i]) > 0.01:
            assert c["usd_position"][i] * c["y"][i] < 0, c["dates"][i]
    # Strategy B overlay: a confirmed shock cuts the exposure to the cut level of the month-end weight
    for r in W["geo"]:
        if r["confirmed"] and r["w"] is not None:   # strategy_b.timing_exposure: w = min(month-end weight, cut)
            assert abs(r["w"] - min(r["w_escalation"], m["shock_cut"])) < 1e-9, r["day"]
        if r["w_escalation"] is not None:
            assert r["w_escalation"] in set(m["escalation_weights"])


def pd_days(s):
    import datetime as dt
    return dt.date.fromisoformat(s).toordinal()


# ------------------------------------------------------------------ page sources and prose
def test_prose_values_have_no_em_dash_and_are_strings(data):
    from src.report.build_site import prose_values
    v = prose_values(data)
    assert len(v) > 100
    for k, s in v.items():
        assert isinstance(s, str) and s and EM_DASH not in s, k


@pytest.mark.skipif(not (SRC / "template.html").exists(), reason="page sources not written yet")
def test_page_sources_have_no_em_dash(data):
    from src.report.build_site import data_json
    for name in ("template.html", "site.css", "site.js"):
        text = (SRC / name).read_text(encoding="utf-8")
        assert EM_DASH not in text, name
    assert EM_DASH not in data_json(data)


@pytest.mark.skipif(not (SRC / "template.html").exists(), reason="page sources not written yet")
def test_rendered_page_carries_the_headline_numbers(data):
    from src.report.build_site import prose_values, render
    v = prose_values(data)
    html = render(data, v)
    for key in ("a1_net", "a1_gross", "a2_net", "a2_gross", "a2dn_net", "a1s_net", "bc_net", "pm_net", "we_net", "lh_sharpe",
                "t_mon_0", "wk_max_t", "d30_oos", "d30_mean", "cov_us_mon", "cov_glob_geo", "cov_us_fis", "pm_markets",
                "km_gain", "km_others", "beta_bc_brent_t", "corr_ab", "val_theme"):
        assert v[key] in html, f"{key} = {v[key]!r} missing from the page"
    assert "{{" not in html.split("<script")[0]
