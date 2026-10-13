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
import numpy as np

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
        ("strategy_b_exposure.csv", lambda p, r: pd.read_csv(r / "strategy_b" / "exposure.csv", index_col=0, parse_dates=True),
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

        # Added 2026-10-10 for the HTML page (reporting; every source already exists in results/)
        ("pm_summary.csv", _pm_summary, "Markets with trades, market-days and traded volume by platform",
         "counts, USD billions", "11.2 (2)"),
        ("coverage_cells_v10k.csv", lambda p, r: pd.read_csv(r / "coverage_cells_v10k.csv"),
         "Coverage per cell at the USD 10k volume threshold (the cells of A2)", "shares in [0, 1], USD millions", "11.2 (2)"),
        ("confirmed_shocks.csv", _confirmed_shocks,
         "Confirmed shocks of the global geopolitical index with the contracts and volume behind each",
         "standard deviations, counts, USD", "11.2 (5)"),
        ("em_universe.csv", _em_universe, "EM universe screen (Ilzetzki-Reinhart-Rogoff fine codes, D23)",
         "codes, flags", "11.2 (5)"),
        ("strategy_b_returns_without_event.csv",
         lambda p, r: pd.read_parquet(r / "strategy_b" / "returns_pm_timed_without_event.parquet"),
         "Daily net returns of the PM overlay rebuilt without the event of the best month (D29)", "decimal returns", "11.2 (5)"),
        ("base_carry_long_history.csv", lambda p, r: pd.read_csv(r / "strategy_b" / "base_carry_long_history.csv"),
         "Base EM carry over the long history (crash-risk premise)", "annualised decimals", "11.2 (5)"),
        ("base_carry_long_history_returns.csv",
         lambda p, r: pd.read_parquet(r / "strategy_b" / "returns_long_history.parquet"),
         "Daily net returns of the base EM carry over the long history", "decimal returns", "11.2 (5)"),
        ("key_month_check.csv", lambda p, r: pd.read_csv(r / "strategy_b" / "key_month_check.csv"),
         "D29 check: gap between PM timing and the base carry, the best month and the event behind it",
         "Sharpe ratios, decimal returns", "11.2 (5)"),
        ("decomposition_static_timing.csv", lambda p, r: pd.read_csv(r / "strategy_a" / "decomposition_static_timing.csv"),
         "D25 check: static and timing decomposition of A1 and A2 (gross)", "annualised decimals", "11.2 (4)"),
        ("gate_estimation.csv", lambda p, r: pd.read_csv(r / "strategy_a" / "gate_estimation.csv"),
         "Spec gated rule: 1-day coefficients on 2024-2025 and the |t| > 3 gate", "coefficients, t-statistics", "11.2 (4)"),
        ("fiscal_regime_days.csv", _fiscal_regime_days,
         "Days in fiscal dominance (D15 indicator) by zone and year", "counts, shares", "11.2 (4)"),
        ("momentum_benchmarks.csv",
         lambda p, r: pd.read_csv(r / "notes" / "strategy_a_explained" / "c2_benchmarks.csv"),
         "Dollar time-series momentum benchmarks through A1's construction (diagnostic)", "annualised decimals", "11.2 (7)"),
        ("momentum_regressions.csv",
         lambda p, r: pd.read_csv(r / "notes" / "strategy_a_explained" / "c3_regressions.csv"),
         "Regressions of A1 on the momentum benchmarks (Newey-West)", "betas, t-statistics, annualised alpha", "11.2 (7)"),

        # Worked example of the signal chain for the page (illustration; nothing here is used by a rule)
        ("walk_contract_info.csv", _walk_contract_info,
         "The deadline contract used by the page's worked example: the one with the most eligible days in the "
         "global geopolitics cell", "text, dates, counts", "11.2 (3)"),
        ("hazard_example.csv", _hazard_example,
         "That contract over its life: traded probability, days to the deadline and implied hazard rate", "probability, days, per year", "11.2 (2)"),
        ("walk_contract.csv", _walk_contract,
         "Twelve eligible days of that contract around its largest standardised move: price, hazard rate, change, "
         "own volatility, signed z, volume weight in the cell, contribution, and the cell's change and index",
         "mixed (see columns)", "11.2 (3)"),
        ("signal_chain_a.csv", _signal_chain_a,
         "Strategy A's signal chain on every trading day: scaled signals of the US monetary and fiscal cells, "
         "regime, forecast y and the realised USD position of A1", "standard deviations, multiples of capital", "11.2 (4)"),
        ("walk_cell_a.csv", _walk_cell_a,
         "Strategy A's signal chain on the trading days around the hawkish Fed cut of December 2024: cell changes, "
         "smoothed and scaled signals, fiscal regime, forecast y and the realised USD position of A1",
         "standard deviations, multiples of capital", "11.2 (4)"),
        ("walk_geo.csv", _walk_geo,
         "Strategy B's overlay on the days around the Israel-Iran war of June 2025: cell change, index, escalation, "
         "z-score, shocks, month-end weight and exposure", "standard deviations, shares", "11.2 (5)"),
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


def _pm_summary(p, r):
    daily = pd.read_parquet(p / "pm_daily.parquet", columns=["platform", "platform_id", "snap_date", "volume_usd"])
    return daily.groupby("platform").agg(markets=("platform_id", "nunique"), market_days=("snap_date", "size"),
                                         volume_usd_bn=("volume_usd", lambda s: s.sum() / 1e9)).reset_index()


def _confirmed_shocks(p, r):
    g = pd.read_parquet(p / "geo_signals.parquet")
    g = g[g["confirmed"].astype(bool)]
    return g[["day", "d", "d_early", "n_contracts", "volume_usd"]].reset_index(drop=True)


def _em_universe(p, r):
    ex = pd.read_csv(rpath("manual") / "em_exclusions.csv", comment="#")
    ex["primary_universe"] = ex["exclude"] == 0
    ex["coarse12_variant"] = ex["exclude_variant_coarse12"] == 0
    return ex[["ccy", "irr_fine_code", "irr_label", "primary_universe", "coarse12_variant"]]


def _fiscal_regime_days(p, r):
    f = pd.read_csv(r / "strategy_a" / "fiscal_regime.csv", index_col=0, parse_dates=True)
    rows = []
    for zone in f.columns:
        for year, g in f[zone].groupby(f.index.year):
            rows.append({"zone": zone, "year": int(year), "days_measured": int(g.notna().sum()),
                         "days_in_regime": int((g == 1).sum())})
    out = pd.DataFrame(rows)
    out["share"] = out["days_in_regime"] / out["days_measured"].where(out["days_measured"] > 0)
    return out


_WALK = {}


def _walk_base(p):
    """Contract-day panel, stored changes and the example contract (cached for the builders below)."""
    if "cd" not in _WALK:
        cd = pd.read_parquet(p / "contract_days.parquet")
        cd["day"] = pd.to_datetime(cd["day"])
        ch = pd.read_parquet(p / "contract_changes.parquet")
        ch["day"] = pd.to_datetime(ch["day"])
        geo = cd[(cd["zone"] == "GLOBAL") & (cd["theme"] == "GEOPOLITICS")]
        hz = geo[geo["unit"] == "hazard"]
        cid = hz.groupby("contract_id")["eligible"].sum().idxmax()     # rule: most eligible days, no hand-picking
        _WALK.update(cd=cd, ch=ch, geo=geo, cid=cid)
    return _WALK


def _walk_contract_info(p, r):
    b = _walk_base(p)
    lab = pd.read_parquet(p / "contracts_classified.parquet",
                          columns=["platform", "platform_id", "title", "event_key", "direction", "closes_at", "resolves_at"])
    platform, pid = b["cid"].split(":", 1)
    row = lab[(lab["platform"] == platform) & (lab["platform_id"] == pid)].iloc[0]
    life = b["geo"][b["geo"]["contract_id"] == b["cid"]].sort_values("day")
    close = pd.Timestamp(row["closes_at"] if pd.notna(row["closes_at"]) else row["resolves_at"])
    return pd.DataFrame([{"contract_id": b["cid"], "platform": platform, "title": row["title"], "event_key": row["event_key"],
                          "sign": int(row["direction"]), "deadline": close.strftime("%Y-%m-%d"),
                          "first_day": life["day"].min().strftime("%Y-%m-%d"), "last_day": life["day"].max().strftime("%Y-%m-%d"),
                          "days": int(len(life)), "eligible_days": int(life["eligible"].sum())}])


def _hazard_example(p, r):
    b = _walk_base(p)
    life = b["geo"][b["geo"]["contract_id"] == b["cid"]].sort_values("day")
    out = life[["day", "px", "ttr_days", "value", "eligible", "stale"]].rename(columns={"value": "hazard_per_year"})
    ch = b["ch"][b["ch"]["contract_id"] == b["cid"]][["day", "dv", "sd", "z"]]
    out = out.merge(ch, on="day", how="left")
    out.loc[~out["eligible"], ["dv", "sd", "z"]] = np.nan     # a change counts only on eligible days (indices.aggregate)
    out["day"] = out["day"].dt.strftime("%Y-%m-%d")
    return out.reset_index(drop=True)


def _walk_contract(p, r):
    b = _walk_base(p)
    life = b["geo"][b["geo"]["contract_id"] == b["cid"]]
    c = b["ch"][b["ch"]["contract_id"] == b["cid"]].merge(life[["day", "px", "ttr_days", "vol7d", "eligible"]], on="day")
    c = c.sort_values("day")
    c["prev_value"] = c["value"].shift(1)
    c["gap_days"] = c["day"].diff().dt.days
    c = c[c["eligible"]].reset_index(drop=True)
    pos = int(c["z"].abs().idxmax())
    win = c.iloc[max(0, pos - 6):pos + 6].copy()
    # the other contributors of the cell on those days (same rule as indices.aggregate: eligible rows with a change)
    rows = (b["geo"][b["geo"]["eligible"] & b["geo"]["day"].isin(win["day"])]
            .merge(b["ch"][["contract_id", "day", "z"]], on=["contract_id", "day"]))
    cell = rows.groupby("day").agg(cell_vol7d=("vol7d", "sum")).reset_index()
    win = win.merge(cell, on="day", how="left")
    win["weight_share"] = win["vol7d"] / win["cell_vol7d"]
    win["contribution"] = win["z"] * win["weight_share"]
    idx = pd.read_parquet(p / "theme_index.parquet")
    idx["day"] = pd.to_datetime(idx["day"])
    g = idx[(idx["zone"] == "GLOBAL") & (idx["theme"] == "GEOPOLITICS")][["day", "d_vw", "n_contracts", "index_vw"]]
    win = win.merge(g, on="day", how="left")
    win["day"] = win["day"].dt.strftime("%Y-%m-%d")
    return win[["day", "px", "ttr_days", "value", "prev_value", "gap_days", "dv", "sd", "sign", "z", "vol7d", "cell_vol7d",
                "weight_share", "contribution", "n_contracts", "d_vw", "index_vw"]].rename(columns={"value": "hazard_per_year"})


def _chain_a(p, r):
    """Strategy A's signal chain on every trading day of the sample (the walkthrough slices it)."""
    if "chain_a" in _WALK:
        return _WALK["chain_a"]
    from src.strategies.strategy_a import MIN_ACTIVE, cell_signal
    cfg = load_config()
    hl = cfg["smoothing"]["ewma_halflife_days"]
    idx = pd.read_parquet(p / "theme_index.parquet")
    idx["day"] = pd.to_datetime(idx["day"])

    def chain(zone, theme):
        """The three lines of strategy_a.cell_signal, kept apart so that the page can show them."""
        cell = idx[(idx["zone"] == zone) & (idx["theme"] == theme)]
        c = cell.sort_values("day").set_index("day")
        active = c["n_contracts"] > 0
        s = c["d_vw"].where(active, 0.0).ewm(halflife=hl).mean()
        n_active = active.cumsum().shift(1).fillna(0)
        sd = s.where(n_active > 0).expanding(min_periods=MIN_ACTIVE).std().shift(1)
        z = (s / sd).where(n_active >= MIN_ACTIVE).fillna(0.0)
        ref = cell_signal(cell, hl)
        assert np.allclose(z.values, ref.values, equal_nan=True), "walkthrough chain differs from strategy_a.cell_signal"
        return pd.DataFrame({"d": c["d_vw"], "n": c["n_contracts"], "s": s, "sd": sd, "Z": z})

    mon, fis = chain("US", "MONETARY"), chain("US", "FISCAL_POLITICAL")
    w = pd.read_parquet(r / "strategy_a" / "weights_A1_theory_with_dollar.parquet")
    days = w.index
    reg = pd.read_csv(r / "strategy_a" / "fiscal_regime.csv", index_col=0, parse_dates=True)["US"]
    R = reg.reindex(days, method="ffill").fillna(0.0)
    m, f = mon.reindex(days, method="ffill"), fis.reindex(days, method="ffill")
    y = -m["Z"] - (1 - 2 * R) * f["Z"]
    out = pd.DataFrame({"day": days, "d_mon": mon["d"].reindex(days).fillna(0.0).values,
                        "s_mon": m["s"].values, "sd_mon": m["sd"].values, "Z_mon": m["Z"].values,
                        "d_fis": fis["d"].reindex(days).fillna(0.0).values, "Z_fis": f["Z"].values, "R": R.values,
                        "y": y.values, "usd_position": (-w.loc[days].sum(axis=1)).values,
                        "gross": w.loc[days].abs().sum(axis=1).values})
    _WALK["chain_a"] = out
    return out


def _signal_chain_a(p, r):
    out = _chain_a(p, r)[["day", "Z_mon", "Z_fis", "R", "y", "usd_position"]].copy()
    out["day"] = out["day"].dt.strftime("%Y-%m-%d")
    return out


def _walk_cell_a(p, r):
    full = _chain_a(p, r)
    anchor = pd.Timestamp(next(a["date"] for a in ANNOTATIONS if a["label"] == "Hawkish Fed cut"))
    out = full[(full["day"] >= anchor - pd.Timedelta(days=9)) & (full["day"] <= anchor + pd.Timedelta(days=9))].copy()
    out["day"] = out["day"].dt.strftime("%Y-%m-%d")
    return out.reset_index(drop=True)


def _walk_geo(p, r):
    gs = pd.read_parquet(p / "geo_signals.parquet")
    gs["day"] = pd.to_datetime(gs["day"])
    anchor = pd.Timestamp(next(a["date"] for a in ANNOTATIONS if a["label"] == "Israel strikes Iran"))
    ex = pd.read_csv(r / "strategy_b" / "exposure.csv", index_col=0, parse_dates=True)
    win = gs[(gs["day"] >= anchor - pd.Timedelta(days=4)) & (gs["day"] <= anchor + pd.Timedelta(days=25))].set_index("day")
    win = win.join(ex[["w", "w_escalation", "shock"]])
    win = win.reset_index()
    win["day"] = win["day"].dt.strftime("%Y-%m-%d")
    return win[["day", "d", "n_contracts", "volume_usd", "sigma", "index", "escalation", "escalation_z", "shock_raw", "confirmed",
                "w_escalation", "shock", "w"]]


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
            if isinstance(df.index, pd.DatetimeIndex):
                df = df.rename_axis("date")   # the first column of every time series is named "date"
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
