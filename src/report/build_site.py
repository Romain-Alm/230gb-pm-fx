"""Build the self-contained interactive HTML page, deliverables/index.html (spec 11.2).

    .venv/Scripts/python.exe -m src.report.build_site

Inputs: results/site_data/ (written by site_data.py), the page sources in src/report/site/
(template.html, site.css, site.js) and the vendored Plotly basic bundle. Every number on the page
comes from the data files: the prose is formatted here, in Python (`prose_values`), and the
charts read `window.DATA` (`assemble_data`). Nothing is typed by hand. The output is one file
with everything inlined, so it opens from disk with no network.
"""
from __future__ import annotations

import datetime as dt
import inspect
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from src.backtest import metrics
from src.common import ROOT, get_logger, load_config, rpath

log = get_logger("build_site")
SITE_SRC = ROOT / "src" / "report" / "site"
PLOTLY = SITE_SRC / "vendor" / "plotly-basic-2.35.2.min.js"
EM_DASH = "\u2014"

ZONES = ["US", "EA", "JP", "UK", "CH", "AU", "NZ", "CA", "NO", "SE", "CN", "KR", "MX", "BR", "TW", "GLOBAL"]
THEMES = ["MONETARY", "INFLATION", "FISCAL_POLITICAL", "TRADE_TARIFFS", "GEOPOLITICS"]
THEME_LABEL = {"MONETARY": "Monetary", "INFLATION": "Inflation", "FISCAL_POLITICAL": "Fiscal-political",
               "TRADE_TARIFFS": "Tariffs", "GEOPOLITICS": "Geopolitics",
               "GEO_OIL": "Geopolitics, oil composite", "GEO_TRADE": "Geopolitics and trade composite"}
PERIOD_LABEL = {"full": "2024-2026", "in-sample": "2024-2025 (in-sample)", "out-of-sample": "2026 (out-of-sample)"}

# Strategy A variants shown on the page: id (column of strategy_a_returns.csv), label, status, primary.
A_VARIANTS = [
    ("A1_theory_with_dollar", "A1, primary", "pre-registered", True),
    ("A2_theory_with_dollar", "A2, all G10 cells at USD 10k", "pre-registered", False),
    ("A1+S_theory_with_dollar", "A1 + geopolitics", "pre-registered", False),
    ("A2_theory_dollar_neutral", "A2, dollar-neutral", "pre-registered", False),
    ("A1_theory_with_dollar_weekly", "A1, weekly rebalancing", "a posteriori", False),
    ("A1_theory_with_dollar_cost0.5x", "A1, costs at 0.5x", "a posteriori", False),
    ("A2_theory_with_dollar_cost0.5x", "A2, costs at 0.5x", "a posteriori", False),
    ("A1_gated20_frozen", "20-day gated rule (D30)", "exploratory", False),
]
# Variants whose gross return is that of another column (costs scenarios).
A_GROSS = {"A1_theory_with_dollar_cost0.5x": "A1_theory_with_dollar_gross",
           "A2_theory_with_dollar_cost0.5x": "A2_theory_with_dollar_gross"}
# Strategy B lines: id (column of strategy_b_returns.csv), label, status.
B_LINES = [
    ("base_carry", "EM carry, base", "pre-registered"),
    ("pm_timed", "with PM geopolitical overlay", "pre-registered"),
    ("vix_timed", "with VIX overlay", "benchmark"),
    ("pm_timed_without_event", "PM overlay without the Taiwan contract (D29)", "a posteriori"),
    ("b2_oil_tilt", "B2, oil tilt", "a posteriori"),
    ("pm_timed_min3events", "overlay with at least 3 events a day (D31)", "a posteriori"),
]
MAIN_A = ["A1_theory_with_dollar", "A2_theory_with_dollar", "A1+S_theory_with_dollar", "A1_theory_with_dollar_weekly"]
MAIN_B = ["base_carry", "pm_timed", "vix_timed", "b2_oil_tilt"]
RISK_STRATEGIES = ["A1_theory_with_dollar", "A2_theory_with_dollar", "A1+S_theory_with_dollar",
                   "base_carry", "pm_timed", "vix_timed"]
SUBPERIOD_STRATEGIES = ["A1_theory_with_dollar", "A2_theory_with_dollar", "A1_theory_with_dollar_weekly",
                        "A1_gated20_frozen", "base_carry", "pm_timed", "vix_timed", "b2_oil_tilt", "pm_timed_min3events"]
STATUS = {"A1_theory_with_dollar_weekly": "a posteriori", "A1_gated20_frozen": "exploratory",
          "b2_oil_tilt": "a posteriori", "b2_brent_tilt": "a posteriori", "pm_timed_min3events": "a posteriori",
          "pm_timed_without_event": "a posteriori", "A1_theory_with_dollar_cost0.5x": "a posteriori",
          "A2_theory_with_dollar_cost0.5x": "a posteriori", "vix_timed": "benchmark"}


# ----------------------------------------------------------------------------- helpers
def _clean(v):
    """JSON-safe scalar: NaN to None, numpy to Python, timestamps to ISO dates."""
    if v is None or v is pd.NaT:
        return None
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    if isinstance(v, (int, np.integer)):
        return int(v)
    if isinstance(v, (float, np.floating)):
        return None if np.isnan(v) else float(v)
    if isinstance(v, pd.Timestamp):
        return v.strftime("%Y-%m-%d")
    return str(v)


def _records(df: pd.DataFrame, cols: list[str] | None = None) -> list[dict]:
    df = df[cols] if cols else df
    return [{k: _clean(v) for k, v in row.items()} for row in df.to_dict("records")]


def _list(s, nd: int | None = 4) -> list:
    out = []
    for v in s:
        v = _clean(v)
        out.append(round(v, nd) if (nd is not None and isinstance(v, float)) else v)
    return out


def _dates(idx) -> list[str]:
    return [pd.Timestamp(d).strftime("%Y-%m-%d") for d in idx]


def _cum(r: pd.Series) -> pd.Series:
    """Cumulative compounded return in percent (same convention as the slide figures)."""
    return 100 * ((1 + r.fillna(0)).cumprod() - 1)


def _hist(draws: pd.Series, actual: float, bins: int = 20) -> dict:
    x = draws.dropna().to_numpy()
    lo, hi = min(x.min(), actual), max(x.max(), actual)
    counts, edges = np.histogram(x, bins=bins, range=(lo, hi))
    return {"edges": _list(edges, 4), "counts": [int(c) for c in counts], "actual": float(actual),
            "n": int(len(x)), "share_beaten": float((x < actual).mean()),
            "mean_draw": float(x.mean()), "min_draw": float(x.min()), "max_draw": float(x.max())}


def _single(df: pd.DataFrame, test: str, col: str = "sharpe"):
    s = df.loc[df["test"] == test, col]
    return float(s.iloc[0]) if len(s) else None


# ----------------------------------------------------------------------------- data
def assemble_data(cfg: dict | None = None) -> dict:
    """Everything the page's JavaScript reads, as one JSON-serialisable dict (brief section 10)."""
    cfg = cfg or load_config()
    S = rpath("results", cfg) / "site_data"

    def rd(name, **kw):
        return pd.read_csv(S / name, **kw)

    smp = cfg["sample"]
    start, end = smp["start"], smp["end"]

    # --- meta: sample, protocol and the rule parameters quoted in the prose (all from config)
    boot = inspect.signature(metrics.sharpe_block_bootstrap).parameters
    sa, sb, sm, pi = cfg["strategy_a"], cfg["strategy_b"], cfg["smoothing"], cfg["pm_inclusion"]
    meta = {
        "built": dt.date.today().isoformat(), "sample_start": start, "sample_end": end,
        "train_end": smp["train_end"], "oos_start": smp["test_start"],
        "bootstrap_block": boot["block"].default, "bootstrap_draws": boot["n_draws"].default,
        "bootstrap_level": boot["level"].default,
        "snapshot_time": cfg["snapshot"]["time"], "snapshot_tz": cfg["snapshot"]["timezone"],
        "stale_hours": cfg["snapshot"]["stale_hours"],
        "min_volume_7d_usd": pi["min_volume_7d_usd"], "volume_grid": pi["min_volume_7d_usd_grid"],
        "min_days_to_resolution": pi["min_days_to_resolution"], "max_days_to_resolution": pi["max_days_to_resolution"],
        "coverage_gate": cfg["coverage"]["min_share_days_covered_train"],
        "vol_ewma_span": cfg["theme_index"]["vol_ewma_span_days"], "winsor_sd": cfg["theme_index"]["winsor_sd"],
        "halflife": sm["ewma_halflife_days"], "halflife_grid": sm["ewma_halflife_grid"],
        "geo_halflife": sm["geo_escalation_halflife_days"], "geo_burnin": sm["geo_escalation_burnin_days"],
        "shock_k": sm["geo_shock_k"], "shock_k_grid": sm["geo_shock_k_grid"],
        "shock_persist_hours": sm["shock_persist_hours"],
        "shock_cut": sb["shock_cut_level"], "shock_cut_grid": sb["shock_cut_grid"],
        "rerisk_days": sb["rerisk_days"], "rerisk_grid": sb["rerisk_grid"],
        "escalation_z_cuts": sb["escalation_z_cuts"], "escalation_weights": sb["escalation_weights"],
        "vol_target": sa["vol_target_annual"], "gross_cap": sa["gross_leverage_cap"],
        "pair_cap": sa["single_pair_cap_share"], "no_trade_band": sa["no_trade_band"], "gate_abs_t": sa["gate_abs_t"],
        "pairs": sa["pairs"], "cost_sensitivity": cfg["costs"]["sensitivity"],
        "half_spread_days": cfg["costs"]["half_spread_median_days"],
        "oil_exporters": sb["oil_exporters"], "oil_importers": sb["oil_importers"],
        "min_events_robustness": sb["min_events_robustness"],
    }

    # --- prediction-market data
    pm = rd("pm_summary.csv")
    pm_summary = {"rows": _records(pm), "markets": int(pm["markets"].sum()),
                  "market_days": int(pm["market_days"].sum()), "volume_usd_bn": float(pm["volume_usd_bn"].sum())}
    cs = rd("classification_summary.csv")
    by_theme = (cs.groupby("theme")[["markets", "events", "usable"]].sum().reset_index()
                .sort_values("markets", ascending=False))
    ex = rd("classification_examples.csv")
    ex["zones"] = ex["zones"].fillna("")
    classification = {"summary": _records(cs), "by_theme": _records(by_theme),
                      "examples": _records(ex, ["platform", "title", "theme", "zones", "direction", "partition",
                                                "theme_rule", "direction_rule"])}
    # hand validation of the rules (blind labels), written by src.pm.validation score
    vs = pd.read_csv(ROOT / "ai_log" / "classification" / "validation_scores.csv")
    classification["validation"] = {"n": int(vs["n_labelled"].iloc[0]),
                                    "theme_accuracy": float(vs["theme_accuracy"].iloc[0])}

    # --- coverage
    cov, cov10 = rd("coverage_cells.csv"), rd("coverage_cells_v10k.csv")
    coverage = {"zones": ZONES, "themes": THEMES, "theme_labels": THEME_LABEL, "gate": meta["coverage_gate"],
                "cells": _records(cov), "cells_10k": _records(cov10),
                "n_kept": int(cov["keep"].sum()), "n_kept_10k": int(cov10["keep"].sum())}

    # --- signals: theme indices of the cells with some coverage, plus the two composites of A+S
    ti = rd("theme_indices.csv", parse_dates=["day"])
    ti = ti[(ti["day"] >= start) & (ti["day"] <= end)]
    sel = cov[(cov["share_train"] > 0.05) | (cov["share_test"] > 0.05)].sort_values("share_train", ascending=False)
    cell_keys = [(z, t) for z, t in zip(sel["zone"], sel["theme"])] + [("GLOBAL", "GEO_TRADE"), ("GLOBAL", "GEO_OIL")]
    days = pd.DatetimeIndex(sorted(ti["day"].unique()))
    kept = {(z, t) for z, t, k in zip(cov["zone"], cov["theme"], cov["keep"]) if k}
    cells = {}
    for z, t in cell_keys:
        sub = ti[(ti["zone"] == z) & (ti["theme"] == t)].set_index("day").reindex(days)
        if sub["index_vw"].notna().sum() == 0:
            continue
        row = cov[(cov["zone"] == z) & (cov["theme"] == t)]
        cells[f"{z}/{t}"] = {"zone": z, "theme": t, "label": f"{z} / {THEME_LABEL.get(t, t)}", "kept": (z, t) in kept,
                             "share_train": float(row["share_train"].iloc[0]) if len(row) else None,
                             "share_test": float(row["share_test"].iloc[0]) if len(row) else None,
                             "index_vw": _list(sub["index_vw"], 3), "index_ew": _list(sub["index_ew"], 3),
                             "n_contracts": [None if pd.isna(v) else int(v) for v in sub["n_contracts"]]}
    signals = {"dates": _dates(days), "cells": cells, "order": [k for k in (f"{z}/{t}" for z, t in cell_keys) if k in cells]}
    annotations = json.loads((S / "annotations.json").read_text(encoding="utf-8"))

    # --- timing: panel t-statistics, hourly lead-lag, weekend gap
    ts = rd("strategy_a_tstats.csv")
    ll = rd("slide_leadlag.csv")
    wk = rd("strategy_a_weekend_gap.csv")
    main_wk = wk[wk["model"].str.startswith("A1+GEO_weekend_gap")]
    timing = {"tstats": _records(ts, ["regressor", "horizon", "model", "coef", "se", "t", "p", "n_obs"]),
              "leadlag": {"studies": list(ll["study"].unique()), "rows": _records(ll)},
              "weekend": {"n_pair_weekends": int(wk.loc[wk["model"] == "A1+GEO_weekend_gap_london", "n_obs"].iloc[0]),
                          "max_abs_t": float(main_wk["t"].abs().max()),
                          "rows": _records(wk[~wk["model"].str.contains("NOT_A_GAP_TEST")],
                                           ["model", "regressor", "coef", "se", "t", "p", "n_obs"])}}

    # --- strategy A
    ra = rd("strategy_a_returns.csv", index_col="date", parse_dates=True).loc[start:end]
    perf_a = rd("strategy_a_performance.csv")
    a_ids = [v[0] for v in A_VARIANTS]
    a_gross = {v: A_GROSS.get(v, v + "_gross") for v in a_ids}
    perf_cols = ["strategy", "period", "n_days", "cum_return", "ann_mean", "ann_vol", "sharpe", "sortino", "max_drawdown",
                 "hit_rate", "skew", "sharpe_t", "sharpe_ci90_low", "sharpe_ci90_high", "turnover_ann", "cost_drag_ann"]
    rob_a = rd("robustness_a.csv")
    rob_a["dollar_neutral"] = rob_a["dollar_neutral"].astype(bool)
    placebo_a = {}
    for v in ("A1", "A2", "A1+S"):
        sub = rob_a[(rob_a["variant"] == v) & (~rob_a["dollar_neutral"])]
        h = _hist(sub.loc[sub["test"] == "placebo_a_shuffle", "sharpe"], _single(sub, "actual"))
        h.update({"random_contracts": _single(sub, "placebo_b_random_contracts"),
                  "reversed": _single(sub, "placebo_c_reversed"), "equal_weights": _single(sub, "equal_weights")})
        placebo_a[v] = h
    loo = rob_a[(rob_a["test"] == "leave_one_event_out") & (~rob_a["dollar_neutral"])]
    hl = rob_a[(rob_a["test"] == "halflife") & (~rob_a["dollar_neutral"])]
    gate = rd("gate_estimation.csv")
    gate = gate[gate["variant"].isin(["A1", "A2"])]   # the rule's own variants, as in RESULTS.md
    ph = rd("d30_phase.csv")
    phase_summary = []
    for col, label in (("sharpe_2024-2025", "in-sample"), ("sharpe_2026", "out-of-sample"), ("sharpe_2024-2026", "full")):
        pub = float(ph.loc[ph["offset"] == 0, col].iloc[0])
        phase_summary.append({"period": label, "published": pub, "mean": float(ph[col].mean()), "min": float(ph[col].min()),
                              "max": float(ph[col].max()), "n_positive": int((ph[col] > 0).sum()), "n": int(len(ph)),
                              "rank": int((ph[col] > pub).sum() + 1)})
    eff = rd("d30_effective_sample.csv")
    reg = rd("fiscal_regime_days.csv")
    strategy_a = {
        "dates": _dates(ra.index),
        "variants": [{"id": i, "label": l, "status": s, "primary": p} for i, l, s, p in A_VARIANTS],
        "cum_net": {v: _list(_cum(ra[v]), 3) for v in a_ids},
        "cum_gross": {v: _list(_cum(ra[a_gross[v]]), 3) for v in a_ids},
        "drawdown": {v: _list(100 * metrics.drawdown(ra[v]), 3) for v in a_ids},
        "performance": _records(perf_a[perf_a["strategy"].isin(a_ids + list(a_gross.values()))], perf_cols),
        "gross_of": a_gross,
        "fiscal_regime_days": _records(reg),
        "robustness": {
            "placebo": placebo_a,
            "leave_one_out": _records(loo, ["variant", "event", "sharpe", "max_drawdown"]),
            "halflife": _records(hl, ["variant", "halflife", "sharpe", "max_drawdown", "ann_mean"]),
            "static_timing": _records(rd("decomposition_static_timing.csv").query("part != 'static_position'"),
                                      ["strategy", "part", "period", "sharpe", "sharpe_t", "ann_mean", "ann_vol"]),
            "momentum_benchmarks": _records(rd("momentum_benchmarks.csv")),
            "momentum_regressions": _records(rd("momentum_regressions.csv"),
                                             ["strategy", "benchmark", "period", "n", "beta", "t_beta", "alpha_ann", "t_alpha", "corr"]),
            "gate": {"rows": _records(gate, ["variant", "regressor", "coef", "t", "n_obs", "passes_gate"]),
                     "largest_t": float(gate["t"].max()), "n_pass": int(gate["passes_gate"].sum())}},
        "d30": {"phase": _records(ph), "summary": phase_summary,
                "effective_sample": _records(eff),
                "monthly_2026": _records(rd("d30_monthly_2026.csv")),
                "decomposition": _records(rd("d30_decomposition.csv")),
                "positions": _records(rd("d30_positions.csv"))},
    }

    # --- strategy B
    rb = rd("strategy_b_returns.csv", index_col="date", parse_dates=True).loc[start:end]
    rb = rb.join(rd("strategy_b_returns_without_event.csv", index_col="date", parse_dates=True))
    b_ids = [b[0] for b in B_LINES]
    perf_b = rd("strategy_b_performance.csv")
    expo = rd("strategy_b_exposure.csv", index_col="date", parse_dates=True).reindex(rb.index)
    geo = rd("geo_signals.csv", parse_dates=["day"])
    geo = geo[(geo["day"] >= start) & (geo["day"] <= end)]
    km = rd("key_month_check.csv")
    lh = rd("base_carry_long_history.csv").iloc[0]
    lhr = rd("base_carry_long_history_returns.csv", index_col="date", parse_dates=True).iloc[:, 0]
    comp = rd("slide_b_composition.csv")
    strategy_b = {
        "dates": _dates(rb.index),
        "lines": [{"id": i, "label": l, "status": s} for i, l, s in B_LINES],
        "cum_net": {v: _list(_cum(rb[v]), 3) for v in b_ids},
        "cum_gross": {v: (_list(_cum(rb[v + "_gross"]), 3) if v + "_gross" in rb.columns else None) for v in b_ids},
        "drawdown": {v: _list(100 * metrics.drawdown(rb[v]), 3) for v in b_ids},
        "performance": _records(perf_b[perf_b["strategy"].isin(b_ids + [v + "_gross" for v in b_ids] + ["b2_brent_tilt"])],
                                perf_cols),
        "exposure": {"w": _list(expo["w"], 4), "w_escalation": _list(expo["w_escalation"], 4),
                     "shock": [bool(x) for x in expo["shock"].fillna(False)],
                     "w_vix": _list(expo["w_vix"], 4), "shock_vix": [bool(x) for x in expo["shock_vix"].fillna(False)]},
        "exposure_summary": {"mean_w": float(expo["w"].mean()), "days_reduced": int((expo["w"] < 1).sum()),
                             "n_days": int(expo["w"].notna().sum()), "shock_days": int(expo["shock"].sum()),
                             "vix_mean_w": float(expo["w_vix"].mean()), "vix_shock_days": int(expo["shock_vix"].sum())},
        "geo": {"dates": _dates(geo["day"]), "index": _list(geo["index"], 3), "escalation_z": _list(geo["escalation_z"], 3),
                "n_contracts": [None if pd.isna(v) else int(v) for v in geo["n_contracts"]],
                "confirmed_shocks": _records(rd("confirmed_shocks.csv"))},
        "key_month": {"month": str(km["best_month"].iloc[0]), "gain": float(km["best_month_gain"].iloc[0]),
                      "total": float(km["total_gain"].iloc[0]),
                      "others": float(km["total_gain"].iloc[0] - km["best_month_gain"].iloc[0]),
                      "event": str(km["event_removed"].iloc[0]), "contracts": int(km["event_contracts"].iloc[0]),
                      "rows": _records(km, ["strategy", "sharpe", "ann_mean", "max_drawdown"])},
        "long_history": {"n_days": int(lh["n_days"]), "years": float(lh["n_days"] / 252), "sharpe": float(lh["sharpe"]),
                         "ann_mean": float(lh["ann_mean"]), "ann_vol": float(lh["ann_vol"]),
                         "max_drawdown": float(lh["max_drawdown"]), "skew": float(lh["skew"]),
                         "excess_kurtosis": float(lh["excess_kurtosis"]), "start": _dates(lhr.index[:1])[0],
                         "cum": {"dates": _dates(lhr.index), "values": _list(_cum(lhr), 2)}},
        "composition": _records(comp),
        "universe": _records(rd("em_universe.csv")),
    }

    # --- risk
    ep = rd("risk_episodes.csv")
    bt = rd("risk_betas.csv")
    db = rd("risk_downside_beta.csv")
    wd = rd("risk_worst_drawdowns.csv")
    wd = wd[wd["strategy"].isin(RISK_STRATEGIES)].sort_values("depth").groupby("strategy").head(5)
    for c in ("peak", "trough", "recovery"):
        wd[c] = pd.to_datetime(wd[c]).dt.strftime("%Y-%m-%d")
    cc = rd("risk_concentration.csv")
    cd = rd("risk_conditional.csv")
    lv = rd("risk_leverage.csv")
    ab = rd("a_vs_b_correlation.csv")
    risk = {
        "episodes": _records(ep[ep["strategy"].isin(RISK_STRATEGIES)]),
        "betas": _records(bt[bt["strategy"].isin(RISK_STRATEGIES)]),
        "downside": _records(db[db["strategy"].isin(RISK_STRATEGIES)]),
        "worst_drawdowns": _records(wd, ["strategy", "peak", "trough", "recovery", "depth", "days_to_trough", "duration_days", "tag"]),
        "concentration": _records(cc[cc["strategy"].isin(RISK_STRATEGIES)]),
        "conditional": _records(cd[cd["strategy"].isin(RISK_STRATEGIES)]),
        "leverage": _records(lv[lv["strategy"].isin(RISK_STRATEGIES)]),
        "a_vs_b": _records(ab[ab["a"].isin(["A1_theory_with_dollar", "A1+S_theory_with_dollar", "A2_theory_with_dollar",
                                            "A2+S_theory_with_dollar"])]),
    }

    # --- robustness
    rob_b = rd("robustness_b.csv")
    hb = _hist(rob_b.loc[rob_b["test"] == "placebo_a_shuffle", "sharpe"], _single(rob_b, "actual"))
    hb.update({"base_carry": _single(rob_b, "base_carry"), "random_contracts": _single(rob_b, "placebo_b_random_contracts"),
               "reversed": _single(rob_b, "placebo_c_reversed"), "equal_weights": _single(rob_b, "equal_weights"),
               "volume_threshold": _records(rob_b[rob_b["test"] == "volume_threshold"], ["threshold", "sharpe", "max_drawdown"]),
               "leave_one_out": _records(rob_b[rob_b["test"] == "leave_one_event_out"], ["event", "sharpe", "max_drawdown"])})
    post = rd("robustness_posthoc.csv")
    posthoc = {}
    for name in post["strategy"].unique():
        sub = post[post["strategy"] == name]
        h = _hist(sub.loc[sub["test"] == "placebo_a_shuffle", "sharpe"], _single(sub, "actual"))
        h.update({"random_contracts": _single(sub, "placebo_b_random_contracts"), "reversed": _single(sub, "placebo_c_reversed"),
                  "status": STATUS.get(name, "a posteriori")})
        posthoc[name] = h
    full_a = perf_a[perf_a["period"] == "full"].set_index("strategy")["sharpe"]
    sp = rd("subperiods.csv")
    sp["period"] = sp["period"].astype(str)
    robustness = {
        "placebo_b": hb, "posthoc": posthoc,
        "grid_b": _records(rd("robustness_grid_b.csv"), ["shock_k", "rerisk_days", "shock_cut", "sharpe", "ann_mean", "max_drawdown"]),
        "grid_b_chosen": {"shock_k": meta["shock_k"], "rerisk_days": meta["rerisk_days"], "shock_cut": meta["shock_cut"]},
        "cost_b": _records(rd("cost_sensitivity_b.csv"), ["cost_multiplier", "sharpe", "ann_mean", "max_drawdown"]),
        "cost_a": [{"variant": v, "multiplier": m, "sharpe": float(full_a[c])}
                   for v, m, c in (("A1", 1.0, "A1_theory_with_dollar"), ("A1", 0.5, "A1_theory_with_dollar_cost0.5x"),
                                   ("A2", 1.0, "A2_theory_with_dollar"), ("A2", 0.5, "A2_theory_with_dollar_cost0.5x"))],
        "subperiods": _records(sp[sp["strategy"].isin(SUBPERIOD_STRATEGIES)], ["strategy", "period", "sharpe", "ann_mean", "max_drawdown"]),
    }

    # --- worked example of the signal chain
    hz = rd("hazard_example.csv")
    ca = rd("signal_chain_a.csv")
    walk = {"contract": _records(rd("walk_contract_info.csv"))[0],
            "hazard_example": {"dates": list(hz["day"]), "px": _list(hz["px"], 4), "ttr_days": _list(hz["ttr_days"], 2),
                               "hazard": _list(hz["hazard_per_year"], 4), "eligible": [bool(x) for x in hz["eligible"]],
                               "z": _list(hz["z"], 3), "dv": _list(hz["dv"], 4), "sd": _list(hz["sd"], 4)},
            "chain_a": {"dates": list(ca["day"]), "Z_mon": _list(ca["Z_mon"], 3), "Z_fis": _list(ca["Z_fis"], 3),
                        "R": _list(ca["R"], 0), "y": _list(ca["y"], 3), "usd_position": _list(ca["usd_position"], 3)},
            "contract_rows": _records(rd("walk_contract.csv")),
            "cell_a": _records(rd("walk_cell_a.csv")),
            "geo": _records(rd("walk_geo.csv"))}

    return {"meta": meta, "pm_summary": pm_summary, "classification": classification, "coverage": coverage,
            "signals": signals, "annotations": annotations, "timing": timing, "strategy_a": strategy_a,
            "strategy_b": strategy_b, "risk": risk, "robustness": robustness, "walk": walk,
            "labels": {"period": PERIOD_LABEL, "status": STATUS, "theme": THEME_LABEL}}


# ----------------------------------------------------------------------------- prose
def _perf(data: dict, strat: str, period: str = "full", key: str = "strategy_a") -> dict:
    for r in data[key]["performance"]:
        if r["strategy"] == strat and r["period"] == period:
            return r
    raise KeyError(f"{strat} / {period}")


def _f2(v):
    return f"{v:.2f}"


def _f1(v):
    return f"{v:.1f}"


def _pct(v, nd=1):
    return f"{100 * v:.{nd}f}%"


def _sign_pts(v):
    return f"{100 * v:+.1f}"


def prose_values(data: dict) -> dict[str, str]:
    """Every number quoted in the page's prose, formatted once here (brief section 5)."""
    m, cov, ti = data["meta"], data["coverage"], data["timing"]
    A, B, R, Q = data["strategy_a"], data["strategy_b"], data["risk"], data["robustness"]
    cells = {(c["zone"], c["theme"]): c for c in cov["cells"]}
    cells10 = {(c["zone"], c["theme"]): c for c in cov["cells_10k"]}
    t = {(r["model"], r["regressor"], r["horizon"]): r["t"] for r in ti["tstats"]}
    pa = lambda s, p="full": _perf(data, s, p, "strategy_a")   # noqa: E731
    pb = lambda s, p="full": _perf(data, s, p, "strategy_b")   # noqa: E731
    a1, a1g, a2, a2g = pa("A1_theory_with_dollar"), pa("A1_theory_with_dollar_gross"), pa("A2_theory_with_dollar"), pa("A2_theory_with_dollar_gross")
    a2dn, a1s = pa("A2_theory_dollar_neutral"), pa("A1+S_theory_with_dollar")
    a1w, a1c, a2c, d30 = pa("A1_theory_with_dollar_weekly"), pa("A1_theory_with_dollar_cost0.5x"), pa("A2_theory_with_dollar_cost0.5x"), pa("A1_gated20_frozen")
    bc, pmt, vix, b2, m3 = pb("base_carry"), pb("pm_timed"), pb("vix_timed"), pb("b2_oil_tilt"), pb("pm_timed_min3events")
    km, lh, es, ex = B["key_month"], B["long_history"], B["exposure_summary"], B["exposure"]
    ph26 = next(s for s in A["d30"]["summary"] if s["period"] == "out-of-sample")
    eff26 = next(r for r in A["d30"]["effective_sample"] if r["period"] == "2026" and r["offset"] == 0)
    st = {(r["strategy"], r["part"], r["period"]): r for r in A["robustness"]["static_timing"]}
    loo_a1 = [r["sharpe"] for r in A["robustness"]["leave_one_out"] if r["variant"] == "A1"]
    mom = {(r["series"], r["period"]): r for r in A["robustness"]["momentum_benchmarks"]}
    momr = {(r["strategy"], r["benchmark"], r["period"]): r for r in A["robustness"]["momentum_regressions"]}
    beta = {(r["strategy"], r["factor"]): r for r in R["betas"]}
    down = {(r["strategy"], r["market"]): r for r in R["downside"]}
    epis = {(r["episode"], r["strategy"]): r for r in R["episodes"]}
    conc = {(r["strategy"], r["dimension"], r["key"]): r for r in R["concentration"]}
    cond = {(r["strategy"], r["conditioner"], r["bucket"]): r for r in R["conditional"]}
    lev = {(r["strategy"], r["period"]): r for r in R["leverage"]}
    ab = next(r for r in R["a_vs_b"] if r["a"] == "A1_theory_with_dollar")
    reg25 = next(r for r in A["fiscal_regime_days"] if r["zone"] == "US" and r["year"] == 2025)
    reg_other = [r for r in A["fiscal_regime_days"] if r["zone"] == "US" and r["year"] in (2024, 2026)]
    wdd = {}
    for r in R["worst_drawdowns"]:   # deepest episode per strategy
        if r["strategy"] in ("A1_theory_with_dollar", "base_carry") and r["depth"] < wdd.get(r["strategy"], {"depth": 0})["depth"]:
            wdd[r["strategy"]] = r
    comp = {c["currency"]: c for c in B["composition"]}
    shocks = B["geo"]["confirmed_shocks"]
    cost_b = {r["cost_multiplier"]: r for r in Q["cost_b"]}
    n_years = a1["n_days"] / 252

    v = {
        # sample and protocol
        "sample_start": m["sample_start"], "sample_end": m["sample_end"], "oos_start": m["oos_start"], "built": m["built"],
        "n_days": f"{a1['n_days']:,}", "n_years": _f1(n_years),
        "boot_block": str(m["bootstrap_block"]), "boot_draws": f"{m['bootstrap_draws']:,}",
        "boot_level": f"{100 * m['bootstrap_level']:.0f}",
        # data
        "pm_markets": f"{data['pm_summary']['markets']:,}", "pm_volume_bn": _f1(data["pm_summary"]["volume_usd_bn"]),
        "pm_kalshi": f"{next(r['markets'] for r in data['pm_summary']['rows'] if r['platform'] == 'kalshi'):,}",
        "pm_polymarket": f"{next(r['markets'] for r in data['pm_summary']['rows'] if r['platform'] == 'polymarket'):,}",
        "pm_kalshi_bn": _f2(next(r["volume_usd_bn"] for r in data["pm_summary"]["rows"] if r["platform"] == "kalshi")),
        "pm_polymarket_bn": _f2(next(r["volume_usd_bn"] for r in data["pm_summary"]["rows"] if r["platform"] == "polymarket")),
        "min_volume_k": f"{m['min_volume_7d_usd'] // 1000}", "stale_hours": str(m["stale_hours"]),
        "min_days": str(m["min_days_to_resolution"]), "max_days": str(m["max_days_to_resolution"]),
        "snapshot_time": m["snapshot_time"], "vol_span": str(m["vol_ewma_span"]), "winsor": f"{m['winsor_sd']:.0f}",
        "val_n": str(data["classification"]["validation"]["n"]),
        "val_theme": f"{100 * data['classification']['validation']['theme_accuracy']:.0f}",
        # coverage
        "gate_pct": f"{100 * cov['gate']:.0f}", "n_kept": str(cov["n_kept"]), "n_kept_10k": str(cov["n_kept_10k"]),
        "cov_us_mon": _pct(cells[("US", "MONETARY")]["share_train"]),
        "cov_glob_geo": _pct(cells[("GLOBAL", "GEOPOLITICS")]["share_train"]),
        "cov_us_fis": _pct(cells[("US", "FISCAL_POLITICAL")]["share_train"]),
        "cov_us_geo": _pct(cells[("US", "GEOPOLITICS")]["share_train"]),
        "cov_uk_fis_26": _pct(cells[("UK", "FISCAL_POLITICAL")]["share_test"]),
        "cov_jp_mon_26": _pct(cells[("JP", "MONETARY")]["share_test"]),
        "cov_us_tar_26": _pct(cells[("US", "TRADE_TARIFFS")]["share_test"]),
        "cov_ea_fis_26": _pct(cells[("EA", "FISCAL_POLITICAL")]["share_test"]),
        "cov_uk_fis": _pct(cells[("UK", "FISCAL_POLITICAL")]["share_train"]),
        "cov_jp_mon": _pct(cells[("JP", "MONETARY")]["share_train"]),
        "gate_low": f"{100 * cells[('US', 'GEOPOLITICS')]['share_train']:.0f}",
        "gate_high": f"{100 * cells[('US', 'FISCAL_POLITICAL')]['share_train']:.0f}",
        "cov10_cn_geo": _pct(cells10[("CN", "GEOPOLITICS")]["share_train"]),
        "cov10_us_geo": _pct(cells10[("US", "GEOPOLITICS")]["share_train"]),
        # timing
        "t_mon_0": _f2(t[("A1_contemporaneous", "MONETARY", 0)]), "t_fis_0": _f2(t[("A1_contemporaneous", "FISCAL_POLITICAL", 0)]),
        "t_mon_1": _f2(t[("A1_predictive", "MONETARY", 1)]), "t_fis_1": _f2(t[("A1_predictive", "FISCAL_POLITICAL", 1)]),
        "t_mon_5": _f2(t[("A1_predictive", "MONETARY", 5)]), "t_fis_5": _f2(t[("A1_predictive", "FISCAL_POLITICAL", 5)]),
        "t_mon_20": _f2(t[("A1_predictive", "MONETARY", 20)]), "t_fis_20": _f2(t[("A1_predictive", "FISCAL_POLITICAL", 20)]),
        "t_mon_0_1": _f1(t[("A1_contemporaneous", "MONETARY", 0)]),
        "wk_n": f"{ti['weekend']['n_pair_weekends']:,}", "wk_max_t": _f1(ti["weekend"]["max_abs_t"]),
        # strategy A
        "a1_net": _f2(a1["sharpe"]), "a1_gross": _f2(a1g["sharpe"]), "a1_t": _f2(a1["sharpe_t"]),
        "a1_ci_lo": _f2(a1["sharpe_ci90_low"]), "a1_ci_hi": _f2(a1["sharpe_ci90_high"]),
        "a1g_ci_lo": _f2(a1g["sharpe_ci90_low"]), "a1g_ci_hi": _f2(a1g["sharpe_ci90_high"]),
        "a2_net": _f2(a2["sharpe"]), "a2_gross": _f2(a2g["sharpe"]), "a2g_t": _f1(a2g["sharpe_t"]),
        "a2g_ci_lo": _f2(a2g["sharpe_ci90_low"]), "a2g_ci_hi": _f2(a2g["sharpe_ci90_high"]),
        "a2dn_net": _f2(a2dn["sharpe"]), "a1s_net": _f2(a1s["sharpe"]),
        "a1_turnover": f"{a1['turnover_ann']:.0f}", "a1_cost": _pct(a1["cost_drag_ann"]),
        "a1_bp_earned": _f1(1e4 * a1g["ann_mean"] / a1["turnover_ann"]), "a1_bp_paid": _f1(1e4 * a1["cost_drag_ann"] / a1["turnover_ann"]),
        "a1_oos_net": _f2(pa("A1_theory_with_dollar", "out-of-sample")["sharpe"]),
        "a1_oos_gross": _f2(pa("A1_theory_with_dollar_gross", "out-of-sample")["sharpe"]),
        "a2_oos_net": _f2(pa("A2_theory_with_dollar", "out-of-sample")["sharpe"]),
        "a1_is_net": _f2(pa("A1_theory_with_dollar", "in-sample")["sharpe"]),
        "a1_dd": _pct(a1["max_drawdown"]), "a1_vol": _pct(a1["ann_vol"]), "a1_ret": _pct(a1["ann_mean"]),
        "a1w_net": _f2(a1w["sharpe"]), "a1w_turnover": f"{a1w['turnover_ann']:.0f}",
        "a1c_net": _f2(a1c["sharpe"]), "a2c_net": _f2(a2c["sharpe"]),
        "d30_full": _f2(d30["sharpe"]), "d30_oos": _f2(pa("A1_gated20_frozen", "out-of-sample")["sharpe"]),
        "d30_mean": _f2(ph26["mean"]), "d30_npos": str(ph26["n_positive"]), "d30_n": str(ph26["n"]), "d30_rank": str(ph26["rank"]),
        "d30_eff_t": _f2(eff26["t"]), "d30_eff_n": str(eff26["n"]),
        "placebo_a1": f"{100 * A['robustness']['placebo']['A1']['share_beaten']:.0f}",
        "placebo_a2": f"{100 * A['robustness']['placebo']['A2']['share_beaten']:.0f}",
        "loo_a1_min": _f2(min(loo_a1)), "loo_a1_max": _f2(max(loo_a1)), "loo_n": str(len(loo_a1)),
        "static_a1": _f2(st[("A1_theory_with_dollar", "static", "full")]["sharpe"]),
        "timing_a1": _f2(st[("A1_theory_with_dollar", "timing", "full")]["sharpe"]),
        "mom1": _f2(mom[("TSMOM 1d", "2024-2026")]["gross_sharpe"]), "mom5": _f2(mom[("TSMOM 5d", "2024-2026")]["gross_sharpe"]),
        "mom5_beta": _f2(momr[("A1", "TSMOM 5d", "2024-2026")]["beta"]), "mom5_t": _f1(momr[("A1", "TSMOM 5d", "2024-2026")]["t_beta"]),
        "mom5_alpha": _pct(momr[("A1", "TSMOM 5d", "2024-2026")]["alpha_ann"], 0), "mom5_alpha_t": _f1(momr[("A1", "TSMOM 5d", "2024-2026")]["t_alpha"]),
        "gate_largest_t": _f2(A["robustness"]["gate"]["largest_t"]), "gate_abs_t": f"{m['gate_abs_t']:.0f}",
        "regime_days_25": str(reg25["days_in_regime"]), "regime_share_25": _pct(reg25["share"]),
        "regime_days_other": str(sum(r["days_in_regime"] for r in reg_other)),
        "halflife": str(m["halflife"]), "vol_target": f"{100 * m['vol_target']:.0f}", "gross_cap": f"{m['gross_cap']:.0f}",
        "pair_cap": f"{100 * m['pair_cap']:.0f}", "n_pairs": str(len(m["pairs"])), "half_spread_days": str(m["half_spread_days"]),
        # strategy B
        "bc_net": _f2(bc["sharpe"]), "bc_t": _f2(bc["sharpe_t"]), "bc_ci_lo": _f2(bc["sharpe_ci90_low"]), "bc_ci_hi": _f2(bc["sharpe_ci90_high"]),
        "bc_oos": _f2(pb("base_carry", "out-of-sample")["sharpe"]), "bc_cost": _pct(bc["cost_drag_ann"]), "bc_dd": _pct(bc["max_drawdown"]),
        "pm_net": _f2(pmt["sharpe"]), "pm_dd": _pct(pmt["max_drawdown"]), "vix_net": _f2(vix["sharpe"]), "vix_dd": _pct(vix["max_drawdown"]),
        "b2_net": _f2(b2["sharpe"]), "m3_net": _f2(m3["sharpe"]),
        "km_month": km["month"], "km_gain": _sign_pts(km["gain"]), "km_others": _sign_pts(km["others"]), "km_total": _sign_pts(km["total"]),
        "km_event": km["event"], "km_contracts": str(km["contracts"]),
        "we_net": _f2(next(r["sharpe"] for r in km["rows"] if r["strategy"] == "pm_timed_without_event")),
        "we_dd": _pct(next(r["max_drawdown"] for r in km["rows"] if r["strategy"] == "pm_timed_without_event")),
        "lh_sharpe": _f2(lh["sharpe"]), "lh_dd": _pct(lh["max_drawdown"]), "lh_kurt": _f1(lh["excess_kurtosis"]),
        "lh_years": f"{lh['years']:.0f}", "lh_start": lh["start"][:4],
        "expo_mean": _f2(es["mean_w"]), "expo_reduced": str(es["days_reduced"]), "expo_n": str(es["n_days"]),
        "n_shocks": str(len(shocks)), "shock_contracts_max": str(int(max(s["n_contracts"] for s in shocks))),
        "shock_contracts_late24": ", ".join(str(int(s["n_contracts"])) for s in shocks if s["day"] < "2025-01-01"),
        "geo_halflife": str(m["geo_halflife"]), "shock_k": f"{m['shock_k']:.0f}", "shock_cut": f"{100 * m['shock_cut']:.0f}",
        "rerisk_days": str(m["rerisk_days"]),
        "comp_cop": f"{100 * comp['COP']['average_weight']:+.0f}", "comp_brl": f"{100 * comp['BRL']['average_weight']:+.0f}",
        "comp_mxn": f"{100 * comp['MXN']['average_weight']:+.0f}", "comp_zar": f"{100 * comp['ZAR']['average_weight']:.0f}",
        "comp_clp": f"{100 * comp['CLP']['average_weight']:+.0f}", "comp_krw": f"{100 * comp['KRW']['average_weight']:+.0f}",
        "beta_bc_brent": _f2(beta[("base_carry", "brent")]["beta"]), "beta_bc_brent_t": _f1(beta[("base_carry", "brent")]["t"]),
        "beta_bc_msci": _f2(beta[("base_carry", "msci_world")]["beta"]),
        "ep_iran_bc": _pct(epis[("Iran war (Feb-Apr 2026)", "base_carry")]["cum_return"]),
        "ep_iran_pm": _pct(epis[("Iran war (Feb-Apr 2026)", "pm_timed")]["cum_return"]),
        "ep_iran_a1": _pct(epis[("Iran war (Feb-Apr 2026)", "A1_theory_with_dollar")]["cum_return"]),
        "ep_yen_bc": _pct(epis[("Yen carry unwind (Aug 2024)", "base_carry")]["cum_return"]),
        "ep_lib_bc": _pct(epis[("Liberation Day tariffs (Apr 2025)", "base_carry")]["cum_return"]),
        # risk
        "a1_wdd": _pct(wdd["A1_theory_with_dollar"]["depth"]), "a1_wdd_peak": wdd["A1_theory_with_dollar"]["peak"],
        "a1_wdd_trough": wdd["A1_theory_with_dollar"]["trough"],
        "bc_wdd": _pct(wdd["base_carry"]["depth"]), "bc_wdd_peak": wdd["base_carry"]["peak"], "bc_wdd_trough": wdd["base_carry"]["trough"],
        "beta_a2_msci": _f2(beta[("A2_theory_with_dollar", "msci_world")]["beta"]), "beta_a2_msci_t": _f1(beta[("A2_theory_with_dollar", "msci_world")]["t"]),
        "dbeta_a2": _f2(down[("A2_theory_with_dollar", "msci_world")]["downside_beta"]),
        "dbeta_a1": _f2(down[("A1_theory_with_dollar", "msci_world")]["downside_beta"]),
        "dbeta_bc": _f2(down[("base_carry", "msci_world")]["downside_beta"]),
        "down_weeks": str(int(down[("base_carry", "msci_world")]["n_down"])),
        "down_bc_bp": f"{down[('base_carry', 'msci_world')]['mean_return_down_days_bp']:.0f}",
        "krw_share": _pct(comp["KRW"]["share_of_gross"], 0), "krw_pnl_share": _pct(conc[("base_carry", "currency", "KRW")]["share_of_abs"], 0),
        "corr_ab": _f2(ab["return_corr"]), "corr_ab_weekly": _f2(ab["weekly_return_corr"]),
        "liq_low": _f2(cond[("base_carry", "half-spread tercile", "q1")]["sharpe"]),
        "liq_high": _f2(cond[("base_carry", "half-spread tercile", "q3")]["sharpe"]),
        "lev_a1_gross": _f2(lev[("A1_theory_with_dollar", "2024-2026")]["gross_mean"]),
        "lev_a1_pair_cap": _pct(lev[("A1_theory_with_dollar", "2024-2026")]["share_days_pair_cap"]),
        "lev_a1_gross_cap": _pct(lev[("A1_theory_with_dollar", "2024-2026")]["share_days_gross_cap"]),
        "lev_a1_vol": _pct(lev[("A1_theory_with_dollar", "2024-2026")]["realised_vol"]),
        "lev_bc_gross": _f2(lev[("base_carry", "2024-2026")]["gross_mean"]),
        # robustness
        "placebo_b": f"{100 * Q['placebo_b']['share_beaten']:.0f}", "placebo_b_random": _f2(Q["placebo_b"]["random_contracts"]),
        "cost_b_05": _f2(cost_b[0.5]["sharpe"]), "cost_b_2": _f2(cost_b[2.0]["sharpe"]), "cost_b_3": _f2(cost_b[3.0]["sharpe"]),
        "grid_k": f"{m['shock_k']:.1f}", "grid_rerisk": str(m["rerisk_days"]), "grid_cut": f"{100 * m['shock_cut']:.0f}",
        "n_grid": str(len(Q["grid_b"])),
    }
    # worked example
    W = data["walk"]
    wc, rows_c, rows_a, rows_g = W["contract"], W["contract_rows"], W["cell_a"], W["geo"]
    peak = max(rows_c, key=lambda r: abs(r["z"]))
    i_peak = rows_c.index(peak)
    before = rows_c[i_peak - 1] if i_peak > 0 else peak
    shocks = [r for r in rows_g if r["confirmed"]]
    month_end = [r for r in rows_g if r["w_escalation"] is not None and r["w_escalation"] < 1]
    v.update({
        "walk_title": wc["title"], "walk_platform": wc["platform"].capitalize(), "walk_deadline": wc["deadline"],
        "walk_first": wc["first_day"], "walk_last": wc["last_day"], "walk_days": str(wc["days"]), "walk_elig": str(wc["eligible_days"]),
        "walk_sign": "+1" if wc["sign"] > 0 else "-1",
        "walk_sign_word": "escalation" if wc["sign"] > 0 else "de-escalation",
        "walk_win_start": rows_c[0]["day"], "walk_win_end": rows_c[-1]["day"],
        "walk_peak_day": peak["day"], "walk_peak_px_before": f"{100 * before['px']:.0f}", "walk_peak_px": f"{100 * peak['px']:.0f}",
        "walk_peak_hz_before": _f2(before["hazard_per_year"]), "walk_peak_hz": _f2(peak["hazard_per_year"]),
        "walk_peak_dv": _f2(peak["dv"]), "walk_peak_sd": _f2(peak["sd"]), "walk_peak_z": _f1(peak["z"]),
        "walk_peak_share": _pct(peak["weight_share"], 0), "walk_peak_contrib": _f2(peak["contribution"]),
        "walk_peak_cell": _f2(peak["d_vw"]), "walk_peak_n": str(int(peak["n_contracts"])),
        "walk_a_start": rows_a[0]["day"], "walk_a_end": rows_a[-1]["day"],
        "walk_a_flip_day": next((r["day"] for r in rows_a if r["usd_position"] > 0), rows_a[0]["day"]),
        "walk_a_zmon_max": _f2(max(r["Z_mon"] for r in rows_a)),
        "walk_a_usd_max": _f2(max(r["usd_position"] for r in rows_a)), "walk_a_usd_min": _f2(min(r["usd_position"] for r in rows_a)),
        "walk_g_start": rows_g[0]["day"], "walk_g_end": rows_g[-1]["day"], "walk_g_shocks": str(len(shocks)),
        "walk_g_first_shock": shocks[0]["day"] if shocks else "", "walk_g_zmax": _f2(max(r["escalation_z"] for r in rows_g if r["escalation_z"] is not None)),
        "walk_g_month_end": month_end[0]["day"] if month_end else "", "walk_g_month_w": _f2(month_end[0]["w_escalation"]) if month_end else "",
        "walk_g_month_z": _f2(month_end[0]["escalation_z"]) if month_end else "",
        "esc_z1": f"{m['escalation_z_cuts'][0]:.0f}", "esc_z2": f"{m['escalation_z_cuts'][1]:.0f}",
        "esc_w1": f"{m['escalation_weights'][1]:.1f}", "min_obs_vol": "5", "min_active": "20",
        "shock_persist_hours": str(m["shock_persist_hours"]),
    })
    return v


# ----------------------------------------------------------------------------- page
def _check_no_em_dash(name: str, text: str) -> None:
    if EM_DASH in text:
        i = text.index(EM_DASH)
        raise ValueError(f"em dash in {name} near: {text[max(0, i - 60):i + 60]!r}")


def data_json(data: dict) -> str:
    """DATA as JSON, safe inside a <script> element, with no em dash (titles from the platforms may carry one)."""
    s = json.dumps(data, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    n = s.count(EM_DASH)
    if n:
        log.info("%d em dash(es) in data strings replaced by a hyphen", n)
        s = s.replace(EM_DASH, "-")
    return s.replace("</", "<\\/")


def render(data: dict, values: dict[str, str] | None = None) -> str:
    values = dict(values or prose_values(data))
    tpl = (SITE_SRC / "template.html").read_text(encoding="utf-8")
    css = (SITE_SRC / "site.css").read_text(encoding="utf-8")
    js = (SITE_SRC / "site.js").read_text(encoding="utf-8")
    djson = data_json(data)
    for name, text in (("template.html", tpl), ("site.css", css), ("site.js", js), ("DATA", djson)):
        _check_no_em_dash(name, text)
    for k, v in values.items():
        _check_no_em_dash(f"prose value {k}", str(v))
    values.update({"CSS": css, "JS": js, "DATA_JSON": djson, "PLOTLY": PLOTLY.read_text(encoding="utf-8")})
    missing = sorted({k for k in re.findall(r"\{\{(\w+)\}\}", tpl)} - set(values))
    if missing:
        raise KeyError(f"template placeholders without a value: {missing}")
    return re.sub(r"\{\{(\w+)\}\}", lambda mt: values[mt.group(1)], tpl)


def build(cfg: dict | None = None, out: Path | None = None) -> Path:
    cfg = cfg or load_config()
    out = out or (ROOT / cfg["paths"].get("site", "site") / "index.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    data = assemble_data(cfg)
    html = render(data)
    out.write_text(html, encoding="utf-8")
    log.info("page written to %s (%.1f MB)", out, out.stat().st_size / 1e6)
    return out


if __name__ == "__main__":
    build()
