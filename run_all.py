"""Rebuild every processed file, table and figure (spec 0.6, 11.1).

Usage:
    .venv/Scripts/python.exe run_all.py                 # everything
    .venv/Scripts/python.exe run_all.py --stage pm      # prediction-market layer only
    .venv/Scripts/python.exe run_all.py --stage strategies --shuffles 200

Stages:
  pm          metadata, daily panel, classification, contract panels (50k, 10k, 250k,
              placebo), coverage, theme indices, shocks, weekend changes, PM figures
  strategies  Strategy A and B backtests (needs market data in data/raw/market)
  robustness  placebos, grids, leave-one-event-out, sub-periods
  risk        risk tables
  figures     strategy figures, slide figures, site data, RESULTS.md and the HTML page
  site        site data and the HTML page only (deliverables/index.html), for a quick rebuild of the page
The pm stage reads the Kairos data estate (read-only) when it is present; without it, it starts from
the panels in data/processed/ shared with the data bundle (TAPE_PANELS). Later stages read only this repo.
"""
from __future__ import annotations

import argparse
import time

import pandas as pd

from src.common import ROOT, get_logger, kairos_root, load_config, rpath

log = get_logger("run_all")
# Panels read from the raw trades tape; shared with the data bundle for runs without the estate.
TAPE_PANELS = ("pm_markets.parquet", "pm_daily.parquet", "weekend_changes.parquet", "hourly_index.parquet")


def stage_pm(cfg, skip_metadata: bool = False):
    from src.data import pm_markets, pm_panel
    from src.pm import contracts, coverage, hourly, indices, shocks, validation, weekend
    from src.report import figures_pm
    proc = rpath("processed", cfg)
    # Without the Kairos data estate (raw trades tape, about 75 GB), start from the panels built
    # from it and shared with the data bundle (README, "Data").
    estate = kairos_root(cfg).exists()
    if estate:
        if not skip_metadata:
            pm_markets.build(cfg)        # about 12 minutes (scans 35 M market rows)
        pm_panel.build(cfg)
    else:
        missing = [f for f in TAPE_PANELS if not (proc / f).exists()]
        if missing:
            raise FileNotFoundError(f"no Kairos data estate at {kairos_root(cfg)} and missing in {proc}: "
                                    f"{', '.join(missing)} (see README, 'Data')")
        log.warning("no Kairos data estate at %s: reusing %s", kairos_root(cfg), ", ".join(TAPE_PANELS))
    if (ROOT / "src" / "pm" / "vendor" / "geo_registry.py").exists():
        from src.pm import classify
        classify.build(cfg)
    else:
        log.warning("src/pm/vendor/ missing: reusing data/processed/contracts_classified.parquet")
    contracts.build(cfg)
    contracts.build(cfg, min_volume=10_000, out_file="contract_days_v10k.parquet")
    contracts.build(cfg, min_volume=250_000, out_file="contract_days_v250k.parquet")
    contracts.build(cfg, out_file="contract_days_placebo.parquet", placebo_seed=cfg["seed"])
    contracts.build(cfg, out_file="contract_days_prob.parquet", hazard=False)            # D12 variant
    contracts.build(cfg, min_volume=10_000, out_file="contract_days_v10k_prob.parquet", hazard=False)
    coverage.build(cfg)
    coverage.build(cfg, panel_file="contract_days_v10k.parquet", suffix="_v10k")
    for f in ("", "_v10k", "_v250k", "_placebo", "_prob", "_v10k_prob"):
        indices.build(cfg, panel_file=f"contract_days{f}.parquet", out_file=f"theme_index{f}.parquet")
    shocks.build(cfg)
    if estate:
        weekend.build(cfg)
        hourly.build(cfg)                # D26, exploratory lead-lag input
    figures_pm.theme_indices(cfg)
    if any(validation.OUT.glob("validation_sheet_[0-9]_human.csv")):
        validation.score()               # hand validation of the classification (labels in ai_log/classification/)
    elif not (validation.OUT / "validation_sheet.csv").exists():
        validation.make_sheet(cfg)


def stage_strategies(cfg):
    from src.strategies import run_a, run_b, weekend_test
    run_b.run(cfg)
    run_a.run(cfg)
    from src.strategies import d30_checks
    d30_checks.run(cfg)    # sanity checks of the a posteriori D30 rule (no rule change)
    if any(rpath("raw_intraday", cfg).glob("*.parquet")):
        weekend_test.run(cfg)
        from src.strategies import leadlag
        leadlag.run(cfg)       # D26, exploratory
    else:
        log.warning("no intraday FX in data/raw/intraday: weekend gap test skipped")


def stage_robustness(cfg, shuffles: int):
    from src.backtest import robustness as R
    from src.strategies import run_a, run_b
    out = rpath("results", cfg) / "robustness"
    out.mkdir(parents=True, exist_ok=True)
    R.strategy_b(run_b.prepare(cfg), n_shuffle=shuffles).to_csv(out / "strategy_b.csv", index=False)
    ctx = run_a.prepare(cfg)
    parts = [R.strategy_a(ctx, v, dn, n_shuffle=shuffles) for v in ("A1", "A2", "A1+S") for dn in (False, True)]
    pd.concat(parts).to_csv(out / "strategy_a.csv", index=False)
    stage_posthoc(cfg, shuffles, ctx)
    res = rpath("results", cfg)
    rets = pd.concat([pd.read_parquet(res / "strategy_a" / "returns.parquet"),
                      pd.read_parquet(res / "strategy_b" / "returns.parquet")], axis=1)
    R.subperiods(rets).to_csv(out / "subperiods.csv", index=False)


def stage_posthoc(cfg, shuffles: int, ctx_a: dict | None = None):
    """Placebos of the a posteriori additions (scope-freeze lifting of 2026-10-03)."""
    from src.backtest import robustness as R
    from src.strategies import run_a, run_b
    out = rpath("results", cfg) / "robustness"
    out.mkdir(parents=True, exist_ok=True)
    g20 = pd.read_csv(rpath("results", cfg) / "strategy_a" / "gate20_estimation.csv")
    frozen = {v: dict(zip(g["regressor"], g["coef"])) for v, g in g20[g20["passes_gate"]].groupby("variant")}
    pd.concat([R.posthoc_a(ctx_a or run_a.prepare(cfg), frozen, shuffles),
               R.posthoc_b(run_b.prepare(cfg), shuffles)]).to_csv(out / "posthoc.csv", index=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", default="all",
                    choices=["all", "pm", "strategies", "robustness", "risk", "figures", "site"])
    ap.add_argument("--skip-metadata", action="store_true", help="reuse pm_markets.parquet")
    ap.add_argument("--shuffles", type=int, default=100)
    args = ap.parse_args()
    cfg = load_config()
    t0 = time.time()
    stages = ["pm", "strategies", "robustness", "risk", "figures"] if args.stage == "all" else [args.stage]
    market_ready = any(rpath("raw_market", cfg).glob("*"))
    for st in stages:
        if st != "pm" and not market_ready:
            log.warning("no market data in data/raw/market: stage %s skipped", st)
            continue
        log.info("=== stage %s", st)
        if st == "pm":
            stage_pm(cfg, args.skip_metadata)
        elif st == "strategies":
            stage_strategies(cfg)
        elif st == "robustness":
            stage_robustness(cfg, args.shuffles)
        elif st == "risk":
            from src.risk import leverage, run_risk
            run_risk.run(cfg)
            leverage.run(cfg)       # reporting: gross and net exposure, caps, realised volatility
        elif st == "figures":
            from src.report import figures_slides, figures_strategies, site_data, strategy_a_checks, strategy_a_explained, summary_md
            figures_strategies.build(cfg)
            figures_slides.build(cfg)
            strategy_a_explained.run(cfg)   # diagnostic note on A1 (results/notes/), no rule change
            strategy_a_checks.run(cfg)      # presentation checks on A1 (results/notes/), no rule change
            site_data.build(cfg)
            summary_md.build()
            from src.report import build_site
            build_site.build(cfg)           # spec 11.2: self-contained interactive page, deliverables/index.html
        elif st == "site":
            from src.report import build_site, site_data
            site_data.build(cfg)
            build_site.build(cfg)
    log.info("done in %.1f minutes", (time.time() - t0) / 60)


if __name__ == "__main__":
    main()
