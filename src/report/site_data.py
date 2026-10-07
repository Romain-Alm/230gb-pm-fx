"""Export everything the HTML page needs (spec 11.2, DECISIONS D21) to results/site_data/.

Each file is CSV (tables, time series) or JSON (annotations). `results/site_data/README.md`
is generated from the registry below: file, content, columns (read from the written file),
units and the spec 11.2 section it supports. Files whose source does not exist yet (strategy
results before the market data arrives) are listed as pending.
"""
from __future__ import annotations

import json

import pandas as pd

from src.backtest.metrics import drawdown
from src.common import get_logger, load_config, rpath

log = get_logger("site_data")

ANNOTATIONS = [  # illustrations only (spec 6.6); never used by a trading rule
    {"date": "2024-07-13", "label": "Assassination attempt on Trump", "cells": ["US/FISCAL_POLITICAL"]},
    {"date": "2024-08-02", "label": "Weak July payrolls", "cells": ["US/MONETARY"]},
    {"date": "2024-10-01", "label": "Iran missile attack on Israel", "cells": ["GLOBAL/GEOPOLITICS"]},
    {"date": "2024-11-06", "label": "US election", "cells": ["US/FISCAL_POLITICAL"]},
    {"date": "2024-12-19", "label": "Hawkish Fed cut", "cells": ["US/MONETARY"]},
    {"date": "2025-04-02", "label": "Liberation Day tariffs", "cells": ["GLOBAL/GEO_TRADE"]},
    {"date": "2025-06-13", "label": "Israel strikes Iran", "cells": ["GLOBAL/GEOPOLITICS"]},
    {"date": "2025-06-22", "label": "US strikes on Fordow", "cells": ["GLOBAL/GEOPOLITICS"]},
    {"date": "2025-08-01", "label": "Payroll revisions", "cells": ["US/MONETARY"]},
    {"date": "2025-10-04", "label": "Gaza deal; Takaichi wins LDP vote", "cells": ["GLOBAL/GEOPOLITICS"]},
]


def _reg():
    """(output file, builder, description, units, spec section)."""
    return [
        ("theme_indices.csv", _theme_indices, "Daily theme indices per (zone, theme) cell and composites",
         "index levels and daily changes in standard deviations of contract changes; n_contracts count", "11.2 (3)"),
        ("coverage_cells.csv", lambda p, r: pd.read_csv(r / "coverage_cells.csv"),
         "Coverage per cell, training and test shares, keep flag (USD 50k rule)", "shares in [0, 1], USD millions", "11.2 (2)"),
        ("coverage_quarterly.csv", lambda p, r: pd.read_csv(r / "coverage.csv"),
         "Coverage per cell and quarter (heatmap)", "share_days_covered in [0, 1]", "11.2 (2)"),
        ("classification_summary.csv", _class_summary, "Classified contracts by platform and theme",
         "counts", "11.2 (2)"),
        ("classification_examples.csv", _class_examples, "Example contracts with their labels and the rule used",
         "direction +1/-1/0", "11.2 (2)"),
        ("geo_signals.csv", lambda p, r: pd.read_parquet(p / "geo_signals.parquet"),
         "Global geopolitical index for Strategy B: daily change, escalation, z-scores, shocks",
         "standard deviations; booleans", "11.2 (5)"),
        ("weekend_changes.csv", lambda p, r: pd.read_parquet(p / "weekend_changes.parquet"),
         "Weekend changes (Friday 17:00 to Sunday 17:00 New York) per cell", "standard deviations", "11.2 (4)"),
        ("strategy_a_returns.csv", lambda p, r: pd.read_parquet(r / "strategy_a" / "returns.parquet"),
         "Daily returns of every Strategy A variant (net; '_gross' columns before costs)", "decimal returns", "11.2 (4)"),
        ("strategy_a_performance.csv", lambda p, r: pd.read_csv(r / "strategy_a" / "performance.csv"),
         "Performance statistics by variant and period", "annualised decimals", "11.2 (4)"),
        ("strategy_a_tstats.csv", lambda p, r: pd.read_csv(r / "strategy_a" / "diagnostics.csv"),
         "Panel regression coefficients and Driscoll-Kraay t-statistics (theory predicts positive)", "t-statistics", "11.2 (4)"),
        ("strategy_a_weekend_gap.csv", lambda p, r: pd.read_csv(r / "weekend" / "weekend_gap_regressions.csv"),
         "Weekend gap regressions", "t-statistics", "11.2 (4)"),
        ("strategy_b_returns.csv", lambda p, r: pd.read_parquet(r / "strategy_b" / "returns.parquet"),
         "Daily returns: base carry, PM-timed, VIX-timed and variants (net; '_gross' before costs)", "decimal returns", "11.2 (5)"),
        ("strategy_b_exposure.csv", lambda p, r: pd.read_csv(r / "strategy_b" / "exposure.csv"),
         "Exposure w(t), escalation component and shock days (PM and VIX timing)", "w in [0, 1]", "11.2 (5)"),
        ("strategy_b_performance.csv", lambda p, r: pd.read_csv(r / "strategy_b" / "performance.csv"),
         "Performance statistics by strategy and period", "annualised decimals", "11.2 (5)"),
        ("drawdowns.csv", _drawdowns, "Drawdown paths of every strategy", "decimal (negative)", "11.2 (5), (6)"),
        ("robustness_grid_b.csv", lambda p, r: pd.read_csv(r / "strategy_b" / "grid.csv"),
         "Strategy B full parameter grid (shock threshold, re-risk days, cut level)", "annualised decimals", "11.2 (7)"),
        ("cost_sensitivity_b.csv", lambda p, r: pd.read_csv(r / "strategy_b" / "cost_sensitivity.csv"),
         "Strategy B performance at 0.5x to 3x costs", "annualised decimals", "11.2 (7)"),
        ("robustness_a.csv", lambda p, r: pd.read_csv(r / "robustness" / "strategy_a.csv"),
         "Strategy A placebos, half-life grid, equal weights, leave-one-event-out", "annualised decimals", "11.2 (7)"),
        ("robustness_b.csv", lambda p, r: pd.read_csv(r / "robustness" / "strategy_b.csv"),
         "Strategy B placebos, thresholds, equal weights, leave-one-event-out", "annualised decimals", "11.2 (7)"),
        ("subperiods.csv", lambda p, r: pd.read_csv(r / "robustness" / "subperiods.csv"),
         "Performance by calendar year", "annualised decimals", "11.2 (7)"),
        ("risk_downside_beta.csv", lambda p, r: pd.read_csv(r / "risk" / "downside_beta.csv"),
         "Normal and downside betas (Lettau, Maggiori, Weber), weekly", "betas", "11.2 (6)"),
        ("risk_betas.csv", lambda p, r: pd.read_csv(r / "risk" / "betas_weekly.csv"),
         "Weekly betas to equity, VIX, Brent, dollar and carry factors", "betas, t-statistics", "11.2 (6)"),
        ("risk_worst_drawdowns.csv", lambda p, r: pd.read_csv(r / "risk" / "worst_drawdowns.csv"),
         "Ten worst drawdowns per strategy with dates and dominant news", "decimal depth, days", "11.2 (6)"),
        ("risk_concentration.csv", lambda p, r: pd.read_csv(r / "risk" / "concentration.csv"),
         "P&L concentration by currency and month, Herfindahl index", "shares, HHI", "11.2 (6)"),
        ("risk_conditional.csv", lambda p, r: pd.read_csv(r / "risk" / "conditional_performance.csv"),
         "Performance by VIX tercile, dollar month, Brent week, shock day, and tercile of the strategy's own "
         "average forward half-spread (liquidity)", "annualised decimals", "11.2 (6)"),
        ("risk_leverage.csv", lambda p, r: pd.read_csv(r / "risk" / "leverage.csv"),
         "Gross and net USD exposure (mean, median, 95th percentile, max), share of days the 3x gross and 30% "
         "per-pair caps bind (Strategy A), realised versus target volatility", "multiples of capital, shares, decimals",
         "11.2 (4), (5), (6)"),
        ("robustness_posthoc.csv", lambda p, r: pd.read_csv(r / "robustness" / "posthoc.csv"),
         "Placebos of the a posteriori additions (A1 weekly, D30, B2, D31)", "annualised decimals", "11.2 (7)"),
        ("d30_phase.csv", lambda p, r: pd.read_csv(r / "strategy_a" / "d30_checks" / "phase.csv"),
         "D30 check: net Sharpe for each of the 20 rebalancing start offsets", "Sharpe ratios", "11.2 (4)"),
        ("d30_positions.csv", lambda p, r: pd.read_csv(r / "strategy_a" / "d30_checks" / "positions.csv"),
         "D30 check: days long and short USD, sign changes, rebalances", "shares, counts", "11.2 (4)"),
        ("d30_monthly_2026.csv", lambda p, r: pd.read_csv(r / "strategy_a" / "d30_checks" / "monthly_2026.csv"),
         "D30 check: monthly P&L in 2026 and USD position", "decimal returns", "11.2 (4)"),
        ("d30_decomposition.csv", lambda p, r: pd.read_csv(r / "strategy_a" / "d30_checks" / "decomposition.csv"),
         "D30 check: static and timing decomposition, ex post benchmarks", "annualised decimals", "11.2 (4)"),
        ("d30_effective_sample.csv", lambda p, r: pd.read_csv(r / "strategy_a" / "d30_checks" / "effective_sample.csv"),
         "D30 check: non-overlapping 20-day OLS on the dollar basket, per phase", "coefficients, t-statistics", "11.2 (4)"),
        ("slide_a_cumulative.csv", lambda p, r: pd.read_csv(r / "figures" / "slides" / "data" / "slide_a_cumulative.csv"),
         "Slide figure a: cumulative net and gross returns of A1 and A2 (%)", "percent", "slides"),
        ("slide_b_cumulative.csv", lambda p, r: pd.read_csv(r / "figures" / "slides" / "data" / "slide_b_cumulative.csv"),
         "Slide figure b: cumulative net returns of base carry, PM and VIX overlays, D29 line (%)", "percent", "slides"),
        ("slide_coverage_heatmap.csv", lambda p, r: pd.read_csv(r / "figures" / "slides" / "data" / "slide_coverage_heatmap.csv"),
         "Slide figure c: 2024-2025 coverage share, zone x theme (%)", "percent", "slides"),
        ("slide_leadlag.csv", lambda p, r: pd.read_csv(r / "figures" / "slides" / "data" / "slide_leadlag.csv"),
         "Slide figure d: hourly lead-lag event studies, mean and 95% CI", "sd (PM) or decimal return (FX)", "slides"),
        ("slide_d30_phase.csv", lambda p, r: pd.read_csv(r / "figures" / "slides" / "data" / "slide_d30_phase.csv"),
         "Slide figure e: Sharpe of the D30 rule for the 20 rebalancing phases", "Sharpe ratios", "slides"),
        ("slide_b_composition.csv", lambda p, r: pd.read_csv(r / "figures" / "slides" / "data" / "slide_b_composition.csv"),
         "Slide figure f: average base-carry weight, share of gross and weekly Brent beta per currency", "decimals, betas", "slides"),

        ("risk_episodes.csv", lambda p, r: pd.read_csv(r / "risk" / "episodes.csv"),
         "Returns over named stress episodes", "decimal returns", "11.2 (6)"),
        ("a_vs_b_correlation.csv", lambda p, r: pd.read_csv(r / "risk" / "a_vs_b_correlation.csv"),
         "Correlation of A and B returns and drawdowns", "correlations", "11.2 (6)"),
    ]


def _theme_indices(p, r):
    idx = pd.read_parquet(p / "theme_index.parquet")
    return idx[["day", "zone", "theme", "index_vw", "index_ew", "d_vw", "n_contracts", "vol7d"]]


def _class_summary(p, r):
    lab = pd.read_parquet(p / "contracts_classified.parquet")
    lab["usable"] = (lab["direction"] != 0) | lab["partition"]
    return lab.groupby(["platform", "theme"]).agg(markets=("platform_id", "size"),
                                                  events=("event_key", "nunique"),
                                                  usable=("usable", "sum")).reset_index()


def _class_examples(p, r):
    lab = pd.read_parquet(p / "contracts_classified.parquet")
    lab = lab[lab["theme"] != "OTHER"]
    ex = lab.groupby("theme").sample(12, random_state=1, replace=False) if lab.groupby("theme").size().min() >= 12         else lab.groupby("theme").head(12)
    ex["zones"] = ex["zones"].apply(lambda z: "|".join(z) if z is not None else "")
    return ex[["platform", "title", "theme", "zones", "direction", "partition", "unit", "bucket_value",
               "theme_rule", "direction_rule"]]


def _drawdowns(p, r):
    cols = {}
    for sub in ("strategy_a", "strategy_b"):
        f = r / sub / "returns.parquet"
        if f.exists():
            rets = pd.read_parquet(f)
            for c in rets.columns:
                if not c.endswith("_gross"):
                    cols[c] = drawdown(rets[c].dropna())
    if not cols:
        raise FileNotFoundError("no strategy returns yet")
    return pd.DataFrame(cols)


def build(cfg: dict | None = None) -> None:
    cfg = cfg or load_config()
    proc, res = rpath("processed", cfg), rpath("results", cfg)
    out = res / "site_data"
    out.mkdir(parents=True, exist_ok=True)
    lines = ["# Data for the HTML page (spec 11.2)", "",
             "Generated by `src/report/site_data.py` (DECISIONS D21). The page can be built from these",
             "files alone. Dates are ISO (YYYY-MM-DD); returns are daily decimal returns at the 16:00",
             "London snapshot; annualised statistics use 252 days. Event annotations are illustrations",
             "only (`annotations.json`).", "",
             "Status: files marked *pending* need the market data (strategy results) and appear after",
             "`run_all.py --stage strategies` (and robustness, risk).", "",
             "| File | Content | Columns | Units | Spec 11.2 section |", "|---|---|---|---|---|"]
    for fname, builder, desc, units, sec in _reg():
        try:
            df = builder(proc, res)
            df.to_csv(out / fname, index=isinstance(df.index, pd.DatetimeIndex))
            cols = (["date"] if isinstance(df.index, pd.DatetimeIndex) else []) + list(df.columns)
            lines.append(f"| `{fname}` | {desc} | {', '.join(map(str, cols))} | {units} | {sec} |")
        except (FileNotFoundError, KeyError):
            lines.append(f"| `{fname}` | {desc} (*pending*) | | {units} | {sec} |")
    (out / "annotations.json").write_text(json.dumps(ANNOTATIONS, indent=1), encoding="utf-8")
    lines.append("| `annotations.json` | Named events for hover tooltips (illustration only) | "
                 "date, label, cells | | 11.2 (3), (4) |")
    lines += ["", "Figures: `results/figures/` (analysis figures) and `results/figures/slides/` (presentation figures, "
              "1920 x 1080 PNG and SVG, no in-figure title; their data are the `slide_*.csv` files above)."]
    (out / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    log.info("site data written to %s", out)


if __name__ == "__main__":
    build()
