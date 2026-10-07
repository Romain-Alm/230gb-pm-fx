"""Markdown report with every key number, generated from the saved results.

    .venv/Scripts/python.exe -m src.report.summary_md              # definitive run -> results/RESULTS.md
    .venv/Scripts/python.exe -m src.report.summary_md preliminary  # free data -> results/preliminary_free/RESULTS.md
"""
from __future__ import annotations

import sys
from datetime import date

import numpy as np
import pandas as pd

from src.common import ROOT, get_logger, load_config

log = get_logger("summary_md")
INT = {"duration_days", "days_to_trough", "n_contracts", "contracts", "rerisk_days", "re-risk (days)",
       "n_obs", "n", "count", "days", "n_days", "n_down", "weekends", "active days"}
PCT = {"ann_mean", "ann_vol", "max_drawdown", "cost_drag_ann", "cum_return", "hit_rate", "depth",
       "share_train", "share_test", "share_of_abs", "worst_day"}


def _fmt(v, col):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ""
    if isinstance(v, (bool, np.bool_)):
        return "yes" if v else "no"
    if isinstance(v, (int, np.integer)):
        return f"{v:,}"
    if v is pd.NaT:
        return "ongoing"
    if isinstance(v, (float, np.floating)):
        if col in INT and float(v).is_integer():
            return f"{int(v):,}"
        if col in PCT:
            return f"{100 * v:.1f}%"
        if abs(v) >= 1000:
            return f"{v:,.0f}"
        return f"{v:.2f}" if abs(v) >= 0.01 or v == 0 else f"{v:.4f}"
    if isinstance(v, pd.Timestamp):
        return v.strftime("%Y-%m-%d")
    return str(v).replace("|", "/")


def table(df: pd.DataFrame, cols: list[str] | None = None, rename: dict | None = None) -> str:
    if df is None or len(df) == 0:
        return "_(no data)_\n"
    df = df[cols] if cols else df
    head = [str(rename.get(c, c) if rename else c) for c in df.columns]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(_fmt(r[c], c) for c in df.columns) + " |")
    return "\n".join(lines) + "\n"


def _read(path, **kw):
    try:
        return pd.read_parquet(path) if str(path).endswith(".parquet") else pd.read_csv(path, **kw)
    except FileNotFoundError:
        return None


def _pct(v, fmt="{:.1f}"):
    return "" if pd.isna(v) else (fmt.format(100 * v) + "%")


PERF_COLS = ["strategy", "period", "sharpe", "sharpe_t", "sharpe_ci", "ann_mean", "ann_vol", "max_drawdown",
             "hit_rate", "skew", "turnover_ann", "cost_drag_ann"]
PERF_NAMES = {"strategy": "strategy", "period": "period", "sharpe": "Sharpe", "sharpe_t": "Sharpe t",
              "sharpe_ci": "90% CI of the Sharpe (bootstrap)", "ann_mean": "annual return",
              "ann_vol": "annual vol", "max_drawdown": "max drawdown", "hit_rate": "positive days",
              "skew": "skew", "turnover_ann": "annual turnover", "cost_drag_ann": "annual cost"}
PERIOD_LABEL = {"in-sample": "2024-2025", "out-of-sample": "2026 (OOS)", "full": "2024-2026"}


def _ci(lo, hi):
    return [f"[{a:.2f}, {b:.2f}]" if pd.notna(a) else "" for a, b in zip(lo, hi)]


def perf_block(p: pd.DataFrame, names: list[str]) -> str:
    if p is None:
        return "_(no data)_\n"
    p = p[p["strategy"].isin(names)].copy()
    p["period"] = p["period"].map(PERIOD_LABEL)
    if "sharpe_ci90_low" in p:
        p["sharpe_ci"] = _ci(p["sharpe_ci90_low"], p["sharpe_ci90_high"])
    p["order"] = p["strategy"].map({n: i for i, n in enumerate(names)})
    p = p.sort_values(["order", "period"])
    return table(p, [c for c in PERF_COLS if c in p], PERF_NAMES)


GLOSSARY = [
    # (name, description, status)
    ("A1_theory_with_dollar", "A: US signal (MONETARY, FISCAL) with theory-given signs, G10 basket against USD, daily rebalancing", "primary, pre-registered (D2, D14)"),
    ("A1_theory_dollar_neutral", "A1 without the dollar leg: zero by construction (same signal on every pair)", "pre-registered"),
    ("A2_theory_with_dollar / _dollar_neutral", "A with every G10 cell at the USD 10k threshold, each active when it has contracts", "variant declared before any backtest (D14)"),
    ("A1+S, A2+S", "A1 or A2 plus geopolitics, tariffs and spillovers (the contracts of B's index)", "variants declared before any backtest (D14, D17)"),
    ("A3, A3+S", "cells that pass the spec's coverage rule; identical to A1 and A1+S", "declared (D14)"),
    ("*_gated_frozen", "spec rule: 1-day regression on 2024-2025, themes with t > 3 and the right sign, frozen coefficients", "spec 6.5 (ex ante rule)"),
    ("*_D12", "indices in demeaned probabilities instead of hazard rates", "declared variant (D12, D18)"),
    ("*_gross", "same strategy, before costs", "information"),
    ("A1_theory_with_dollar_weekly", "A1 rebalanced on the last trading day of each week", "a posteriori (freeze lifted, 2026-10-03)"),
    ("A1_gated20_frozen, A2_gated20_frozen", "gated rule at 20 days, estimated on 2024-2025, frozen, rebalanced every 20 days", "a posteriori, horizon chosen after the full-sample diagnostic (D30)"),
    ("*_cost0.5x", "costs at 0.5x the Bloomberg composite half-spread", "a posteriori scenario; the primary result stays at 1x"),
    ("base_carry", "B: EM carry, IRR 12-13 universe (BRL, MXN, COP, CLP, ZAR, KRW), top versus bottom tercile, monthly", "pre-registered (spec 7.2, D23)"),
    ("pm_timed", "base carry with the PM geopolitical overlay (monthly escalation, cut on a confirmed shock)", "pre-registered (spec 7.4, D16); to be read with D29"),
    ("vix_timed", "same overlay driven by VIX", "ex ante benchmark"),
    ("pm_timed_level_misspecified", "literal spec rule (index level), misspecified", "reported for transparency (D16)"),
    ("pm_timed_prob_index_D12", "overlay computed on the probability-based index", "declared variant (D12)"),
    ("*__coarse12, *__previous, *_cap20", "other EM universes and a 20% cap per currency", "declared variants (D23)"),
    ("pm_timed_without_event", "overlay rebuilt without the event that triggers the cut of the best month", "a posteriori diagnostic (D29)"),
    ("b2_oil_tilt", "B2: an \"oil\" shock does not cut the carry, it adds an exporters-versus-importers tilt", "mechanism from spec 7.5; details fixed a posteriori"),
    ("b2_brent_tilt", "B2 triggered by a Brent rise of more than 2 standard deviations", "a posteriori benchmark"),
    ("pm_timed_min3events", "overlay with at least 3 distinct events per index day", "a posteriori robustness (D31)"),
]


def _guide(w):
    w("## 0. Reading guide\n")
    w("- **Project**: two currency strategies built on prediction markets (Polymarket, Kalshi). A trades the G10 "
      "against the dollar; B is an EM carry with a geopolitical overlay. Course MFE 230GB, presentation on October 8, 2026.\n"
      "- **Status of the results**: every line has a status (glossary below). \"Pre-registered\" = rule fixed before any "
      "backtest. \"A posteriori\" = added after seeing the definitive results: to be presented as such. Identifiers D1 "
      "to D31 refer to `DECISIONS.md`.\n"
      "- **Periods**: \"2024-2025\" = in-sample (estimation period of the gated rules); \"2026 (OOS)\" = out-of-sample, "
      "from 2026-01-01 to 2026-09-24; \"2024-2026\" = full sample.\n"
      "- **Units**: annualised Sharpe (252 days); Sharpe t = Sharpe x square root of the number of years; 90% CI by "
      "block bootstrap (blocks of 20 days, 1000 draws); annualised returns and volatilities in percent; \"points\" = sum "
      "of daily returns in percentage points.\n"
      "- **Sources**: tables in `results/strategy_a/`, `results/strategy_b/`, `results/robustness/`, `results/risk/`, "
      "`results/weekend/`, `results/leadlag/`; figures in `results/figures/`; data for a web page in `results/site_data/`; "
      "step-by-step explanations in `notebooks/02_strategies_tests_results.ipynb`.\n"
      "- **Scope frozen** (final freeze of 2026-10-03, `DECISIONS.md`): no rule or variant will be added.\n"
      "- **Slide figures**: `results/figures/slides/` (1920 x 1080, PNG and SVG, no in-figure title; data in "
      "`results/site_data/slide_*.csv`).\n"
      "- **Pending**: (1) hand validation of the classification: label the four files "
      "`ai_log/classification/validation_sheet_1.csv` to `_4.csv` (50 rows each; guide: `LABELLING_GUIDE.md`), then run "
      "`.venv/Scripts/python.exe -m src.pm.validation score` (accuracy per field: theme, zone, direction; shown "
      "automatically in section 1); (2) HTML page (data ready in `results/site_data/`); (3) list of the AI conversations "
      "used for design and review (`ai_log/design_conversations.md`, to be filled from the exports).\n\n")
    w("**Glossary of strategies**:\n\n")
    w(table(pd.DataFrame(GLOSSARY, columns=["name", "description", "status"])))


def _synthesis(w, R):
    pa, pb = _read(R / "strategy_a" / "performance.csv"), _read(R / "strategy_b" / "performance.csv")
    da, km = _read(R / "strategy_a" / "diagnostics.csv"), _read(R / "strategy_b" / "key_month_check.csv")
    wk, bt = _read(R / "weekend" / "weekend_gap_regressions.csv"), _read(R / "risk" / "betas_weekly.csv")
    ab, ph = _read(R / "risk" / "a_vs_b_correlation.csv"), _read(R / "robustness" / "posthoc.csv")
    ph30 = _read(R / "strategy_a" / "d30_checks" / "phase.csv")
    info0 = _read(R / "strategy_b" / "posthoc_b2_min3_info.csv")
    iv0 = info0.set_index("item")["value"] if info0 is not None else None
    if pa is None or pb is None:
        return

    def sh(p, n, per="full", col="sharpe"):
        try:
            return float(p[(p.strategy == n) & (p.period == per)][col].iloc[0])
        except Exception:
            return np.nan

    def tval(model, reg, h):
        try:
            return float(da[(da.model == model) & (da.regressor == reg) & (da.horizon == h)]["t"].iloc[0])
        except Exception:
            return np.nan

    def beat(name):
        if ph is None:
            return np.nan
        t = ph[ph.strategy == name]
        a, s_ = t[t.test == "actual"]["sharpe"], t[t.test == "placebo_a_shuffle"]["sharpe"]
        return 100 * (s_ < a.iloc[0]).mean() if len(a) and len(s_) else np.nan

    w("## Summary\n")
    w("**1. Prediction markets move with currencies, not before them.** ")
    w(f"Contemporaneous, US MONETARY: t = {tval('A1_contemporaneous', 'MONETARY', 0):.1f}; predictive at 1 day: "
      f"t = {tval('A1_predictive', 'MONETARY', 1):.1f} (MONETARY) and {tval('A1_predictive', 'FISCAL_POLITICAL', 1):.1f} (FISCAL). ")
    if wk is not None:
        g = wk[wk.model.str.startswith("A1+GEO_weekend_gap")]
        if len(g):
            w(f"Pre-registered weekend gap test (D24): maximum |t| {g['t'].abs().max():.1f}, null result. ")
    w("Hourly lead-lag (D26): the dollar moves first or at the same time (section 7b).\n\n")
    w("**2. Strategy A: real content before costs, eaten by costs.** "
      f"A1 net {sh(pa, 'A1_theory_with_dollar'):.2f} (gross {sh(pa, 'A1_theory_with_dollar_gross'):.2f}, CI "
      f"[{sh(pa, 'A1_theory_with_dollar_gross', col='sharpe_ci90_low'):.2f}, {sh(pa, 'A1_theory_with_dollar_gross', col='sharpe_ci90_high'):.2f}]); "
      f"A2 net {sh(pa, 'A2_theory_with_dollar'):.2f} (gross {sh(pa, 'A2_theory_with_dollar_gross'):.2f}, t "
      f"{sh(pa, 'A2_theory_with_dollar_gross', col='sharpe_t'):.1f}). The spec's gated rule does not trade. "
      f"A posteriori: weekly {sh(pa, 'A1_theory_with_dollar_weekly'):.2f}; costs at 0.5x: A1 "
      f"{sh(pa, 'A1_theory_with_dollar_cost0.5x'):.2f}, A2 {sh(pa, 'A2_theory_with_dollar_cost0.5x'):.2f}; gated rule at "
      f"20 days (D30, horizon chosen after the fact): {sh(pa, 'A1_gated20_frozen'):.2f}, of which "
      f"{sh(pa, 'A1_gated20_frozen', 'out-of-sample'):.2f} in 2026 (beats {beat('A1_gated20_frozen'):.0f}% of placebos (a)). "
      "D30 fails the checks of section 4"
      + (f": averaged over the 20 possible rebalancing start dates, its 2026 Sharpe is only "
         f"{ph30['sharpe_2026'].mean():.2f}, and the effective-sample regression is not significant"
         if ph30 is not None else "")
      + ". It is an exploratory lead, not a result.\n\n")
    d29 = ""
    if km is not None:
        k = km.set_index("strategy")
        d29 = (f" But the whole gap comes from {k['best_month'].iloc[0]}: without the event `{k['event_removed'].iloc[0]}` "
               f"({int(k['event_contracts'].iloc[0])} contract), the overlay falls to {k.loc['pm_timed_without_event', 'sharpe']:.2f} (D29).")
    w("**3. Strategy B: the carry works, the PM geopolitical overlay adds nothing.** "
      f"Base carry {sh(pb, 'base_carry'):.2f} (t {sh(pb, 'base_carry', col='sharpe_t'):.1f}); with the PM overlay "
      f"{sh(pb, 'pm_timed'):.2f}, drawdown {100 * sh(pb, 'pm_timed', col='max_drawdown'):.1f}% versus "
      f"{100 * sh(pb, 'base_carry', col='max_drawdown'):.1f}%.{d29} With at least 3 events per day (D31): "
      f"{sh(pb, 'pm_timed_min3events'):.2f}. Oil tilt B2: {sh(pb, 'b2_oil_tilt'):.2f}, Brent-triggered: "
      f"{sh(pb, 'b2_brent_tilt'):.2f}; B2's lead comes from the same month (section 5). VIX timing: {sh(pb, 'vix_timed'):.2f}."
      + (f" {iv0['oil_confirmed_shocks']} of the {iv0['confirmed_shocks']} confirmed shocks are classified as \"oil\": "
         "B2 almost always tilts instead of cutting." if iv0 is not None else "") + "\n\n")
    brent_t = np.nan
    if bt is not None:
        x = bt[(bt.strategy == "base_carry") & (bt.factor == "brent")]
        brent_t = float(x["t"].iloc[0]) if len(x) else np.nan
    corr = np.nan
    if ab is not None:
        x = ab[ab.a == "A1_theory_with_dollar"]
        corr = float(x["return_corr"].iloc[0]) if len(x) else np.nan
    w("**4. Risk.** The 2024-2026 carry is long BRL, MXN and COP against KRW and CLP. It has a positive Brent beta "
      f"(t = {brent_t:.1f}) and no equity beta; the Brent beta comes mostly from the short legs (KRW and CLP fall when oil "
      "rises) and from COP, BRL and MXN having a Brent beta close to zero over the period (figure `slide_b_composition`). "
      "Middle East escalation helps it instead of crashing it, hence the failure of the overlay. Crash risk shows in the "
      f"long history (section 5). A and B are distinct (daily correlation A1 / B: {corr:.2f}).\n\n")


def _leverage(w, R, names, strat_b: bool):
    """Leverage and exposure table with one sentence per strategy (assignment: use of leverage)."""
    lv = _read(R / "risk" / "leverage.csv")
    if lv is None:
        return
    lv = lv[lv.strategy.isin(names)].copy()
    if not len(lv):
        return
    w("\n**Leverage and exposure** (gross exposure = sum of absolute weights, in multiples of capital; net USD exposure "
      "= minus the sum of the weights, > 0 = long USD; "
      + ("caps measured on the daily targets, before the no-trade band" if not strat_b else
         "B's rule has no gross cap and no per-currency cap; the 20% variant is reported in section 5")
      + "):\n\n")
    t = lv.copy()
    for c in ("share_days_long_usd", "realised_vol", "share_days_gross_cap", "share_days_pair_cap"):
        if c in t:
            t[c] = t[c].map(_pct)
    cols = ["strategy", "period", "gross_mean", "gross_median", "gross_p95", "gross_max", "abs_net_usd_mean",
            "share_days_long_usd", "realised_vol"] + ([] if strat_b else ["share_days_gross_cap", "share_days_pair_cap"])
    w(table(t, cols, {"strategy": "strategy", "period": "period", "gross_mean": "mean gross", "gross_median": "median gross",
                      "gross_p95": "gross 95th percentile", "gross_max": "max gross", "abs_net_usd_mean": "mean |net USD|",
                      "share_days_long_usd": "days long USD", "realised_vol": "realised vol (target 10%)",
                      "share_days_gross_cap": "3x cap binds", "share_days_pair_cap": "30% per-pair cap binds"}))
    w("\n")
    for n in names:
        x = lv[(lv.strategy == n) & (lv.period == "2024-2026")]
        if not len(x):
            continue
        x = x.iloc[0]
        msg = (f"- `{n}`: to target {100 * x['target_vol']:.0f}% volatility, gross exposure averages "
               f"{x['gross_mean']:.2f} times capital (95th percentile {x['gross_p95']:.2f}, maximum {x['gross_max']:.2f}); "
               f"realised volatility {100 * x['realised_vol']:.1f}%")
        if not strat_b:
            msg += (f"; the 3x gross cap binds on {100 * x['share_days_gross_cap']:.1f}% of decision days and the "
                    f"30% per-pair cap on {100 * x['share_days_pair_cap']:.1f}%")
            if x["abs_net_usd_mean"] > 0.9 * x["gross_mean"]:
                msg += "; the whole exposure is a dollar position (same signal on every pair)"
        else:
            msg += (f"; net dollar exposure close to zero (mean |net USD| {x['abs_net_usd_mean']:.2f}), the long and short "
                    "legs having the same gross size")
            if x["gross_max"] > 3:
                msg += f"; with no cap in the rule, gross exposure exceeds 3x on some days (max {x['gross_max']:.2f})"
        w(msg + ".\n")


def _d30_checks(w, R):
    """Sanity checks of D30 (final review): phase, positions, decomposition, effective sample."""
    D = R / "strategy_a" / "d30_checks"
    ph, pos, mo = _read(D / "phase.csv"), _read(D / "positions.csv"), _read(D / "monthly_2026.csv")
    dec, eff = _read(D / "decomposition.csv"), _read(D / "effective_sample.csv")
    if ph is None:
        return
    w("\n**Checks of D30 (final review; no rule changed)**\n\n"
      "*1. Phase robustness.* The published rule rebalances on trading days 0, 20, 40… of the sample. Same frozen rule, "
      "for the 20 possible start dates:\n\n")
    rows = []
    for col, lab in (("sharpe_2024-2026", "2024-2026"), ("sharpe_2024-2025", "2024-2025"), ("sharpe_2026", "2026 (OOS)")):
        x = ph[col]
        rows.append({"period": lab, "net Sharpe, published phase": x.iloc[0], "mean of the 20 phases": x.mean(),
                     "min": x.min(), "max": x.max(), "phases with Sharpe > 0": f"{int((x > 0).sum())} / {len(x)}",
                     "rank of the published phase": f"{int((x > x.iloc[0]).sum()) + 1} / {len(x)}"})
    w(table(pd.DataFrame(rows)))
    w("\nB2 and its Brent version do not rebalance on a fixed cycle: the base carry is rebuilt at each calendar month-end "
      "and the overlay is daily. The phase test therefore does not apply.\n")
    if pos is not None:
        w("\n*2. Positions* (published phase; USD position = minus the sum of the pair weights, > 0 = long USD):\n\n")
        p2 = pos.copy()
        for c in ("share_long_usd", "share_short_usd", "share_flat"):
            p2[c] = p2[c].map(lambda v: _pct(v, "{:.0f}"))
        w(table(p2, ["period", "days", "share_long_usd", "share_short_usd", "share_flat", "sign_changes", "rebalances"],
                {"period": "period", "days": "days", "share_long_usd": "long USD", "share_short_usd": "short USD",
                 "share_flat": "flat", "sign_changes": "sign changes", "rebalances": "rebalances"}))
    if mo is not None:
        w("\nMonthly P&L in 2026 (sum of daily returns):\n\n")
        m2 = mo.copy()
        for c in ("net", "gross"):
            m2[c] = m2[c].map(lambda v: f"{100 * v:+.1f}%")
        m2["usd_position_month_end"] = m2["usd_position_month_end"].map(
            lambda v: ("long USD" if v > 0 else "short USD" if v < 0 else "flat") + f" ({v:+.2f})")
        w(table(m2, rename={"month": "month", "net": "net", "gross": "gross", "usd_position_month_end": "USD position at month-end"}))
    if dec is not None:
        w("\n*3. Static / timing decomposition* (method of D25, gross P&L), and two ex post benchmarks that use 2026 "
          "information: the 2026 average position held all year, and the 2026 average direction "
          f"({dec['usd_direction_of_2026_average'].iloc[0]}) held at full size:\n\n")
        w(table(dec, ["part", "period", "sharpe", "ann_mean", "ann_vol"], {"part": "part", "period": "period", **PERF_NAMES}))
    if eff is not None and len(eff):
        w("\n*4. Effective sample*: a single series (G10 dollar basket), non-overlapping 20-day returns, OLS with "
          "small-sample t. \"Published phase\" = start on day 0; the other columns summarise the 20 phases.\n\n")
        rows = []
        for lab, g in eff.groupby("period", sort=False):
            g0 = g[g.offset == 0]
            rows.append({"period": lab, "n (published phase)": int(g0["n"].iloc[0]) if len(g0) else np.nan,
                         "t (published phase)": float(g0["t"].iloc[0]) if len(g0) else np.nan,
                         "mean t (20 phases)": g["t"].mean(), "t min": g["t"].min(), "t max": g["t"].max(),
                         "phases with t > 2": f"{int((g['t'] > 2).sum())} / {len(g)}"})
        w(table(pd.DataFrame(rows)))
    x26 = ph["sharpe_2026"]
    rank26 = int((x26 > x26.iloc[0]).sum()) + 1
    w(f"\n*Reading.* In 2026 the published phase ranks {rank26} of {len(x26)} possible start dates; the average over "
      f"phases ({x26.mean():.2f} in 2026) gives a more credible order of magnitude. The published start (day 0) was not "
      "chosen, but the published number owes much to phase luck. The P&L comes from timing (alternately long and short "
      "USD), not from a dollar direction held through the year. On the effective sample (one observation every 20 days) "
      "the relation is not significant. D30 is to be presented as an exploratory lead, not as a result.\n")


def build(preliminary: bool = False) -> str:
    cfg = load_config()
    P = ROOT / "data" / "processed"
    R = ROOT / ("results/preliminary_free" if preliminary else "results")
    G = ROOT / "results"
    out = []
    w = out.append
    w("# Quantitative results: prediction markets x FX (MFE 230GB)\n")
    w(f"Generated on {date.today().isoformat()} by `src/report/summary_md.py` from the result files. Every number comes "
      "from the CSV/Parquet files listed in each section; nothing is typed by hand.\n")
    if preliminary:
        w("> **Preliminary results (DECISIONS D22).** Free market data: FRED H.10 (G10, New York noon), ECB reference "
          "rates (EM, one-day execution lag), synthetic forwards from covered interest parity with OECD short rates, flat "
          "costs (2 bp G10, 10 bp EM). They validate the mechanics and flag the points to decide; the Bloomberg run "
          "supersedes them.\n")
    else:
        w("> **Definitive run (DECISIONS D28).** FX spot, 1-month forwards and 1-month NDFs: Bloomberg (default close, no "
          "16:00 London fix); MSCI World net TR, S&P 500 TR, DXY, Brent: Bloomberg; VIX: Cboe via WRDS; 10-year yields: "
          "official sources (US Treasury, Bundesbank, Bank of England, MOF Japan). Signals are taken at the 16:00 London "
          "snapshot and executed at the next close: the same day's New York close for the G10 and Latin America, the next "
          "day's Asian close for KRW. Costs: half of the delivered forward bid/ask spread, causal rolling median over 20 days.\n")
    w(f"Sample: {cfg['sample']['start']} to {cfg['sample']['end']}; in-sample 2024-2025, out-of-sample from "
      f"{cfg['sample']['test_start']}. Signals at the 16:00 London snapshot, "
      + ("returns at the free-data fixing, " if preliminary else "close-to-close returns (Bloomberg), ")
      + "statistics annualised over 252 days. Returns and volatility are in percent.\n")

    if not preliminary:
        _guide(w)
        _synthesis(w, R)

    # ------------------------------------------------------------ Key numbers
    pa0, pb0 = _read(R / "strategy_a" / "performance.csv"), _read(R / "strategy_b" / "performance.csv")
    db0, ab0 = _read(R / "risk" / "downside_beta.csv"), _read(R / "risk" / "a_vs_b_correlation.csv")
    cov0 = _read(G / "coverage_cells.csv")

    def _s(p, name, period, col="sharpe"):
        try:
            return float(p[(p.strategy == name) & (p.period == period)][col].iloc[0])
        except Exception:
            return np.nan

    w("## Key numbers\n")
    if cov0 is not None:
        kept = cov0[cov0["keep"]]
        w(f"- Cells that pass the coverage rule: {len(kept)} ("
          + ", ".join(f"{z}/{t}" for z, t in zip(kept.zone, kept.theme)) + ").\n")
    if pa0 is not None:
        w(f"- **A1 (dollar leg)**, net Sharpe: {_s(pa0, 'A1_theory_with_dollar', 'in-sample'):.2f} in 2024-2025, "
          f"{_s(pa0, 'A1_theory_with_dollar', 'out-of-sample'):.2f} in 2026; gross over 2024-2026: "
          f"{_s(pa0, 'A1_theory_with_dollar_gross', 'full'):.2f}; annual turnover "
          f"{_s(pa0, 'A1_theory_with_dollar', 'full', 'turnover_ann'):.0f}.\n")
        w(f"- **A2 (relaxed coverage)**, net Sharpe: {_s(pa0, 'A2_theory_with_dollar', 'in-sample'):.2f} in 2024-2025, "
          f"{_s(pa0, 'A2_theory_with_dollar', 'out-of-sample'):.2f} in 2026; spec gated rule: no theme passes |t| > 3.\n")
        if "A1_gated20_frozen" in set(pa0.strategy):
            w(f"- **A, a posteriori additions** (partial lifting of the freeze, see `DECISIONS.md`): weekly A1, net Sharpe "
              f"{_s(pa0, 'A1_theory_with_dollar_weekly', 'full'):.2f} (turnover "
              f"{_s(pa0, 'A1_theory_with_dollar_weekly', 'full', 'turnover_ann'):.0f}); gated rule at 20 days (D30, "
              f"horizon chosen after the full-sample diagnostic): A1 net {_s(pa0, 'A1_gated20_frozen', 'full'):.2f} over "
              f"2024-2026 and {_s(pa0, 'A1_gated20_frozen', 'out-of-sample'):.2f} in 2026; costs at 0.5x: A1 "
              f"{_s(pa0, 'A1_theory_with_dollar_cost0.5x', 'full'):.2f}, A2 {_s(pa0, 'A2_theory_with_dollar_cost0.5x', 'full'):.2f}.\n")
    if pb0 is not None:
        km0 = _read(R / "strategy_b" / "key_month_check.csv")
        d29 = ""
        if km0 is not None:
            k = km0.set_index("strategy")
            d29 = (f"; without the event `{k['event_removed'].iloc[0]}` that triggers the cut of {k['best_month'].iloc[0]} "
                   f"(D29): {k.loc['pm_timed_without_event', 'sharpe']:.2f}, drawdown "
                   f"{100 * k.loc['pm_timed_without_event', 'max_drawdown']:.1f}%")
        w(f"- **B, EM carry (IRR 12-13 universe) with a PM geopolitical overlay**, net Sharpe 2024-2026: base carry "
          f"{_s(pb0, 'base_carry', 'full'):.2f}; with the PM overlay {_s(pb0, 'pm_timed', 'full'):.2f}{d29}.\n")
        w(f"- **B, the three versions**, net Sharpe 2024-2026: base carry {_s(pb0, 'base_carry', 'full'):.2f}, PM-timed "
          f"{_s(pb0, 'pm_timed', 'full'):.2f}, VIX-timed {_s(pb0, 'vix_timed', 'full'):.2f}; maximum drawdown: "
          f"{100 * _s(pb0, 'base_carry', 'full', 'max_drawdown'):.1f}%, "
          f"{100 * _s(pb0, 'pm_timed', 'full', 'max_drawdown'):.1f}%, "
          f"{100 * _s(pb0, 'vix_timed', 'full', 'max_drawdown'):.1f}%"
          + (" (primary universe 1 versus 1 on free data: a mechanical check, not interpretable; \"coarse 1-2\" variant: "
             f"carry {_s(pb0, 'base_carry__coarse12', 'full'):.2f}, PM-timed {_s(pb0, 'pm_timed__coarse12', 'full'):.2f})"
             if preliminary else "") + ".\n")
        w("- **A1, decomposition (D25)**: the timing part carries most of the gross P&L (see section 4).\n")
    if db0 is not None:
        d = db0[db0.market == "msci_world"].set_index("strategy")["downside_beta"]
        w(f"- **Downside beta** (equities): base carry {d.get('base_carry', np.nan):.2f}, PM-timed "
          f"{d.get('pm_timed', np.nan):.2f}, VIX-timed {d.get('vix_timed', np.nan):.2f}.\n")
    if ab0 is not None:
        c = ab0.set_index("a")["return_corr"]
        w(f"- **Correlation A1 / B** (daily returns): {c.get('A1_theory_with_dollar', np.nan):.2f}.\n")
    w("\n")

    # ------------------------------------------------------------ 1. Prediction-market data
    w("## 1. Prediction-market data\n")
    daily = _read(P / "pm_daily.parquet")
    if daily is not None:
        g = daily.groupby("platform").agg(markets=("platform_id", "nunique"), market_days=("snap_date", "size"),
                                          volume_bn=("volume_usd", lambda s: s.sum() / 1e9)).reset_index()
        w(table(g, rename={"platform": "platform", "markets": "markets with trades",
                           "market_days": "market-days", "volume_bn": "volume (USD bn)"}))
    lab = _read(P / "contracts_classified.parquet")
    if lab is not None:
        lab["usable"] = (lab["direction"] != 0) | lab["partition"]
        c = lab.groupby("theme").agg(markets=("platform_id", "size"), events=("event_key", "nunique"),
                                     usable=("usable", "sum")).reset_index().sort_values("markets", ascending=False)
        w("\n**Classification (rules, D1)**: candidate macro markets with trades, by theme. \"Usable\" = defined direction "
          "or partition bucket.\n\n")
        w(table(c))
    cd = _read(P / "contract_days.parquet")
    if cd is not None:
        u = cd.drop_duplicates("contract_id")["unit"].value_counts()
        w(f"\nContracts in the panel: {len(cd['contract_id'].unique()):,}; by unit: "
          + ", ".join(f"{k} {v:,}" for k, v in u.items())
          + " (hazard = deadline markets valued as hazard rates, D18).\n")
    vs = _read(ROOT / "ai_log" / "classification" / "validation_scores.csv")
    w("\n**Hand validation**: " + ("see the table.\n\n" + table(vs) if vs is not None else
                                  "200 events to label (`ai_log/classification/validation_sheet_1.csv` to `_4.csv`), "
                                  "score not computed yet.\n"))

    # ------------------------------------------------------------ 2. Coverage
    w("\n## 2. Coverage table (rule: at least 60% of weekdays covered in 2024-2025)\n\n")
    cov = _read(G / "coverage_cells.csv")
    if cov is not None:
        cov = cov.sort_values("share_train", ascending=False).head(15)
        w(table(cov, ["zone", "theme", "share_train", "share_test", "n_contracts", "n_events", "volume_usd_m", "keep"],
                {"share_train": "coverage 2024-25", "share_test": "coverage 2026", "n_contracts": "contracts",
                 "n_events": "events", "volume_usd_m": "volume (USD m)", "keep": "kept"}))
    cov10 = _read(G / "coverage_cells_v10k.csv")
    if cov10 is not None:
        w("\nSame table at the USD 10k threshold (robustness), first 10 cells:\n\n")
        w(table(cov10.sort_values("share_train", ascending=False).head(10),
                ["zone", "theme", "share_train", "share_test", "keep"],
                {"share_train": "coverage 2024-25", "share_test": "coverage 2026", "keep": "kept"}))

    # ------------------------------------------------------------ 3. Indices and shocks
    w("\n## 3. Theme indices and shocks\n")
    idx = _read(P / "theme_index.parquet")
    if idx is not None:
        rows = []
        for z, t in [("US", "MONETARY"), ("US", "FISCAL_POLITICAL"), ("GLOBAL", "GEOPOLITICS"), ("GLOBAL", "GEO_TRADE")]:
            s = idx[(idx.zone == z) & (idx.theme == t)].set_index("day")
            a = s.loc[s.n_contracts > 0, "d_vw"]
            top = s["d_vw"].abs().sort_values(ascending=False).head(5).index
            rows.append({"cell": f"{z}/{t}", "active days": int((s.n_contracts > 0).sum()),
                         "average contracts per day": s.loc[s.n_contracts > 0, "n_contracts"].mean(),
                         "average drift (sd per day)": a.mean(), "t of the drift": a.mean() / a.std() * len(a) ** 0.5,
                         "5 largest moves": ", ".join(f"{d.date()} ({s.loc[d, 'd_vw']:+.1f})" for d in sorted(top))})
        w(table(pd.DataFrame(rows)))
        w("\nMoves of ±5.0 are winsorised. In 2024 the geopolitical cell often rests on one or two contracts, so its "
          "largest moves of that period carry little information.\n")
    idxp = _read(P / "theme_index_prob.parquet")
    if idxp is not None:
        a = idxp[(idxp.zone == "US") & (idxp.theme == "MONETARY") & (idxp.n_contracts > 0)]["d_vw"]
        w(f"\nComparison (D18): without hazard rates, the drift of US MONETARY would be {a.mean():.3f} sd per day "
          f"(t = {a.mean() / a.std() * len(a) ** 0.5:.1f}).\n")
    geo = _read(P / "geo_signals.parquet")
    if geo is not None:
        g = geo.set_index("day")
        me, ml = g["escalation_z"].resample("ME").last(), g["level_z_spec_misspecified"].resample("ME").last()
        w(f"\n**B's geopolitical index**: {int(g['shock_raw'].sum())} raw shocks, {int(g['confirmed'].sum())} confirmed. "
          f"Month-ends with an escalation z-score ≥ 1: {100 * (me >= 1).mean():.0f}% (≥ 2: {100 * (me >= 2).mean():.0f}%); "
          f"with the original misspecified version (level, D16): {100 * (ml >= 1).mean():.0f}%.\n\n")
        sh = g.loc[g["confirmed"], ["d", "d_early", "n_contracts", "volume_usd"]].reset_index()
        w(table(sh, rename={"day": "date", "d": "change (sd)", "d_early": "change 4 h before",
                            "n_contracts": "contracts", "volume_usd": "volume (USD)"}))
    wk = _read(P / "weekend_changes.parquet")
    if wk is not None:
        rows = []
        for z, t in [("GLOBAL", "GEOPOLITICS"), ("US", "FISCAL_POLITICAL"), ("US", "MONETARY")]:
            x = wk[(wk.zone == z) & (wk.theme == t)].set_index("friday")["d_vw"]
            top = x.abs().sort_values(ascending=False).head(4).index
            rows.append({"cell": f"{z}/{t}", "weekends": len(x),
                         "4 largest (Friday, sd)": ", ".join(f"{d.date()} ({x[d]:+.1f})" for d in top)})
        w("\n**Weekend changes** (Friday 17:00 to Sunday 17:00 New York):\n\n")
        w(table(pd.DataFrame(rows)))

    # ------------------------------------------------------------ 4. Strategy A
    w("\n## 4. Strategy A (G10)\n")
    pa = _read(R / "strategy_a" / "performance.csv")
    if pa is not None:
        names = ["A1_theory_with_dollar", "A1_theory_with_dollar_gross", "A2_theory_with_dollar",
                 "A2_theory_with_dollar_gross", "A2_theory_dollar_neutral", "A1+S_theory_with_dollar",
                 "A1+S_theory_dollar_neutral", "A2+S_theory_with_dollar", "A2+S_theory_dollar_neutral",
                 "A1_theory_with_dollar_D12", "A1_gated_frozen", "A2_gated_frozen"]
        w("\nTheory-signed rule (D2), net of costs except \"_gross\". A3 = A1 and A3+S = A1+S by construction (D14, D17); "
          "the dollar-neutral versions of A1 and A3 are zero (same signal on every pair). \"gated\" = the spec rule "
          "(|t| > 3 on 2024-2025, frozen coefficients).\n\n")
        w(perf_block(pa, names))
    ga = _read(R / "strategy_a" / "gate_estimation.csv")
    if ga is not None:
        w("\n**Estimation of the gated rule (2024-2025)**: no theme has t > 3 with the right sign, so the rule does not trade.\n\n")
        w(table(ga[ga.variant.isin(["A1", "A2"])], ["variant", "regressor", "coef", "t", "n_obs", "passes_gate"],
                {"regressor": "component", "passes_gate": "passes the gate"}))
    if pa is not None and "A1_gated20_frozen" in set(pa.strategy):
        w("\n**A posteriori additions (partial lifting of the scope freeze, 2026-10-03; nothing is pre-registered)**:\n"
          "- `A1_theory_with_dollar_weekly`: A1 rebalanced on the last trading day of each week.\n"
          "- `*_gated20_frozen` (D30): gated rule at the 20-day horizon. **The horizon was chosen after seeing the 20-day "
          "diagnostic on the full sample.** Estimation on 2024-2025 only (targets ending inside the training window, "
          "Driscoll-Kraay with a 20-day bandwidth), components with the right sign and t > 3, frozen coefficients, "
          "rebalancing every 20 trading days, test on 2026.\n"
          "- `*_cost0.5x`: costs at 0.5x the Bloomberg composite half-spread (the primary result stays at 1x).\n\n")
        w(perf_block(pa, ["A1_theory_with_dollar_weekly", "A1_theory_with_dollar_weekly_gross", "A1_gated20_frozen",
                          "A1_gated20_frozen_gross", "A2_gated20_frozen", "A1_theory_with_dollar_cost0.5x",
                          "A2_theory_with_dollar_cost0.5x", "A1_theory_with_dollar_weekly_cost0.5x",
                          "A1_gated20_frozen_cost0.5x"]))
        g20 = _read(R / "strategy_a" / "gate20_estimation.csv")
        if g20 is not None:
            w("\n**Estimation of the 20-day gated rule (D30, 2024-2025)**:\n\n")
            w(table(g20, ["variant", "regressor", "coef", "t", "n_obs", "passes_gate"],
                    {"regressor": "component", "passes_gate": "passes the gate"}))
        _d30_checks(w, R)
    _leverage(w, R, ["A1_theory_with_dollar", "A2_theory_with_dollar", "A1_theory_with_dollar_weekly"], False)
    da = _read(R / "strategy_a" / "diagnostics.csv")
    if da is not None:
        w("\n**Diagnostics** (pooled panel regressions, pair fixed effects, Driscoll-Kraay; theory predicts positive "
          "coefficients; horizon 0 = contemporaneous):\n\n")
        da = da[da.model.str.startswith(("A1_", "A2_"))]
        w(table(da, ["model", "horizon", "regressor", "coef", "t", "n_obs"],
                {"horizon": "horizon (days)", "regressor": "component"}))
        w("\nReading: the `_fiscal_x_regime` line cannot be interpreted (regime active on about 1% of days).\n")
    dec = _read(R / "strategy_a" / "decomposition_static_timing.csv")
    if dec is not None:
        w("\n**Static / timing decomposition (D25, pre-registered)**: the static part holds the 2024-2025 average position "
          "constant; the timing part is the deviation from that average. Gross P&L.\n\n")
        d = dec[dec.part.isin(["total", "static", "timing"])].copy()
        d["period"] = d["period"].map(PERIOD_LABEL)
        if "sharpe_ci90_low" in d:
            d["sharpe_ci"] = _ci(d["sharpe_ci90_low"], d["sharpe_ci90_high"])
        cols = ["strategy", "part", "period", "sharpe"] + (["sharpe_t", "sharpe_ci"] if "sharpe_t" in d else []) \
            + ["ann_mean", "ann_vol"]
        w(table(d, cols, {"part": "part", **PERF_NAMES}))
    reg = _read(R / "strategy_a" / "fiscal_regime.csv", index_col=0, parse_dates=True)
    if reg is not None and "US" in reg:
        w("\n**US fiscal regime (D15)**, share of days in fiscal dominance by year: "
          + ", ".join(f"{y}: {100 * v:.1f}%" for y, v in reg["US"].groupby(reg.index.year).mean().items()) + ".\n")
        w("\n**Finding (D27, exploratory, indicator not retuned)**: the 2025 fiscal-dominance episode was too short for a "
          "60-day rolling correlation; the indicator almost never activates.\n")
    wg = _read(R / "weekend" / "weekend_gap_regressions.csv")
    if wg is not None:
        w("\n**Weekend test (D24, pre-registered)**: main specification = `A1+GEO` (US MONETARY, US FISCAL and GLOBAL "
          "GEOPOLITICS on JPY and CHF), gap from Friday 17:00 New York to Monday 07:00 London (`london`), robustness Sunday "
          "18:00 New York (`ny`). The `daily_window_NOT_A_GAP_TEST` rows (Friday noon to Monday noon New York) are **not** a "
          "gap test. All weekends since 2024.\n\n")
        w(table(wg, ["model", "regressor", "coef", "t", "n_obs"], {"regressor": "component"}))

    # ------------------------------------------------------------ 5. Strategy B
    w("\n## 5. Strategy B: EM carry (IRR 12-13 universe) with a PM geopolitical overlay\n")
    ex_irr = _read(ROOT / "data" / "manual" / "em_exclusions.csv", comment="#")
    if ex_irr is not None:
        w("\n**Universe (D23, pre-registered)**: Ilzetzki-Reinhart-Rogoff de facto classification, 2019 vintage "
          "(limitation: no regime change after 2019 is seen). Primary universe = fine codes 12 (managed floating) and 13 "
          "(freely floating); portfolio = top tercile versus bottom tercile of the carry sort.\n\n")
        e = ex_irr.copy()
        e["primary universe"] = e["exclude"].map({0: "yes", 1: "no"})
        e["coarse 1-2 variant"] = e["exclude_variant_coarse12"].map({0: "yes", 1: "no"})
        w(table(e, ["ccy", "irr_fine_code", "irr_label", "primary universe", "coarse 1-2 variant"],
                {"ccy": "currency", "irr_fine_code": "IRR code", "irr_label": "de facto regime"}))
        if preliminary:
            w("\nIn the preliminary run, only BRL, MXN, ZAR and KRW have both a price and a rate in the free data: the "
              "primary universe gives 1 versus 1. It is a mechanical check, **not a result to interpret**.\n")
    pb = _read(R / "strategy_b" / "performance.csv")
    if pb is not None:
        w("\n")
        w(perf_block(pb, ["base_carry", "base_carry_gross", "pm_timed", "pm_timed_gross", "vix_timed",
                          "vix_timed_gross", "pm_timed_level_misspecified", "pm_timed_prob_index_D12"]))
        w("\n`pm_timed` = base carry with the PM geopolitical overlay. To be read with the D29 diagnostic just below.\n")
        km = _read(R / "strategy_b" / "key_month_check.csv")
        if km is not None:
            k0 = km.iloc[0]
            w("\n**Where does the gap between PM timing and the base carry come from? (D29, a posteriori diagnostic)**\n\n"
              f"Cumulative gap (PM timing minus base carry, sum of net returns): {100 * k0['total_gain']:+.1f} points, of "
              f"which {100 * k0['best_month_gain']:+.1f} points in the single month {k0['best_month']}. The event that raised "
              f"the escalation index most in the previous 35 days is `{k0['event_removed']}` "
              f"({int(k0['event_contracts'])} contract(s)). Same rule, index rebuilt without that event:\n\n")
            w(table(km, ["strategy", "sharpe", "ann_mean", "max_drawdown"], PERF_NAMES))
        rb = _read(R / "strategy_b" / "returns.parquet")
        info = _read(R / "strategy_b" / "posthoc_b2_min3_info.csv")
        if info is not None and rb is not None and "b2_oil_tilt" in rb:
            iv = info.set_index("item")["value"]
            w("\n**A posteriori additions on B (partial lifting of the freeze, 2026-10-03)**:\n"
              "- `b2_oil_tilt` (B2, spec 7.5): mechanism and direction pre-specified in spec 7.5 (deferred by D5); "
              "implementation details fixed after seeing B's oil exposure. A confirmed shock carried more than half by "
              "\"oil\" contracts (Middle East, Russia-Ukraine) does not cut the carry: it adds a tilt long exporters "
              f"({iv['oil_exporters_used']}) against importers ({iv['oil_importers_used']}), sized by the avoided cut. Other "
              f"shocks cut as in the primary rule. Confirmed shocks: {iv['confirmed_shocks']}, of which "
              f"{iv['oil_confirmed_shocks']} classified as \"oil\": B2 therefore almost always tilts instead of cutting.\n"
              f"- `b2_brent_tilt`: same rule, oil shock triggered by a daily Brent rise of more than 2 standard deviations "
              f"({iv['brent_shock_days']} days).\n"
              "- `pm_timed_min3events` (D31, robustness motivated by D29): a day counts in the index, the escalation measure "
              "and shock confirmation only if at least 3 distinct events have eligible contracts that day "
              f"({iv['min3_index_days']} index days versus {iv['primary_index_days']}). The primary rule is unchanged.\n\n")
            w(perf_block(pb, ["b2_oil_tilt", "b2_oil_tilt_gross", "b2_brent_tilt", "pm_timed_min3events"]))
            if km is not None:
                m = km.iloc[0]["best_month"]
                att = []
                for n in ("pm_timed", "b2_oil_tilt", "b2_brent_tilt", "pm_timed_min3events"):
                    dlt = (rb[n] - rb["base_carry"]).dropna()
                    att.append({"strategy": n, "cumulative gap (points)": 100 * dlt.sum(),
                                f"of which {m} (points)": 100 * dlt.loc[m].sum(),
                                f"excluding {m} (points)": 100 * (dlt.sum() - dlt.loc[m].sum())})
                w(f"\nGap to the base carry (sum of net returns), with and without the month {m} identified by D29 (B2's "
                  "escalation component is the primary rule's):\n\n")
                w(table(pd.DataFrame(att)))
        w("\n**Universe variants and 20% cap per currency (D23)**:\n\n")
        w(perf_block(pb, ["base_carry__coarse12", "pm_timed__coarse12", "base_carry__previous", "pm_timed__previous",
                          "base_carry__primary_cap20", "pm_timed__primary_cap20", "base_carry__previous_cap20",
                          "pm_timed__previous_cap20"]))
        w("\nThe 20% cap cannot be met with fewer than three currencies per leg; weights are then equal within the leg "
          "instead of inverse to volatility.\n")
    lh = _read(R / "strategy_b" / "base_carry_long_history.csv")
    if lh is not None:
        w("\n**Base EM carry over the long history** (crash-risk premise):\n\n")
        w(table(lh, [c for c in ["n_days", "sharpe", "ann_mean", "ann_vol", "max_drawdown", "skew", "excess_kurtosis"] if c in lh],
                {"n_days": "days", **PERF_NAMES}))
    wts = _read(R / "strategy_b" / "weights_base_carry.parquet")
    pnl = _read(R / "strategy_b" / "pnl_by_asset_base_carry.parquet")
    if wts is not None and pnl is not None:
        wts, pnl = wts.loc[cfg["sample"]["start"]:], pnl.loc[cfg["sample"]["start"]:]
        share = wts.abs().div(wts.abs().sum(axis=1), axis=0).mean()
        long_share = (wts > 0).mean()
        comp = pd.DataFrame({"currency": share.index, "share of exposure": share.values,
                             "days long": long_share.reindex(share.index).values,
                             "cumulative P&L (sum of returns)": pnl.sum().reindex(share.index).values}
                            ).sort_values("share of exposure", ascending=False)
        comp["share of exposure"] = comp["share of exposure"].map(_pct)
        comp["days long"] = comp["days long"].map(lambda v: _pct(v, "{:.0f}"))
        w("\n**Composition of the base carry over 2024-2026**:\n\n")
        w(table(comp))
    ex = _read(R / "strategy_b" / "exposure.csv", index_col=0, parse_dates=True)
    if ex is not None:
        w(f"\n**Exposure w(t)** of the PM timing: mean {ex['w'].mean():.2f}; days with w < 1: {int((ex['w'] < 1).sum())} "
          f"of {len(ex)}; shock days: {int(ex['shock'].sum())}. VIX timing: mean {ex['w_vix'].mean():.2f}, shock days: "
          f"{int(ex['shock_vix'].sum())}.\n")
    gr = _read(R / "strategy_b" / "grid.csv")
    if gr is not None:
        w("\n**Full grid** (27 cells: shock threshold k, re-risk days, cut level):\n\n")
        w(table(gr, ["shock_k", "rerisk_days", "shock_cut", "sharpe", "ann_mean", "max_drawdown"],
                {"shock_k": "k", "rerisk_days": "re-risk (days)", "shock_cut": "cut to", **PERF_NAMES}))
    cs = _read(R / "strategy_b" / "cost_sensitivity.csv")
    if cs is not None:
        w("\n**Cost sensitivity** (PM timing):\n\n")
        w(table(cs, ["cost_multiplier", "sharpe", "ann_mean", "max_drawdown"], {"cost_multiplier": "cost multiple", **PERF_NAMES}))

    _leverage(w, R, ["base_carry", "pm_timed", "vix_timed", "b2_oil_tilt"], True)

    # ------------------------------------------------------------ 6. Robustness
    w("\n## 6. Robustness and placebos\n")
    for name, label in (("strategy_a", "Strategy A"), ("strategy_b", "Strategy B (PM timing)")):
        t = _read(R / "robustness" / f"{name}.csv")
        if t is None:
            continue
        groups = [("A1", False), ("A2", False), ("A1+S", True)] if "variant" in t else [(None, None)]
        for v, dn in groups:
            tt = t if v is None else t[(t["variant"] == v) & (t["dollar_neutral"].astype(bool) == dn)]
            if not len(tt):
                continue
            s = tt.groupby("test")["sharpe"].agg(["count", "mean", "min", "max"]).reset_index()
            sh = tt.loc[tt.test == "placebo_a_shuffle", "sharpe"]
            act = tt.loc[tt.test == "actual", "sharpe"]
            pct = (sh < act.iloc[0]).mean() if len(sh) and len(act) else np.nan
            lab_v = label if v is None else f"{label}, {v} {'dollar-neutral' if dn else 'with dollar'}"
            w(f"\n**{lab_v}**: the actual Sharpe beats {100 * pct:.0f}% of the {len(sh)} placebo draws (a).\n\n")
            w(table(s, rename={"test": "exercise", "count": "n", "mean": "mean Sharpe", "min": "min", "max": "max"}))
        loeo = t[t.test == "leave_one_event_out"]
        if len(loeo) and "event" in loeo:
            sub = loeo if "variant" not in loeo else loeo[(loeo.variant == "A1") & (~loeo.dollar_neutral.astype(bool))]
            w(f"\nLeave-one-event-out ({label}, events removed one at a time):\n\n")
            w(table(sub, ["event", "sharpe", "max_drawdown"], {"event": "event removed", **PERF_NAMES}))
    ph = _read(R / "robustness" / "posthoc.csv")
    if ph is not None:
        w("\n**Placebos of the a posteriori additions** (same placebos (a), (b), (c); for D30 the frozen component and "
          "coefficient are applied to the placebo signals without re-estimation; the Brent benchmark has no PM signal, "
          "hence no placebo).\n")
        for name in ph["strategy"].unique():
            tt = ph[ph.strategy == name]
            s_ = tt.groupby("test")["sharpe"].agg(["count", "mean", "min", "max"]).reset_index()
            shf, act = tt.loc[tt.test == "placebo_a_shuffle", "sharpe"], tt.loc[tt.test == "actual", "sharpe"]
            pct = (shf < act.iloc[0]).mean() if len(shf) and len(act) else np.nan
            w(f"\n**{name}**: the actual Sharpe beats {100 * pct:.0f}% of the {len(shf)} placebo draws (a).\n\n")
            w(table(s_, rename={"test": "exercise", "count": "n", "mean": "mean Sharpe", "min": "min", "max": "max"}))
        w("\nReading:\n"
          "- **Weekly A1 and D30** beat the large majority of draws, and collapse with random contracts or the reversed "
          "sign. For D30, placebo (a) shuffles dates within the month while the position is held 20 days: it keeps part of "
          "the monthly level of the signal (positive mean of the draws), so it is a weaker test than for a daily rule. No "
          "placebo addresses the a posteriori choice of the horizon.\n"
          "- **B2** beats most draws and placebos (b) and (c), but the mean of the draws stays below the base carry, and "
          "B2's lead over the carry comes from the month identified by D29 (section 5).\n"
          "- **3-event overlay (D31)**: random contracts and the reversed sign do better than the actual rule; nothing "
          "distinguishes this signal from random timing.\n")
    sp = _read(R / "robustness" / "subperiods.csv")
    if sp is not None:
        sp = sp[sp.strategy.isin(["A1_theory_with_dollar", "A2_theory_with_dollar", "A1_theory_with_dollar_weekly",
                                  "A1_gated20_frozen", "base_carry", "pm_timed", "vix_timed", "b2_oil_tilt",
                                  "b2_brent_tilt", "pm_timed_min3events"])]
        w("\n**Sub-periods**:\n\n")
        w(table(sp.pivot(index="strategy", columns="period", values="sharpe").reset_index(),
                rename={"strategy": "strategy (Sharpe by year)"}))

    # ------------------------------------------------------------ 7. Risk
    w("\n## 7. Risk\n")
    main = ["A1_theory_with_dollar", "A2_theory_with_dollar", "A1+S_theory_with_dollar", "base_carry", "pm_timed", "vix_timed"]
    db = _read(R / "risk" / "downside_beta.csv")
    if db is not None:
        w("\n**Normal and downside beta** (Lettau, Maggiori, Weber; weekly; market = "
          + ("S&P 500 in place of MSCI World" if preliminary else "MSCI World net TR") + ", or EM carry):\n\n")
        w(table(db[db.strategy.isin(main)], ["strategy", "market", "beta", "downside_beta", "n_down", "mean_return_down_days_bp"],
                {"n_down": "down weeks", "mean_return_down_days_bp": "mean return in those weeks (bp)"}))
    bt = _read(R / "risk" / "betas_weekly.csv")
    if bt is not None:
        w("\n**Weekly betas** (Newey-West t):\n\n")
        if preliminary:
            w("In the preliminary run the S&P 500 stands in for MSCI World: the two lines are identical.\n\n")
        w(table(bt[bt.strategy.isin(main)], ["strategy", "factor", "beta", "t", "corr"], {"corr": "correlation"}))
    ep = _read(R / "risk" / "episodes.csv")
    if ep is not None:
        w("\n**Stress episodes** (cumulative return over the window):\n\n")
        e = ep[ep.strategy.isin(main)].pivot(index="episode", columns="strategy", values="cum_return").reset_index()
        for c in e.columns[1:]:
            e[c] = e[c].map(_pct)
        w(table(e))
    cp = _read(R / "risk" / "conditional_performance.csv")
    if cp is not None:
        w("\n**Conditional performance** (Sharpe by state):\n\n")
        c = cp[cp.strategy.isin(main) & (cp.conditioner != "half-spread tercile")].copy()
        lab_b = {"-1.0": "dollar down", "1.0": "dollar up", "True": "yes", "False": "no",
                 "q1": "low tercile", "q2": "middle tercile", "q3": "high tercile"}
        c["state"] = c["conditioner"] + ": " + c["bucket"].astype(str).map(lambda b: lab_b.get(b, b))
        w(table(c.pivot_table(index="state", columns="strategy", values="sharpe").reset_index()))
        lq = cp[cp.strategy.isin(main) & (cp.conditioner == "half-spread tercile")].copy()
        if len(lq):
            w("\n**Liquidity risk** (reporting): performance by tercile of the average 1-month forward half-spread of each "
              "strategy's universe (G10 for A, primary EM universe for B), same causal smoothing as the costs, value known "
              "the day before. High tercile = least liquid market.\n\n")
            lab_q = {"q1": "low spreads", "q2": "middle spreads", "q3": "high spreads"}
            lq["tercile"] = lq["bucket"].astype(str).map(lambda b: lab_q.get(b, b))
            sh_ = lq.pivot_table(index="tercile", columns="strategy", values="sharpe")
            mu_ = lq.pivot_table(index="tercile", columns="strategy", values="ann_mean")
            order = [v for v in lab_q.values() if v in sh_.index]
            w("Sharpe:\n\n")
            w(table(sh_.reindex(order).reset_index()))
            w("\nMean annual return:\n\n")
            mu_ = mu_.reindex(order)
            for c_ in mu_.columns:
                mu_[c_] = mu_[c_].map(_pct)
            w(table(mu_.reset_index()))
    dd = _read(R / "risk" / "worst_drawdowns.csv", parse_dates=["peak", "trough", "recovery"])
    if dd is not None:
        for s_ in ["A1_theory_with_dollar", "pm_timed", "base_carry"]:
            d = dd[dd.strategy == s_].head(5)
            if len(d):
                w(f"\n**5 worst drawdowns: {s_}** (label = news between peak and trough):\n\n")
                w(table(d, ["peak", "trough", "recovery", "depth", "duration_days", "tag"],
                        {"duration_days": "duration (days)", "tag": "context"}))
    co = _read(R / "risk" / "concentration.csv")
    if co is not None:
        h = co.groupby(["strategy", "dimension"])["hhi"].first().reset_index()
        h = h[~h["strategy"].str.contains("A1_theory_dollar_neutral")]   # zero positions by construction
        w("\n**P&L concentration** (Herfindahl index of absolute contributions; 1 = everything on a single item):\n\n")
        w(table(h, rename={"hhi": "HHI"}))
    ab = _read(R / "risk" / "a_vs_b_correlation.csv")
    if ab is not None:
        w("\n**A versus B** (correlation with PM-timed B):\n\n")
        w(table(ab[ab.a.isin(main + ["A2+S_theory_with_dollar"])], ["a", "return_corr", "weekly_return_corr", "drawdown_corr"],
                {"a": "strategy A", "return_corr": "daily correlation", "weekly_return_corr": "weekly correlation",
                 "drawdown_corr": "drawdown correlation"}))

    # ------------------------------------------------------------ 7b. Lead-lag (D26)
    ll = _read(R / "leadlag" / "event_study.csv")
    w("\n## 7b. Intraday lead-lag (D26, exploratory)\n")
    if ll is None:
        w("\n_Waiting for the complete Dukascopy hourly data._\n")
    else:
        w("\nEvent studies: top 1% of hourly changes (mechanical selection). Values aligned on the sign of the event; "
          "hour 0 = hour of the event (intervals dated by their end); 95% CI. A significant mean at negative hours would "
          "mean that the other market moves first.\n\n")
        x = ll[ll.hour.between(-3, 3)].copy()
        x["mean [95% CI]"] = [f"{m:.4f} [{a:.4f}, {b:.4f}]" for m, a, b in zip(x["mean"], x["ci_low"], x["ci_high"])]
        piv = x.pivot(index="study", columns="hour", values="mean [95% CI]").reset_index()
        piv.columns = ["study"] + [f"h{c:+d}" for c in piv.columns[1:]]
        w(table(piv))

    # ------------------------------------------------------------ 8. Caveats
    w("\n## 8. Caveats\n")
    w("- Statistics that rest on a regressor that is almost always zero (fiscal × regime interaction, own-zone "
      "geopolitics in the weekend test) cannot be interpreted, even with a high t.\n"
      "- Several variants are reported (D14, D17), plus the a posteriori additions of 2026-10-03: results must be read "
      "with the multiple-testing caveat, and an a posteriori addition must never be presented as pre-registered.\n"
      + ("- Preliminary costs are flat; the true bid-ask (Bloomberg) may change the ranking of high-turnover variants.\n"
         if preliminary else
         "- Costs come from Bloomberg closing bid/ask (indicative composite quotes). They are wide for NOK and SEK (median "
         "half-spread of about 11 to 12 bp) and CHF (about 5 bp), probably wider than dealable spreads: A's costs are "
         "conservative. A's daily turnover makes its net Sharpe very sensitive to this.\n"
         "- No price is a 16:00 London fix: the FX day (New York close to New York close) ends six hours after the PM day "
         "(16:00 to 16:00 London), which slightly dilutes contemporaneous coefficients; predictive regressions and "
         "backtests are not affected (signal known before execution).\n")
      + "- The Sharpe t (annualised Sharpe x square root of the number of years) and the 90% block-bootstrap confidence "
      "interval (blocks of 20 days, 1000 draws) show the uncertainty: over two to three years, a Sharpe below about 1.2 is "
      "not significantly different from zero.\n")
    # Concentration of B, computed from the current universe (no hand-written currency names).
    wb = _read(R / "strategy_b" / "weights_base_carry.parquet")
    if wb is not None:
        wb = wb.loc[cfg["sample"]["start"]:]
        sh = wb.abs().div(wb.abs().sum(axis=1), axis=0).mean().sort_values(ascending=False)
        top, n_ccy = sh.index[0], int((sh > 0.001).sum())
        msg = (f"- Base EM carry (primary universe, {n_ccy} currencies used): the most heavily weighted currency is "
               f"{top} ({100 * sh.iloc[0]:.0f}% of average exposure)")
        msg += ": a concentrated portfolio.\n" if sh.iloc[0] > 0.30 else ".\n"
        if preliminary:
            msg += ("- In the preliminary run the primary universe has only a few currencies (1 versus 1): B cannot be "
                    "interpreted before the Bloomberg run.\n")
        w(msg)
    text = "\n".join(out)
    path = R / "RESULTS.md"
    path.write_text(text, encoding="utf-8")
    log.info("written %s", path)
    return text


if __name__ == "__main__":
    build(preliminary=len(sys.argv) > 1 and sys.argv[1] == "preliminary")
