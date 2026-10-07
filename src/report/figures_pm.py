"""Figures for the prediction-market layer: theme indices and the global geopolitical index."""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.common import get_logger, load_config, rpath

log = get_logger("figures_pm")

ANNOTATIONS = {  # illustration only (spec 6.6): not used by any rule
    "2024-08-02": "Weak July payrolls",
    "2024-11-06": "US election",
    "2024-12-19": "Hawkish Fed cut",
    "2025-04-02": "Liberation Day tariffs",
    "2025-06-13": "Israel strikes Iran",
    "2025-10-04": "Gaza deal",
}


def theme_indices(cfg: dict | None = None, cells=None) -> None:
    cfg = cfg or load_config()
    proc, fig_dir = rpath("processed", cfg), rpath("figures", cfg)
    idx = pd.read_parquet(proc / "theme_index.parquet")
    geo = pd.read_parquet(proc / "geo_signals.parquet")
    cells = cells or [("US", "MONETARY"), ("US", "FISCAL_POLITICAL"), ("GLOBAL", "GEOPOLITICS"),
                      ("GLOBAL", "GEO_TRADE")]
    fig, axes = plt.subplots(len(cells), 1, figsize=(11, 2.6 * len(cells)), sharex=True)
    for ax, (z, t) in zip(axes, cells):
        s = idx[(idx["zone"] == z) & (idx["theme"] == t)].set_index("day")
        ax.plot(s.index, s["index_vw"], lw=1.1, color="#2b5c8a", label="volume-weighted")
        ax.plot(s.index, s["index_ew"], lw=0.8, color="#d08c2a", alpha=0.8, label="equal-weighted")
        ax.set_title(f"{z} / {t}", fontsize=10, loc="left")
        ax.axvline(pd.Timestamp(cfg["sample"]["test_start"]), color="grey", ls="--", lw=0.8)
        if t in ("GEOPOLITICS", "GEO_TRADE"):
            for d in geo.loc[geo["confirmed"], "day"]:
                ax.axvline(d, color="#b22222", alpha=0.35, lw=0.8)
        for d, lab in ANNOTATIONS.items():
            ts = pd.Timestamp(d)
            if ts in s.index and t in ("MONETARY", "FISCAL_POLITICAL"):
                ax.annotate(lab, (ts, s.loc[ts, "index_vw"]), fontsize=7, rotation=90,
                            va="bottom", color="#444")
        ax.grid(alpha=0.25)
    axes[0].legend(fontsize=8, loc="upper left")
    axes[-1].set_xlabel("Red lines: confirmed geopolitical shocks. Dashed: start of the out-of-sample period.",
                        fontsize=8)
    fig.tight_layout()
    path = fig_dir / "theme_indices.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    log.info("saved %s", path)


if __name__ == "__main__":
    theme_indices()
