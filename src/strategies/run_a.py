"""Run Strategy A end to end once market data is available (spec 6, 8, 10; D2, D14, D15).

For each variant A1, A2, A3 (D14):
  - theory-signed rule (primary, D2), dollar-neutral and with dollar exposure;
  - regression-gated rule (spec 6.5): pooled regression on 2024-2025, themes with t > 3 and
    the predicted (positive) sign enter with frozen coefficients; expanding-window version
    re-estimated monthly;
  - diagnostics (spec 6.4): predictive (1, 5, 20 days) and contemporaneous pooled panel
    regressions with Driscoll-Kraay errors, the amended fiscal-regime regression, and Wald
    tests of the pooling restriction.
Outputs in results/strategy_a/.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.backtest import engine, metrics
from src.common import get_logger, load_config, rpath
from src.data import market
from src.strategies import diagnostics as D
from src.strategies import strategy_a as A
from src.strategies.run_b import split_stats

log = get_logger("run_a")
G10 = list(A.PAIRS)


def regime_inputs(raw, mp, fx, days):
    """10-year yields and currency values per zone for the fiscal-regime indicator."""
    try:
        y10 = market.simple_series(raw, mp, "y10", days)
    except Exception as e:                       # yields missing: baseline (monetary dominance)
        log.warning("no 10-year yields (%s): fiscal regime set to the baseline", e)
        return None
    logs = np.log(fx.spot[G10])
    val = pd.DataFrame({"US": -logs.mean(axis=1), "EA": logs["EUR"], "UK": logs["GBP"],
                        "JP": logs["JPY"], "CH": logs["CHF"], "CA": logs["CAD"],
                        "AU": logs["AUD"], "NZ": logs["NZD"], "NO": logs["NOK"], "SE": logs["SEK"]})
    return A.fiscal_regime(y10, val, 60)


def gated_weights(comps: dict, rx: pd.DataFrame, end: str, gate: float) -> tuple[dict, pd.DataFrame]:
    keys = [k for k in comps if not k.startswith("_") and comps[k].abs().to_numpy().sum() > 0]
    if not keys:
        return {}, pd.DataFrame()
    df = D.stack({k: comps[k].loc[:end] for k in keys}, rx.loc[:end], horizon=1)
    res = D.pooled(df, keys)
    tab = D.coef_table(res, 1, "gate")
    keep = tab[(tab["t"] > gate) & (tab["coef"] > 0)]
    return dict(zip(keep["regressor"], keep["coef"])), tab


def prepare(cfg: dict) -> dict:
    """Market data, fiscal regime and theme signals shared by the run and the robustness
    exercises."""
    proc = rpath("processed", cfg)
    raw, mp = market.read_raw(cfg), market.series_map(cfg)
    days_warm = pd.bdate_range("2023-06-01", cfg["sample"]["end"])
    fx = market.fx_panel(raw, mp, G10, days_warm, cfg["costs"].get("half_spread_median_days", 1))
    hs = fx.half_spread.fillna(cfg["costs"]["g10_half_spread_bp"] / 1e4)
    debt = pd.read_csv(rpath("manual", cfg) / "fiscal_regime.csv", comment="#").set_index("zone")["debt_gdp_2024"] / 100
    hl = cfg["smoothing"]["ewma_halflife_days"]
    cov = pd.read_csv(rpath("results", cfg) / "coverage_cells.csv")
    return {"cfg": cfg, "fx": fx, "rx": fx.rx, "hs": hs, "debt": debt.to_dict(),
            "regime": regime_inputs(raw, mp, fx, days_warm), "days_warm": days_warm,
            "days": pd.bdate_range(cfg["sample"]["start"], cfg["sample"]["end"]),
            "sig50": A.all_cell_signals(pd.read_parquet(proc / "theme_index.parquet"), hl),
            "sig10": A.all_cell_signals(pd.read_parquet(proc / "theme_index_v10k.parquet"), hl),
            "kept": set(zip(cov.loc[cov["keep"], "zone"], cov.loc[cov["keep"], "theme"])),
            # D12 robustness variant: probability-based indices (no hazard transform), demeaned
            "sig50_d12": (A.all_cell_signals(pd.read_parquet(proc / "theme_index_prob.parquet"), hl, demean=True)
                          if (proc / "theme_index_prob.parquet").exists() else None)}


def hold_weights(w: pd.DataFrame, days: pd.DatetimeIndex, rebalance=None, offset: int = 0) -> pd.DataFrame:
    """Weights decided only on rebalance dates and held until the next one: None = daily,
    "weekly" = last trading day of each week, an integer n = every n trading days starting at
    trading day `offset` (flat before the first rebalance)."""
    if rebalance is None:
        return w
    if rebalance == "weekly":
        dates = pd.DatetimeIndex(pd.Series(days, index=days).groupby(days.to_period("W-FRI")).max().values)
    else:
        dates = days[int(offset)::int(rebalance)]
    return w.reindex(days).fillna(0.0).loc[dates].reindex(days, method="ffill").fillna(0.0)


def forecast(ctx: dict, variant: str, sigs: dict | None = None, sign: float = 1.0,
             components: dict | None = None) -> pd.DataFrame:
    """Pair-level forecast of a variant: equal-weighted sum of its signed components, or the
    frozen {component: coefficient} of a gated rule."""
    sigs = sigs if sigs is not None else (ctx["sig10"] if variant.startswith("A2") else ctx["sig50"])
    cells = A.variant_cells(variant, set(sigs), ctx["kept"])
    comps = A.pair_components(sigs, ctx["days_warm"], cells, ctx["regime"], True, ctx["debt"])
    if components is None:
        return sign * sum(v for k, v in comps.items() if not k.startswith("_")).loc[ctx["days"]]
    return sign * sum(comps[k] * c for k, c in components.items() if k in comps).loc[ctx["days"]]


def evaluate(ctx: dict, variant: str, dollar_neutral: bool, sigs: dict | None = None,
             sign: float = 1.0, rebalance=None, components: dict | None = None, offset: int = 0):
    """Backtest of the theory-signed rule for one variant (optionally with replaced signals
    or a reversed sign, for placebos). `components` = frozen {component: coefficient} of a
    gated rule (default: equal-weighted sum of every signed component); `rebalance` as in
    hold_weights."""
    y = forecast(ctx, variant, sigs, sign, components)
    w = A.positions(y, ctx["rx"].reindex(ctx["days"]), ctx["cfg"], dollar_neutral)
    w = hold_weights(w, ctx["days"], rebalance, offset)
    return engine.run(w, ctx["rx"].reindex(ctx["days"]), ctx["hs"].reindex(ctx["days"]))


def run(cfg: dict | None = None) -> dict:
    cfg = cfg or load_config()
    out_dir = rpath("results", cfg) / "strategy_a"
    out_dir.mkdir(parents=True, exist_ok=True)
    a = cfg["strategy_a"]
    ctx = prepare(cfg)
    fx, rx, hs, regime, days_warm, days = (ctx[k] for k in ("fx", "rx", "hs", "regime", "days_warm", "days"))
    debt = pd.Series(ctx["debt"])
    sig50, sig10, kept = ctx["sig50"], ctx["sig10"], ctx["kept"]

    series, extras, diag_tables, gate_tables, results = {}, {}, [], [], {}
    for variant in ("A1", "A1+S", "A2", "A2+S", "A3", "A3+S"):
        sigs = sig10 if variant.startswith("A2") else sig50
        cells = A.variant_cells(variant, set(sigs), kept)
        comps = A.pair_components(sigs, days_warm, cells, regime, True, debt.to_dict())
        signed = {k: v for k, v in comps.items() if not k.startswith("_")}
        y = sum(signed.values()).loc[days]
        for dn in (True, False):
            name = f"{variant}_theory_{'dollar_neutral' if dn else 'with_dollar'}"
            w = A.positions(y, rx.reindex(days), cfg, dn)
            res = engine.run(w, rx.reindex(days), hs.reindex(days))
            series[name], series[name + "_gross"] = res.net_ret, res.gross_ret
            extras[name] = {"turnover": res.turnover, "gross": res.gross_exposure, "costs": res.costs}
            results[name] = res

        # Regression-gated rule, frozen on 2024-2025 (spec 6.5).
        wts, tab = gated_weights({k: v.loc[days] for k, v in comps.items()}, rx.reindex(days),
                                 cfg["sample"]["train_end"], a["gate_abs_t"])
        if len(tab):
            gate_tables.append(tab.assign(variant=variant))
        yg = sum(signed[k] * c for k, c in wts.items()).loc[days] if wts else pd.DataFrame(0.0, index=days, columns=G10)
        name = f"{variant}_gated_frozen"
        w = A.positions(yg, rx.reindex(days), cfg, True) if wts else yg
        res = engine.run(w, rx.reindex(days), hs.reindex(days))
        series[name] = res.net_ret
        results[name] = res
        log.info("%s gated themes: %s", variant, wts or "none passes |t| > 3")

        # Diagnostics (spec 6.4).
        for h in (1, 5, 20):
            df = D.stack({k: v.loc[days] for k, v in signed.items() if v.abs().to_numpy().sum() > 0},
                         rx.reindex(days), horizon=h)
            if df.shape[1] > 1:
                r = D.pooled(df, [c for c in df.columns if c != "y"], bandwidth=max(h, 5))
                diag_tables.append(D.coef_table(r, h, f"{variant}_predictive"))
        dfc = D.stack({k: v.loc[days] for k, v in signed.items() if v.abs().to_numpy().sum() > 0},
                      rx.reindex(days), contemporaneous=True)
        if dfc.shape[1] > 1:
            r = D.pooled(dfc, [c for c in dfc.columns if c != "y"])
            diag_tables.append(D.coef_table(r, 0, f"{variant}_contemporaneous"))
        fis = {k: comps[k].loc[days] for k in ("_fiscal_raw", "_fiscal_x_regime", "_fiscal_x_debt") if k in comps}
        if fis and comps["_fiscal_raw"].abs().to_numpy().sum() > 0:
            dff = D.stack(fis, rx.reindex(days), horizon=1)
            r = D.pooled(dff, list(fis))
            t = D.coef_table(r, 1, f"{variant}_fiscal_regime")
            t["prediction"] = t["regressor"].map({"_fiscal_raw": "b0 > 0", "_fiscal_x_regime": "b2 < 0",
                                                  "_fiscal_x_debt": "b1 < 0"})
            diag_tables.append(t)

    # D12 robustness variant: probability-based indices with causal demeaning.
    if ctx["sig50_d12"] is not None:
        for dn in (True, False):
            name = f"A1_theory_{'dollar_neutral' if dn else 'with_dollar'}_D12"
            res = evaluate(ctx, "A1", dn, ctx["sig50_d12"])
            series[name], results[name] = res.net_ret, res

    # ---- Added on 2026-10-03 after the definitive results (scope-freeze lifting, DECISIONS): not pre-registered.

    def add(name, res):
        series[name], series[name + "_gross"] = res.net_ret, res.gross_ret
        extras[name] = {"turnover": res.turnover, "gross": res.gross_exposure, "costs": res.costs}
        results[name] = res

    # A1 with weekly rebalancing (last trading day of each week), a posteriori.
    add("A1_theory_with_dollar_weekly",
        engine.run(hold_weights(results["A1_theory_with_dollar"].weights, days, "weekly"), rx.reindex(days),
                   hs.reindex(days)))

    # D30: regression-gated rule at the 20-day horizon (horizon chosen after seeing the
    # full-sample 20-day diagnostic). Estimated on 2024-2025 only, targets that end inside the
    # training window, Driscoll-Kraay (Bartlett, bandwidth 20) standard errors; components with
    # the predicted (positive) sign and t > gate kept, coefficients frozen, rebalanced every 20
    # trading days, evaluated on 2026.
    gate20 = []
    train_end = cfg["sample"]["train_end"]
    for variant in ("A1", "A2"):
        sigs = sig10 if variant.startswith("A2") else sig50
        cells = A.variant_cells(variant, set(sigs), kept)
        comps = A.pair_components(sigs, days_warm, cells, regime, True, debt.to_dict())
        signed = {k: v.loc[days] for k, v in comps.items() if not k.startswith("_")}
        train = [k for k, v in signed.items() if v.loc[:train_end].abs().to_numpy().sum() > 0]
        wts = {}
        if train:
            df = D.stack({k: signed[k].loc[:train_end] for k in train}, rx.reindex(days).loc[:train_end], horizon=20)
            tab = D.coef_table(D.pooled(df, train, bandwidth=20), 20, f"{variant}_gate20").assign(variant=variant)
            tab["passes_gate"] = (tab["t"] > a["gate_abs_t"]) & (tab["coef"] > 0)
            gate20.append(tab)
            keep = tab[tab["passes_gate"]]
            wts = dict(zip(keep["regressor"], keep["coef"]))
        if wts:
            yg = sum(signed[k] * c for k, c in wts.items())
            w = hold_weights(A.positions(yg, rx.reindex(days), cfg, False), days, 20)
        else:
            w = pd.DataFrame(0.0, index=days, columns=G10)
        add(f"{variant}_gated20_frozen", engine.run(w, rx.reindex(days), hs.reindex(days)))
        log.info("%s gated20 themes: %s", variant, wts or "none passes |t| > 3")
    if gate20:
        pd.concat(gate20).to_csv(out_dir / "gate20_estimation.csv", index=False)

    # Cost scenario at 0.5x the Bloomberg composite half-spread (primary stays at 1x).
    for name in ("A1_theory_with_dollar", "A2_theory_with_dollar", "A1_theory_with_dollar_weekly",
                 "A1_gated20_frozen", "A2_gated20_frozen"):
        res = results[name]
        series[name + "_cost0.5x"] = res.gross_ret - 0.5 * res.costs
        extras[name + "_cost0.5x"] = {"turnover": res.turnover, "gross": res.gross_exposure, "costs": 0.5 * res.costs}

    # D25: static versus timing decomposition of A1 (gross P&L, positions held from t to t+1).
    dec_rows = []
    for name in ("A1_theory_with_dollar", "A2_theory_with_dollar"):
        if name not in results:
            continue
        w = results[name].weights.reindex(days).fillna(0.0)
        r = rx.reindex(days).fillna(0.0)
        w_bar = w.loc[:cfg["sample"]["train_end"]].mean()
        parts = {"total": (w.shift(1) * r).sum(axis=1),
                 "static": (r * w_bar).sum(axis=1).where(w.shift(1).abs().sum(axis=1) >= 0),
                 "timing": ((w.shift(1) - w_bar) * r).sum(axis=1)}
        for part, ret in parts.items():
            for period, a_, b_ in (("in-sample", cfg["sample"]["start"], cfg["sample"]["train_end"]),
                                   ("out-of-sample", cfg["sample"]["test_start"], cfg["sample"]["end"]),
                                   ("full", cfg["sample"]["start"], cfg["sample"]["end"])):
                st = metrics.perf_stats(ret.loc[a_:b_], bootstrap=True)
                dec_rows.append({"strategy": name, "part": part, "period": period, "sharpe": st.get("sharpe"),
                                 "sharpe_t": st.get("sharpe_t"), "sharpe_ci90_low": st.get("sharpe_ci90_low"),
                                 "sharpe_ci90_high": st.get("sharpe_ci90_high"),
                                 "ann_mean": st.get("ann_mean"), "ann_vol": st.get("ann_vol")})
        dec_rows.append({"strategy": name, "part": "static_position", "period": "2024-2025 average",
                         **{f"w_{k}": v for k, v in w_bar.round(4).items()}})
    pd.DataFrame(dec_rows).to_csv(out_dir / "decomposition_static_timing.csv", index=False)

    perf = split_stats(series, cfg, extras)
    perf.to_csv(out_dir / "performance.csv", index=False)
    pd.DataFrame(series).to_parquet(out_dir / "returns.parquet")
    for name, res in results.items():
        res.pnl_by_asset.to_parquet(out_dir / f"pnl_by_asset_{name}.parquet")
        res.weights.to_parquet(out_dir / f"weights_{name}.parquet")
    if diag_tables:
        pd.concat(diag_tables).to_csv(out_dir / "diagnostics.csv", index=False)
    if gate_tables:
        pd.concat(gate_tables).to_csv(out_dir / "gate_estimation.csv", index=False)
    if regime is not None:
        regime.to_csv(out_dir / "fiscal_regime.csv")
    log.info("strategy A done:\n%s", perf[perf["period"] == "full"][["strategy", "sharpe", "ann_mean",
                                                                      "ann_vol", "max_drawdown"]])
    return {"fx": fx, "results": results, "series": series, "regime": regime}


if __name__ == "__main__":
    run()
