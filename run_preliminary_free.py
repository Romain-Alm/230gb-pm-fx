"""Preliminary run on free market data (DECISIONS D22). Results go to results/preliminary_free/
and are superseded by the Bloomberg run (`run_all.py`).

Usage:
    .venv/Scripts/python.exe -m src.data.download_free all      # FRED, ECB, Dukascopy (slow)
    .venv/Scripts/python.exe run_preliminary_free.py [--shuffles 50] [--skip-robustness]
"""
from __future__ import annotations

import argparse
import shutil

from src.common import ROOT, get_logger
from src.data import free_market

log = get_logger("preliminary")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shuffles", type=int, default=50)
    ap.add_argument("--skip-robustness", action="store_true")
    args = ap.parse_args()
    free_market.build()
    cfg = free_market.preliminary_config()
    out = ROOT / cfg["paths"]["results"]
    out.mkdir(parents=True, exist_ok=True)
    for f in ("coverage_cells.csv", "coverage.csv", "coverage_cells_v10k.csv"):
        shutil.copy(ROOT / "results" / f, out / f)          # PM-layer outputs are shared
    (out / "PRELIMINARY_README.md").write_text(
        "# Preliminary results on free market data\n\n"
        "Built by `run_preliminary_free.py` (DECISIONS D22): FRED H.10 G10 rates, ECB reference rates "
        "for emerging currencies (one-day execution lag), synthetic forwards from OECD short rates, "
        "fallback bid-ask costs. Superseded by the Bloomberg run in `results/`.\n", encoding="utf-8")
    from src.strategies import run_a, run_b, weekend_test
    run_b.run(cfg)
    run_a.run(cfg)
    weekend_test.run(cfg)    # hourly gap if Dukascopy data exists, Friday-to-Monday daily window otherwise
    if any((ROOT / cfg["paths"]["raw_intraday"]).glob("*.parquet")):
        from src.strategies import leadlag
        leadlag.run(cfg)       # D26, exploratory
    from src.risk import run_risk
    run_risk.run(cfg)
    if not args.skip_robustness:
        import run_all
        run_all.stage_robustness(cfg, args.shuffles)
    from src.report import figures_strategies, site_data, summary_md
    figures_strategies.build(cfg)
    site_data.build(cfg)
    summary_md.build(preliminary=True)
    log.info("preliminary results in %s", out)


if __name__ == "__main__":
    main()
