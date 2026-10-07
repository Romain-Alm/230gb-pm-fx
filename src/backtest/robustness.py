"""Robustness exercises (spec 10.2) for both strategies.

Placebos (performance should collapse):
  (a) signal dates shuffled within each calendar month (many seeds, distribution reported);
  (b) theme contracts replaced by randomly drawn OTHER contracts with random signs;
  (c) signs reversed.
Also: leave-one-event-out on the largest events, sub-periods 2024 / 2025 / 2026, volume vs
equal weights, volume-threshold grid, EWMA half-life grid (Strategy A).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.backtest.metrics import perf_stats
from src.common import get_logger, rpath
from src.pm import indices, shocks
from src.strategies import run_a, run_b
from src.strategies import strategy_a as A
from src.strategies import strategy_b as B

log = get_logger("robustness")


def _shuffle_within_month(df: pd.DataFrame, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    out = df.copy()
    for _, idx in df.groupby(df.index.to_period("M")).groups.items():
        perm = rng.permutation(len(idx))
        out.loc[idx] = df.loc[idx].to_numpy()[perm]
    return out


def _row(name, r: pd.Series, **kw) -> dict:
    st = perf_stats(r)
    return {"test": name, **kw, "sharpe": st.get("sharpe"), "ann_mean": st.get("ann_mean"),
            "ann_vol": st.get("ann_vol"), "max_drawdown": st.get("max_drawdown")}


def subperiods(returns: pd.DataFrame) -> pd.DataFrame:
    out = []
    for y in sorted(set(returns.index.year)):
        seg = returns[returns.index.year == y]
        for c in seg.columns:
            out.append(_row("subperiod", seg[c], strategy=c, period=str(y)))
    return pd.DataFrame(out)


# ------------------------------------------------------------------------- Strategy B
def strategy_b(ctx: dict, n_shuffle: int = 100, n_loeo: int = 10) -> pd.DataFrame:
    cfg = ctx["cfg"]
    proc = rpath("processed", cfg)
    out = []
    sig = shocks.build_signals(ctx["rows"], cfg).set_index("day")
    _, base = run_b.timed(ctx, pd.Series(-9.0, index=sig.index), pd.Series(False, index=sig.index))
    _, act = run_b.timed(ctx, sig["escalation_z"], sig["confirmed"])
    out.append(_row("actual", act.net_ret))
    out.append(_row("base_carry", base.net_ret))
    # (a) shuffle within month
    for seed in range(n_shuffle):
        sh = _shuffle_within_month(sig[["escalation_z", "confirmed"]], seed)
        _, r = run_b.timed(ctx, sh["escalation_z"], sh["confirmed"].astype(bool))
        out.append(_row("placebo_a_shuffle", r.net_ret, seed=seed))
    # (b) random OTHER contracts with random signs
    if (proc / "contract_days_placebo.parquet").exists():
        rows_p = shocks.composite_rows(cfg, proc, "contract_days_placebo.parquet",
                                       "contract_changes_placebo.parquet", placebo=True)
        sp = shocks.build_signals(rows_p, cfg).set_index("day")
        _, r = run_b.timed(ctx, sp["escalation_z"], sp["confirmed"])
        out.append(_row("placebo_b_random_contracts", r.net_ret))
    # (c) reversed sign: de-escalation treated as escalation
    rows_rev = ctx["rows"].assign(z=-ctx["rows"]["z"], z_early=-ctx["rows"]["z_early"])
    sr = shocks.build_signals(rows_rev, cfg).set_index("day")
    _, r = run_b.timed(ctx, sr["escalation_z"], sr["confirmed"])
    out.append(_row("placebo_c_reversed", r.net_ret))
    # Equal weights inside the index
    se = shocks.build_signals(ctx["rows"].assign(vol7d=1.0), cfg).set_index("day")
    _, r = run_b.timed(ctx, se["escalation_z"], se["confirmed"])
    out.append(_row("equal_weights", r.net_ret))
    # Volume threshold grid
    for thr, cdf, chf in (("10k", "contract_days_v10k.parquet", "contract_changes_v10k.parquet"),
                          ("250k", "contract_days_v250k.parquet", "contract_changes_v250k.parquet")):
        if (proc / cdf).exists() and (proc / chf).exists():
            s2 = shocks.build_signals(shocks.composite_rows(cfg, proc, cdf, chf), cfg).set_index("day")
            _, r = run_b.timed(ctx, s2["escalation_z"], s2["confirmed"])
            out.append(_row("volume_threshold", r.net_ret, threshold=thr))
    # Leave one event out (largest events by volume)
    top = ctx["rows"].groupby("event_key")["vol1d"].sum().sort_values(ascending=False).head(n_loeo).index
    for ev in top:
        s3 = shocks.build_signals(shocks.composite_rows(cfg, proc, exclude_events=(ev,)), cfg).set_index("day")
        _, r = run_b.timed(ctx, s3["escalation_z"], s3["confirmed"])
        out.append(_row("leave_one_event_out", r.net_ret, event=ev))
    return pd.DataFrame(out)


# ------------------------------------------------------------------------- Post-hoc additions
def posthoc_b(ctx: dict, n_shuffle: int = 100) -> pd.DataFrame:
    """Placebos (a), (b), (c) for the a posteriori B additions of 2026-10-03: B2 (oil-shock
    tilt, spec 7.5) and D31 (at least 3 distinct events per index day). The Brent-triggered
    benchmark has no prediction-market signal and gets no placebo."""
    cfg, b = ctx["cfg"], ctx["cfg"]["strategy_b"]
    proc = rpath("processed", cfg)
    exp_ = [c for c in b["oil_exporters"] if c in ctx["ccys"]]
    imp_ = [c for c in b["oil_importers"] if c in ctx["ccys"]]
    tilt_w = B.tilt_weights(ctx["fx"].rx.loc["2023-06-01":], exp_, imp_, b["vol_lookback_days"], b["vol_target_annual"])
    n_ev = b["min_events_robustness"]

    def b2(s):
        oil = s["oil_confirmed"].astype(bool) if "oil_confirmed" in s else pd.Series(False, index=s.index)
        res, _ = run_b.oil_tilt(ctx, s["escalation_z"], s["confirmed"].astype(bool) & ~oil, oil, tilt_w)
        return res.net_ret

    def min3(s):
        return run_b.timed(ctx, s["escalation_z"], s["confirmed"].astype(bool))[1].net_ret

    rows = ctx["rows"]
    rows_p = (shocks.composite_rows(cfg, proc, "contract_days_placebo.parquet", "contract_changes_placebo.parquet",
                                    placebo=True)
              if (proc / "contract_days_placebo.parquet").exists() else None)
    rev = lambda r: r.assign(z=-r["z"], z_early=-r["z_early"])
    out = []
    for name, fn, prep in (("b2_oil_tilt", b2, lambda r: r),
                           ("pm_timed_min3events", min3, lambda r: shocks.min_events_filter(r, n_ev))):
        sig = shocks.build_signals(prep(rows), cfg).set_index("day")
        out.append(_row("actual", fn(sig), strategy=name))
        cols = [c for c in ("escalation_z", "confirmed", "oil_confirmed") if c in sig]
        for seed in range(n_shuffle):
            out.append(_row("placebo_a_shuffle", fn(_shuffle_within_month(sig[cols], seed)), strategy=name, seed=seed))
        if rows_p is not None:
            out.append(_row("placebo_b_random_contracts", fn(shocks.build_signals(prep(rows_p), cfg).set_index("day")),
                            strategy=name))
        out.append(_row("placebo_c_reversed", fn(shocks.build_signals(prep(rev(rows)), cfg).set_index("day")),
                        strategy=name))
        log.info("posthoc placebos done: %s", name)
    return pd.DataFrame(out)


def posthoc_a(ctx: dict, frozen: dict, n_shuffle: int = 100) -> pd.DataFrame:
    """Placebos (a), (b), (c) for the a posteriori A additions of 2026-10-03: A1 with weekly
    rebalancing, and the D30 gated rule (frozen components and coefficients, 20-day rebalancing,
    applied to the placebo signals without re-estimation)."""
    cfg = ctx["cfg"]
    proc = rpath("processed", cfg)
    hl = cfg["smoothing"]["ewma_halflife_days"]
    specs = [("A1_theory_with_dollar_weekly", "A1", {"rebalance": "weekly"})]
    for v, comp in frozen.items():
        if comp:
            specs.append((f"{v}_gated20_frozen", v, {"rebalance": 20, "components": comp}))
    out = []
    for name, variant, kw in specs:
        sigs = ctx["sig10"] if variant.startswith("A2") else ctx["sig50"]
        ev = lambda s=None, sign=1.0: run_a.evaluate(ctx, variant, False, s, sign, **kw).net_ret
        out.append(_row("actual", ev(), strategy=name))
        for seed in range(n_shuffle):
            sh = {k: _shuffle_within_month(v.to_frame("z"), seed * 1000 + i)["z"] for i, (k, v) in enumerate(sigs.items())}
            out.append(_row("placebo_a_shuffle", ev(sh), strategy=name, seed=seed))
        if (proc / "theme_index_placebo.parquet").exists():
            pz = A.cell_signal(pd.read_parquet(proc / "theme_index_placebo.parquet"), hl)
            rng = np.random.default_rng(7)
            out.append(_row("placebo_b_random_contracts", ev({k: pz * rng.choice([-1.0, 1.0]) for k in sigs}),
                            strategy=name))
        out.append(_row("placebo_c_reversed", ev(sign=-1.0), strategy=name))
        log.info("posthoc placebos done: %s", name)
    return pd.DataFrame(out)


# ------------------------------------------------------------------------- Strategy A
def strategy_a(ctx: dict, variant: str = "A1", dollar_neutral: bool = False,
               n_shuffle: int = 100, n_loeo: int = 10) -> pd.DataFrame:
    cfg = ctx["cfg"]
    proc = rpath("processed", cfg)
    hl = cfg["smoothing"]["ewma_halflife_days"]
    sigs = ctx["sig10"] if variant.startswith("A2") else ctx["sig50"]
    kw = {"variant": variant, "dollar_neutral": dollar_neutral}
    out = [_row("actual", run_a.evaluate(ctx, variant, dollar_neutral).net_ret, **kw)]
    # (a) shuffle each cell signal within month (independently per cell)
    for seed in range(n_shuffle):
        sh = {}
        for i, (k, v) in enumerate(sigs.items()):
            sh[k] = _shuffle_within_month(v.to_frame("z"), seed * 1000 + i)["z"]
        out.append(_row("placebo_a_shuffle", run_a.evaluate(ctx, variant, dollar_neutral, sh).net_ret,
                        seed=seed, **kw))
    # (b) every used cell replaced by the placebo cell (random OTHER contracts), random sign per cell
    if (proc / "theme_index_placebo.parquet").exists():
        pz = A.cell_signal(pd.read_parquet(proc / "theme_index_placebo.parquet"), hl)
        rng = np.random.default_rng(7)
        pb = {k: pz * rng.choice([-1.0, 1.0]) for k in sigs}
        out.append(_row("placebo_b_random_contracts", run_a.evaluate(ctx, variant, dollar_neutral, pb).net_ret, **kw))
    # (c) reversed signs
    out.append(_row("placebo_c_reversed", run_a.evaluate(ctx, variant, dollar_neutral, sign=-1.0).net_ret, **kw))
    # EWMA half-life grid and equal weights
    idx_file = "theme_index_v10k.parquet" if variant.startswith("A2") else "theme_index.parquet"
    idx = pd.read_parquet(proc / idx_file)
    for h in cfg["smoothing"]["ewma_halflife_grid"]:
        s = A.all_cell_signals(idx, h)
        out.append(_row("halflife", run_a.evaluate(ctx, variant, dollar_neutral, s).net_ret, halflife=h, **kw))
    s_ew = A.all_cell_signals(idx.assign(d_vw=idx["d_ew"]), hl)
    out.append(_row("equal_weights", run_a.evaluate(ctx, variant, dollar_neutral, s_ew).net_ret, **kw))
    # Leave one event out on the cells the variant uses
    rows, _ = indices.load_rows(cfg, "contract_days_v10k.parquet" if variant.startswith("A2") else "contract_days.parquet")
    used = A.variant_cells(variant, set(sigs), ctx["kept"])
    in_use = rows[[(z, t) in used for z, t in zip(rows["zone"], rows["theme"])]]
    top = in_use.groupby("event_key")["vol1d"].sum().sort_values(ascending=False).head(n_loeo).index
    for ev in top:
        s = A.all_cell_signals(indices.dense_index(rows[rows["event_key"] != ev], cfg), hl)
        out.append(_row("leave_one_event_out", run_a.evaluate(ctx, variant, dollar_neutral, s).net_ret,
                        event=ev, **kw))
    return pd.DataFrame(out)
