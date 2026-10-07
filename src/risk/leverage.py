"""Leverage and exposure report (assignment: "any use of leverage"). Reporting only.

For each main strategy and period: gross exposure (sum of absolute notional weights per unit
of capital) and net USD exposure (minus the sum of the weights: > 0 = long USD against the
basket), mean, median, 95th percentile and maximum; how often the caps of the volatility
target bind (Strategy A: 3x gross cap and 30% per-pair cap, measured on the daily targets
before the no-trade band; Strategy B has no such cap in its rule); realised volatility of net
returns against the 10% target.
Output: results/risk/leverage.csv
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.backtest import engine
from src.common import get_logger, load_config, rpath
from src.strategies import run_a
from src.strategies import strategy_a as A

log = get_logger("leverage")
STRATS_A = {"A1_theory_with_dollar": ("A1", None), "A2_theory_with_dollar": ("A2", None),
            "A1_theory_with_dollar_weekly": ("A1", "weekly")}
STRATS_B = ["base_carry", "pm_timed", "vix_timed", "b2_oil_tilt"]


def _periods(cfg):
    return {"2024-2025": (cfg["sample"]["start"], cfg["sample"]["train_end"]),
            "2026": (cfg["sample"]["test_start"], cfg["sample"]["end"]),
            "2024-2026": (cfg["sample"]["start"], cfg["sample"]["end"])}


def _stats(x: pd.Series, prefix: str) -> dict:
    return {f"{prefix}_mean": x.mean(), f"{prefix}_median": x.median(), f"{prefix}_p95": x.quantile(0.95),
            f"{prefix}_max": x.max()}


def run(cfg: dict | None = None) -> pd.DataFrame:
    cfg = cfg or load_config()
    res = rpath("results", cfg)
    a = cfg["strategy_a"]
    per = _periods(cfg)
    rets = pd.concat([pd.read_parquet(res / "strategy_a" / "returns.parquet"),
                      pd.read_parquet(res / "strategy_b" / "returns.parquet")], axis=1)

    flags = {}
    ctx = run_a.prepare(cfg)
    rx = ctx["rx"].reindex(ctx["days"])
    for name, (variant, rebalance) in STRATS_A.items():
        raw = A.raw_positions(run_a.forecast(ctx, variant), rx, cfg, False)
        f = engine.cap_flags(raw, rx, a["vol_target_annual"], a["cov_ewma_span_days"], a["gross_leverage_cap"],
                             a["single_pair_cap_share"])
        if rebalance == "weekly":
            days = ctx["days"]
            dec = pd.Series(days, index=days).groupby(days.to_period("W-FRI")).max().values
            f = f[f.index.isin(dec)]
        flags[name] = f

    rows = []
    for name in list(STRATS_A) + STRATS_B:
        sub = "strategy_a" if name in STRATS_A else "strategy_b"
        w = pd.read_parquet(res / sub / f"weights_{name}.parquet")
        target = a["vol_target_annual"] if name in STRATS_A else cfg["strategy_b"]["vol_target_annual"]
        for lab, (s, e) in per.items():
            ww = w.loc[s:e]
            gross, net = ww.abs().sum(axis=1), -ww.sum(axis=1)
            row = {"strategy": name, "period": lab, **_stats(gross, "gross"),
                   "net_usd_mean": net.mean(), **_stats(net.abs(), "abs_net_usd"),
                   "share_days_long_usd": float((net > 1e-9).mean()),
                   "realised_vol": float(rets[name].loc[s:e].std() * np.sqrt(252)), "target_vol": target}
            if name in flags:
                fl = flags[name].loc[s:e]
                row.update({"share_days_gross_cap": float(fl["gross_cap"].mean()) if len(fl) else np.nan,
                            "share_days_pair_cap": float(fl["pair_cap"].mean()) if len(fl) else np.nan,
                            "cap_days_measured": len(fl)})
            rows.append(row)
    out = pd.DataFrame(rows)
    (res / "risk").mkdir(parents=True, exist_ok=True)
    out.to_csv(res / "risk" / "leverage.csv", index=False)
    log.info("leverage report written")
    return out


if __name__ == "__main__":
    run()
