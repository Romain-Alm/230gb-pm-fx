"""Run Strategy B end to end once market data is available (spec 7, 8, 10).

Outputs in results/strategy_b/: performance tables (gross and net, in-sample and
out-of-sample), the 3 x 3 x 3 robustness grid, cost sensitivity, exposure w(t), and the
benchmark comparison (base carry, VIX-timed carry, PM-timed carry).
"""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from src.backtest import engine, metrics
from src.common import get_logger, load_config, rpath
from src.data import market
from src.pm import shocks
from src.strategies import strategy_b as B

log = get_logger("run_b")


UNIVERSE_COLUMN = {"primary": "exclude", "coarse12": "exclude_variant_coarse12", "previous": "exclude_previous"}


def em_universe(cfg, mapping: dict | None = None, universe: str = "primary") -> list[str]:
    """Eligible EM currencies (IRR screen, D23), restricted to those present in the data mapping."""
    ex = pd.read_csv(rpath("manual", cfg) / "em_exclusions.csv", comment="#")
    ccys = ex.loc[ex[UNIVERSE_COLUMN[universe]] == 0, "ccy"].tolist()
    return [c for c in ccys if mapping is None or c in mapping.get("fx", {})]


def split_stats(series: dict[str, pd.Series], cfg, extras: dict | None = None) -> pd.DataFrame:
    rows = []
    for name, r in series.items():
        for period, a, b in (("in-sample", cfg["sample"]["start"], cfg["sample"]["train_end"]),
                             ("out-of-sample", cfg["sample"]["test_start"], cfg["sample"]["end"]),
                             ("full", cfg["sample"]["start"], cfg["sample"]["end"])):
            seg = r.loc[a:b]
            kw = (extras or {}).get(name, {})
            kw = {k: v.loc[a:b] for k, v in kw.items()}
            rows.append({"strategy": name, "period": period, **metrics.perf_stats(seg, bootstrap=True, **kw)})
    return pd.DataFrame(rows)


def prepare(cfg: dict, history_start: str = "2010-01-01", universe: str = "primary",
            single_cap: float | None = None) -> dict:
    """Market data, base carry portfolio and timing inputs shared by the run and the
    robustness exercises."""
    b = cfg["strategy_b"]
    raw, mp = market.read_raw(cfg), market.series_map(cfg)
    ccys = em_universe(cfg, mp, universe)
    days_long = pd.bdate_range(history_start, cfg["sample"]["end"])
    fx = market.fx_panel(raw, mp, ccys, days_long, cfg["costs"].get("half_spread_median_days", 1))
    risk = market.simple_series(raw, mp, "risk", days_long)
    hs = fx.half_spread.fillna(cfg["costs"]["em_half_spread_bp"] / 1e4)
    vix_stress = risk["vix"] > risk["vix"].expanding(min_periods=250).quantile(cfg["costs"]["vix_stress_quantile"])
    hs = hs.mul(np.where(vix_stress.shift(1).fillna(False), cfg["costs"]["vix_stress_multiplier"], 1.0), axis=0)
    # Base carry over the long history (crash-risk premise), then the timing sample.
    base_w = B.base_carry_weights(fx.carry, fx.rx, b["n_long"], b["n_short"], b["vol_lookback_days"],
                                  b["vol_target_annual"], leg_rule=b.get("leg_rule", "fixed"),
                                  single_cap=single_cap)
    # VIX closes after the London snapshot: the VIX signal for day t uses the close of t-1.
    vix_z, vix_shock = B.vix_signals(risk["vix"].shift(1).dropna())
    p0 = B.TimingParams(tuple(b["escalation_z_cuts"]), tuple(b["escalation_weights"]),
                        b["shock_cut_level"], b["rerisk_days"])
    # Execution lag (trading days) when prices are observed before the signal snapshot: one lag
    # for every currency (D22, free data) or per currency from its closing time ("by_close", D28).
    lag_cfg = b.get("exec_lag_days", 0)
    lags = market.exec_lags(mp, ccys) if lag_cfg == "by_close" else {c: int(lag_cfg) for c in ccys}
    base_w = pd.DataFrame({c: base_w[c].shift(lags[c]) for c in base_w.columns}).fillna(0.0)
    return {"cfg": cfg, "fx": fx, "risk": risk, "hs": hs, "base_w": base_w, "p0": p0, "lags": lags,
            "days": pd.bdate_range(cfg["sample"]["start"], cfg["sample"]["end"]),
            "rows": shocks.composite_rows(cfg, rpath("processed", cfg)),
            "vix_z": vix_z, "vix_shock": vix_shock, "history_start": history_start,
            "universe": universe, "single_cap": single_cap, "ccys": ccys}


def timed(ctx: dict, esc_z: pd.Series, shock: pd.Series, p: B.TimingParams | None = None):
    """Exposure w(t) and backtest of the timed carry portfolio."""
    days = ctx["days"]
    w = B.timing_exposure(esc_z, shock, days, p or ctx["p0"])
    base = ctx["base_w"].reindex(days)
    lags = ctx.get("lags", {})
    weights = base.mul(pd.DataFrame({c: w["w"].shift(lags.get(c, 0)).fillna(1.0) for c in base.columns}))
    return w, engine.run(weights, ctx["fx"].rx.reindex(days), ctx["hs"].reindex(days))


def oil_tilt(ctx: dict, esc_z: pd.Series, nonoil: pd.Series, oil: pd.Series, tilt_w: pd.DataFrame,
             p: B.TimingParams | None = None):
    """B2 (spec 7.5, scope-freeze lifting of 2026-10-03): non-oil shocks cut the carry portfolio as in the primary rule; an
    oil shock does not cut it but adds the exporters-minus-importers tilt, sized by the cut the
    shock would have made (same re-risk path). Returns the backtest and the tilt exposure."""
    days, p = ctx["days"], p or ctx["p0"]
    w_non = B.timing_exposure(esc_z, nonoil, days, p)
    w_oil = B.timing_exposure(esc_z, oil, days, p)
    over = w_oil["w_escalation"] - w_oil["w"]
    lags = ctx.get("lags", {})
    base = ctx["base_w"].reindex(days)
    tw = tilt_w.reindex(index=days, columns=base.columns).fillna(0.0)
    mult = pd.DataFrame({c: w_non["w"].shift(lags.get(c, 0)).fillna(1.0) for c in base.columns})
    add = pd.DataFrame({c: over.shift(lags.get(c, 0)).fillna(0.0) for c in base.columns})
    weights = base.mul(mult) + tw.mul(add)
    return engine.run(weights, ctx["fx"].rx.reindex(days), ctx["hs"].reindex(days)), over


def key_month_check(ctx: dict, cfg: dict, rows: pd.DataFrame, r_pm: pd.Series, r_base: pd.Series) -> pd.DataFrame:
    """D29 (diagnostic, after results): month with the largest gain of the PM timing over the base
    carry, the event that moved the escalation index most in the 35 days before that month, and
    the timed portfolio rebuilt without that event (leave-one-event-out on the decisive event)."""
    diff = (r_pm - r_base).dropna()
    by_month = diff.resample("ME").sum()
    m = by_month.idxmax()
    m_start = m - pd.offsets.MonthBegin(1)
    win = rows[(rows["day"] >= m_start - pd.Timedelta(days=35)) & (rows["day"] < m_start) & (rows["z"] > 0)]
    ev = win.groupby("event_key")["z"].sum().idxmax()
    n_contracts = win[win["event_key"] == ev]["contract_id"].nunique()
    sig = shocks.build_signals(shocks.composite_rows(cfg, rpath("processed", cfg), exclude_events=[ev]),
                               cfg).set_index("day")
    _, res = timed(ctx, sig["escalation_z"], sig["confirmed"])
    out = []
    for name, r in (("base_carry", r_base), ("pm_timed", r_pm), ("pm_timed_without_event", res.net_ret)):
        st = metrics.perf_stats(r.loc[cfg["sample"]["start"]:cfg["sample"]["end"]])
        out.append({"strategy": name, "sharpe": st["sharpe"], "ann_mean": st["ann_mean"],
                    "max_drawdown": st["max_drawdown"]})
    out = pd.DataFrame(out)
    out["best_month"] = m.strftime("%Y-%m")
    out["best_month_gain"] = by_month.loc[m]
    out["total_gain"] = diff.sum()
    out["event_removed"] = ev
    out["event_contracts"] = n_contracts
    out.attrs["series"] = res.net_ret.rename("pm_timed_without_event")
    return out


def run(cfg: dict | None = None, history_start: str = "2010-01-01") -> dict:
    cfg = cfg or load_config()
    out_dir = rpath("results", cfg) / "strategy_b"
    out_dir.mkdir(parents=True, exist_ok=True)
    b = cfg["strategy_b"]
    ctx = prepare(cfg, history_start)
    fx, risk, hs, base_w, days, rows, p0 = (ctx[k] for k in ("fx", "risk", "hs", "base_w", "days", "rows", "p0"))
    vix_z, vix_shock = ctx["vix_z"], ctx["vix_shock"]
    base_long = engine.run(base_w, fx.rx, hs)
    sig = shocks.build_signals(rows, cfg).set_index("day")
    w_pm, res_pm = timed(ctx, sig["escalation_z"], sig["confirmed"], p0)
    # Reported variant only: the original, misspecified level rule (D16).
    w_lvl, res_lvl = timed(ctx, sig["level_z_spec_misspecified"], sig["confirmed"], p0)
    w_vix, res_vix = timed(ctx, vix_z, vix_shock, p0)
    # D12 robustness variant: probability-based geopolitical index (no hazard transform).
    proc = rpath("processed", cfg)
    extra_series, extra_res = {}, {"pm_timed_level_misspecified": res_lvl}
    if (proc / "contract_days_prob.parquet").exists():
        sp = shocks.build_signals(shocks.composite_rows(cfg, proc, "contract_days_prob.parquet",
                                                        "contract_changes_prob.parquet"), cfg).set_index("day")
        _, res_prob = timed(ctx, sp["escalation_z"], sp["confirmed"], p0)
        extra_series["pm_timed_prob_index_D12"] = res_prob.net_ret
        extra_res["pm_timed_prob_index_D12"] = res_prob
    base = engine.run(base_w.reindex(days), fx.rx.reindex(days), hs.reindex(days))

    # D23 variants: other universes and the 20% single-currency cap (same signals and rule).
    for univ, cap in (("coarse12", None), ("previous", None), ("primary", 0.20), ("previous", 0.20)):
        tag = univ + ("_cap20" if cap else "")
        cv = prepare(cfg, history_start, univ, cap)
        cv["rows"] = rows
        _, rb_ = timed(cv, pd.Series(-9.0, index=days), pd.Series(False, index=days), p0)
        _, rt_ = timed(cv, sig["escalation_z"], sig["confirmed"], p0)
        extra_series[f"base_carry__{tag}"], extra_series[f"pm_timed__{tag}"] = rb_.net_ret, rt_.net_ret
        extra_res[f"base_carry__{tag}"], extra_res[f"pm_timed__{tag}"] = rb_, rt_
        log.info("variant %s: %d currencies %s", tag, len(cv["ccys"]), cv["ccys"])
    log.info("primary universe: %s", ctx["ccys"])

    series = {"base_carry": base.net_ret, "pm_timed": res_pm.net_ret, "vix_timed": res_vix.net_ret,
              "pm_timed_level_misspecified": res_lvl.net_ret, **extra_series,
              "base_carry_gross": base.gross_ret, "pm_timed_gross": res_pm.gross_ret,
              "vix_timed_gross": res_vix.gross_ret}
    # ---- Added on 2026-10-03 after the definitive results (scope-freeze lifting, DECISIONS): not pre-registered.
    # B2, oil-shock reallocation (spec 7.5): exporters and importers intersected with the universe.
    exp_ = [c for c in b["oil_exporters"] if c in ctx["ccys"]]
    imp_ = [c for c in b["oil_importers"] if c in ctx["ccys"]]
    tilt_w = B.tilt_weights(fx.rx.loc["2023-06-01":], exp_, imp_, b["vol_lookback_days"], b["vol_target_annual"])
    nonoil = sig["confirmed"] & ~sig["oil_confirmed"]
    res_b2, over_b2 = oil_tilt(ctx, sig["escalation_z"], nonoil, sig["oil_confirmed"], tilt_w, p0)
    # Brent-triggered benchmark: same rule, oil shock = Brent daily rise above k sd. Brent settles
    # after the 16:00 London snapshot, so the move of t-1 triggers at t.
    brent_sh = B.brent_shocks(risk["brent"], b["brent_shock_k"]).shift(1, fill_value=False)
    res_b2b, over_b2b = oil_tilt(ctx, sig["escalation_z"], nonoil, brent_sh, tilt_w, p0)
    # D31 robustness (after D29): at least `min_events_robustness` distinct events per index day,
    # for both the escalation measure and shock confirmation. Primary rule unchanged.
    sig3 = shocks.build_signals(shocks.min_events_filter(rows, b["min_events_robustness"]), cfg).set_index("day")
    w_3, res_3 = timed(ctx, sig3["escalation_z"], sig3["confirmed"], p0)
    me = B.month_ends(days)
    pd.DataFrame([
        {"item": "oil_exporters_used", "value": " ".join(exp_)},
        {"item": "oil_importers_used", "value": " ".join(imp_)},
        {"item": "confirmed_shocks", "value": int(sig["confirmed"].sum())},
        {"item": "oil_confirmed_shocks", "value": int(sig["oil_confirmed"].sum())},
        {"item": "oil_shock_dates", "value": " ".join(d.strftime("%Y-%m-%d") for d in sig.index[sig["oil_confirmed"]])},
        {"item": "brent_shock_days", "value": int(brent_sh.loc[cfg["sample"]["start"]:cfg["sample"]["end"]].sum())},
        {"item": "days_with_tilt_pm", "value": int((over_b2 > 0).sum())},
        {"item": "days_with_tilt_brent", "value": int((over_b2b > 0).sum())},
        {"item": "min3_confirmed_shocks", "value": int(sig3["confirmed"].sum())},
        {"item": "min3_month_ends_escalation_z_ge_2",
         "value": int((sig3["escalation_z"].reindex(me, method="ffill") >= 2).sum())},
        {"item": "primary_month_ends_escalation_z_ge_2",
         "value": int((sig["escalation_z"].reindex(me, method="ffill") >= 2).sum())},
        {"item": "min3_index_days", "value": int((sig3["n_contracts"] > 0).sum())},
        {"item": "primary_index_days", "value": int((sig["n_contracts"] > 0).sum())},
    ]).to_csv(out_dir / "posthoc_b2_min3_info.csv", index=False)
    series.update({"b2_oil_tilt": res_b2.net_ret, "b2_oil_tilt_gross": res_b2.gross_ret,
                   "b2_brent_tilt": res_b2b.net_ret, "pm_timed_min3events": res_3.net_ret})

    extras = {k: {"turnover": r.turnover, "gross": r.gross_exposure, "costs": r.costs}
              for k, r in (("base_carry", base), ("pm_timed", res_pm), ("vix_timed", res_vix),
                           ("b2_oil_tilt", res_b2), ("b2_brent_tilt", res_b2b), ("pm_timed_min3events", res_3),
                           *extra_res.items())}
    perf = split_stats(series, cfg, extras)
    perf.to_csv(out_dir / "performance.csv", index=False)
    pd.DataFrame(series).to_parquet(out_dir / "returns.parquet")
    base_long.net_ret.rename("base_carry_long_history").to_frame().to_parquet(out_dir / "returns_long_history.parquet")
    for name, res in (("base_carry", base), ("pm_timed", res_pm), ("vix_timed", res_vix), ("b2_oil_tilt", res_b2),
                      ("b2_brent_tilt", res_b2b)):
        res.pnl_by_asset.to_parquet(out_dir / f"pnl_by_asset_{name}.parquet")
        res.weights.to_parquet(out_dir / f"weights_{name}.parquet")
    pd.DataFrame([{"strategy": "base_carry_long_history",
                   **metrics.perf_stats(base_long.net_ret.loc[history_start:])}]).to_csv(
        out_dir / "base_carry_long_history.csv", index=False)
    w_pm.join(w_vix, rsuffix="_vix").to_csv(out_dir / "exposure.csv")

    # Robustness grid (spec 7.4): full grid, not the best cell.
    grid = []
    for k, rr, cut in itertools.product(cfg["smoothing"]["geo_shock_k_grid"], b["rerisk_grid"],
                                        b["shock_cut_grid"]):
        s_k = shocks.build_signals(rows, cfg, k=k).set_index("day")
        p = B.TimingParams(tuple(b["escalation_z_cuts"]), tuple(b["escalation_weights"]), cut, rr)
        _, res = timed(ctx, s_k["escalation_z"], s_k["confirmed"], p)
        st = metrics.perf_stats(res.net_ret)
        grid.append({"shock_k": k, "rerisk_days": rr, "shock_cut": cut, **st})
    pd.DataFrame(grid).to_csv(out_dir / "grid.csv", index=False)

    # Cost sensitivity and break-even.
    cs = []
    for m in cfg["costs"]["sensitivity"]:
        r = res_pm.gross_ret - m * res_pm.costs
        cs.append({"cost_multiplier": m, **metrics.perf_stats(r)})
    pd.DataFrame(cs).to_csv(out_dir / "cost_sensitivity.csv", index=False)
    km = key_month_check(ctx, cfg, rows, res_pm.net_ret, base.net_ret)
    km.to_csv(out_dir / "key_month_check.csv", index=False)
    km.attrs["series"].to_frame().to_parquet(out_dir / "returns_pm_timed_without_event.parquet")
    log.info("strategy B done:\n%s", perf[perf["period"] == "full"][["strategy", "sharpe", "ann_mean",
                                                                      "ann_vol", "max_drawdown"]])
    return {"fx": fx, "risk": risk, "base": base, "pm": res_pm, "vix": res_vix, "w_pm": w_pm,
            "base_long": base_long, "signals": sig}


if __name__ == "__main__":
    run()
