"""Sanity checks of the D30 gated 20-day rule (final review, 2026-10-03). No rule is changed.

1. Phase robustness: the frozen rule rebalanced every 20 trading days, for each of the 20
   possible start offsets.
2. Positions: days long / short USD and number of sign changes, 2024-2025 and 2026; monthly
   P&L in 2026.
3. Static / timing decomposition (method of D25), and an ex post benchmark holding the 2026
   average position through 2026.
4. Effective-sample regression: one series (dollar basket), non-overlapping 20-day returns,
   OLS with small-sample t statistics, 2024-2025 and 2026.
Outputs in results/strategy_a/d30_checks/.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

from src.backtest import metrics
from src.common import get_logger, load_config, rpath
from src.strategies import run_a
from src.strategies import strategy_a as A

log = get_logger("d30_checks")
N = 20


def _periods(cfg):
    return {"2024-2025": (cfg["sample"]["start"], cfg["sample"]["train_end"]),
            "2026": (cfg["sample"]["test_start"], cfg["sample"]["end"]),
            "2024-2026": (cfg["sample"]["start"], cfg["sample"]["end"])}


def run(cfg: dict | None = None) -> dict:
    cfg = cfg or load_config()
    res_dir = rpath("results", cfg) / "strategy_a"
    out = res_dir / "d30_checks"
    out.mkdir(parents=True, exist_ok=True)
    g20 = pd.read_csv(res_dir / "gate20_estimation.csv")
    frozen = {v: dict(zip(g["regressor"], g["coef"])) for v, g in g20[g20["passes_gate"]].groupby("variant")}
    if "A1" not in frozen:
        log.info("no A1 component passes the 20-day gate: nothing to check")
        return {}
    comp = frozen["A1"]
    ctx = run_a.prepare(cfg)
    days, rx = ctx["days"], ctx["rx"].reindex(ctx["days"])
    per = _periods(cfg)

    # 1. Phase robustness.
    rows, results = [], {}
    for k in range(N):
        res = run_a.evaluate(ctx, "A1", False, rebalance=N, components=comp, offset=k)
        results[k] = res
        row = {"offset": k}
        for lab, (a, b) in per.items():
            row[f"sharpe_{lab}"] = metrics.perf_stats(res.net_ret.loc[a:b]).get("sharpe")
        rows.append(row)
    phase = pd.DataFrame(rows)
    phase.to_csv(out / "phase.csv", index=False)

    # 2. Positions of the published version (offset 0).
    res0 = results[0]
    w = res0.weights.reindex(days).fillna(0.0)
    usd = -w.sum(axis=1)                       # > 0: long USD against the G10 basket
    pos = []
    for lab in ("2024-2025", "2026"):
        a, b = per[lab]
        u = usd.loc[a:b]
        sgn = np.sign(u[u != 0])
        pos.append({"period": lab, "days": len(u), "share_long_usd": float((u > 0).mean()),
                    "share_short_usd": float((u < 0).mean()), "share_flat": float((u == 0).mean()),
                    "sign_changes": int((sgn.diff().fillna(0) != 0).sum()),
                    "rebalances": int(len(days[::N][(days[::N] >= a) & (days[::N] <= b)]))})
    pd.DataFrame(pos).to_csv(out / "positions.csv", index=False)
    a26, b26 = per["2026"]
    monthly = pd.DataFrame({"net": res0.net_ret.loc[a26:b26].resample("ME").sum(),
                            "gross": res0.gross_ret.loc[a26:b26].resample("ME").sum(),
                            "usd_position_month_end": usd.loc[a26:b26].resample("ME").last()})
    monthly.index = monthly.index.strftime("%Y-%m")
    monthly.rename_axis("month").to_csv(out / "monthly_2026.csv")

    # 3. Static / timing decomposition (gross P&L), and the ex post 2026-average benchmark.
    r = rx.fillna(0.0)
    w_bar = w.loc[:cfg["sample"]["train_end"]].mean()
    w_bar26 = w.loc[a26:b26].mean()
    # Direction benchmark: the 2026 average USD direction held at full size (Sharpe is scale-free).
    direction = -1.0 if -w_bar26.sum() > 0 else 1.0      # long USD = short the G10 basket
    parts = {"total": (w.shift(1) * r).sum(axis=1), "static": (r * w_bar).sum(axis=1),
             "timing": ((w.shift(1) - w_bar) * r).sum(axis=1),
             "ex_post_2026_average_position": (r * w_bar26).sum(axis=1),
             "ex_post_2026_average_direction": direction * r.mean(axis=1)}
    dec = []
    for part, ret in parts.items():
        for lab in ("2024-2025", "2026"):
            if part.startswith("ex_post") and lab != "2026":
                continue
            a, b = per[lab]
            st = metrics.perf_stats(ret.loc[a:b])
            dec.append({"part": part, "period": lab, "sharpe": st.get("sharpe"), "ann_mean": st.get("ann_mean"),
                        "ann_vol": st.get("ann_vol")})
    dec = pd.DataFrame(dec)
    dec["usd_direction_of_2026_average"] = "long USD" if -w_bar26.sum() > 0 else "short USD"
    dec.to_csv(out / "decomposition.csv", index=False)

    # 4. Effective-sample regression on the dollar basket.
    comps = A.pair_components(ctx["sig50"], ctx["days_warm"], A.variant_cells("A1", set(ctx["sig50"]), ctx["kept"]),
                              ctx["regime"], True, ctx["debt"])
    x_all = sum(comps[k] * c for k, c in comp.items()).loc[days].mean(axis=1)
    basket = rx.mean(axis=1)                   # long the G10 basket against USD
    y_all = basket.rolling(N).sum().shift(-N)  # next 20 trading days, aligned on t
    eff = []
    for lab in ("2024-2025", "2026"):
        a, b = per[lab]
        for k in range(N):
            t_idx = days[k::N]
            t_idx = t_idx[(t_idx >= a) & (t_idx <= b)]
            d = pd.DataFrame({"y": y_all.reindex(t_idx), "x": x_all.reindex(t_idx)}).dropna()
            d = d[d.index + pd.tseries.offsets.BDay(N) <= pd.Timestamp(b)] if lab == "2024-2025" else d
            if len(d) < 4 or d["x"].std() == 0:
                continue
            fit = sm.OLS(d["y"], sm.add_constant(d["x"])).fit()
            eff.append({"period": lab, "offset": k, "n": len(d), "coef": fit.params["x"], "t": fit.tvalues["x"],
                        "p": fit.pvalues["x"]})
    eff = pd.DataFrame(eff)
    eff.to_csv(out / "effective_sample.csv", index=False)
    log.info("D30 checks written to %s", out)
    return {"phase": phase, "decomposition": dec, "effective": eff}


if __name__ == "__main__":
    run()
