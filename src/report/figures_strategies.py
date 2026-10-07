"""Figures for the presentation (spec 11.3), from the saved results. PNG and SVG."""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.backtest.metrics import drawdown
from src.common import get_logger, load_config, rpath

log = get_logger("figures")
COL = {"base_carry": "#7f7f7f", "pm_timed": "#1f5c99", "vix_timed": "#d08c2a",
       "pm_timed_level_misspecified": "#b0b0d0"}


def _save(fig, path):
    fig.tight_layout()
    fig.savefig(path.with_suffix(".png"), dpi=150)
    fig.savefig(path.with_suffix(".svg"))
    plt.close(fig)
    log.info("saved %s", path.with_suffix(".png"))


def _shade_oos(ax, cfg):
    ax.axvspan(pd.Timestamp(cfg["sample"]["test_start"]), pd.Timestamp(cfg["sample"]["end"]),
               color="#f2e6c9", alpha=0.5, lw=0, label="out-of-sample")


def strategy_b(cfg, res, fig_dir):
    d = res / "strategy_b"
    r = pd.read_parquet(d / "returns.parquet")
    w = pd.read_csv(d / "exposure.csv", index_col=0, parse_dates=True)
    fig, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=True,
                             gridspec_kw={"height_ratios": [3, 1.3, 1.6]})
    ax = axes[0]
    _shade_oos(ax, cfg)
    for c in ("base_carry", "vix_timed", "pm_timed"):
        ax.plot((1 + r[c].fillna(0)).cumprod() - 1, label=c.replace("_", " "), color=COL[c], lw=1.4)
    ax.set_title("Strategy B: EM carry, base vs timed (net of costs)", loc="left")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.25)
    ax = axes[1]
    ax.fill_between(w.index, w["w"], step="post", color=COL["pm_timed"], alpha=0.4)
    ax.plot(w.index, w["w_escalation"], color="black", lw=0.8, drawstyle="steps-post", label="escalation component")
    for t in w.index[w["shock"]]:
        ax.axvline(t, color="#b22222", lw=0.8, alpha=0.6)
    ax.set_ylim(-0.05, 1.05)
    ax.set_title("Exposure w(t); red: confirmed geopolitical shocks", loc="left", fontsize=9)
    ax = axes[2]
    for c in ("base_carry", "vix_timed", "pm_timed"):
        ax.plot(drawdown(r[c]), color=COL[c], lw=1.1)
    ax.set_title("Drawdowns", loc="left", fontsize=9)
    ax.grid(alpha=0.25)
    _save(fig, fig_dir / "strategy_b_overview")

    g = pd.read_csv(d / "grid.csv")
    cuts = sorted(g["shock_cut"].unique())
    fig, axes = plt.subplots(1, len(cuts), figsize=(4 * len(cuts), 3.4))
    vmax = np.nanmax(np.abs(g["sharpe"])) or 1
    for ax, c in zip(np.atleast_1d(axes), cuts):
        p = g[g["shock_cut"] == c].pivot(index="shock_k", columns="rerisk_days", values="sharpe")
        im = ax.imshow(p.values, cmap="RdBu", vmin=-vmax, vmax=vmax)
        ax.set_xticks(range(p.shape[1]), p.columns)
        ax.set_yticks(range(p.shape[0]), p.index)
        ax.set_xlabel("re-risk days")
        ax.set_ylabel("shock threshold k")
        ax.set_title(f"cut to {c}", fontsize=9)
        for i in range(p.shape[0]):
            for j in range(p.shape[1]):
                ax.text(j, i, f"{p.values[i, j]:.2f}", ha="center", va="center", fontsize=8)
    fig.suptitle("Strategy B robustness grid: Sharpe ratio, every cell shown", fontsize=10)
    _save(fig, fig_dir / "strategy_b_grid")


def strategy_a(cfg, res, fig_dir):
    d = res / "strategy_a"
    r = pd.read_parquet(d / "returns.parquet")
    cols = [c for c in r.columns if "theory" in c and not c.endswith("_gross")]
    fig, ax = plt.subplots(figsize=(11, 5))
    _shade_oos(ax, cfg)
    for c in cols:
        ax.plot((1 + r[c].fillna(0)).cumprod() - 1, lw=1.2, label=c.replace("_", " "),
                ls="--" if "neutral" in c else "-")
    ax.set_title("Strategy A variants (theory-signed rule, net of costs)", loc="left")
    ax.legend(fontsize=7, ncol=2)
    ax.grid(alpha=0.25)
    _save(fig, fig_dir / "strategy_a_cumulative")

    if (d / "diagnostics.csv").exists():
        t = pd.read_csv(d / "diagnostics.csv")
        t = t[t["model"].str.startswith("A1") | t["model"].str.startswith("A2")]
        t["col"] = t["model"].str.replace("_predictive", "") + " h=" + t["horizon"].astype(str)
        p = t.pivot_table(index="regressor", columns="col", values="t", aggfunc="first")
        fig, ax = plt.subplots(figsize=(1.2 + 0.9 * p.shape[1], 0.45 * p.shape[0] + 1.6))
        im = ax.imshow(p.values, cmap="RdBu", vmin=-4, vmax=4, aspect="auto")
        ax.set_yticks(range(p.shape[0]), p.index, fontsize=8)
        ax.set_xticks(range(p.shape[1]), p.columns, rotation=45, ha="right", fontsize=8)
        for i in range(p.shape[0]):
            for j in range(p.shape[1]):
                v = p.values[i, j]
                if np.isfinite(v):
                    ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=7)
        ax.set_title("t-statistics (Driscoll-Kraay); theory predicts positive; gate |t| > 3", fontsize=9)
        fig.colorbar(im, ax=ax, fraction=0.03)
        _save(fig, fig_dir / "strategy_a_tstats")


def placebos(cfg, res, fig_dir):
    f = res / "robustness"
    for name in ("strategy_b", "strategy_a"):
        p = f / f"{name}.csv"
        if not p.exists():
            continue
        t = pd.read_csv(p)
        if "variant" in t:
            t = t[(t["variant"] == "A1") & (~t["dollar_neutral"].astype(bool))]
        sh = t.loc[t["test"] == "placebo_a_shuffle", "sharpe"].dropna()
        act = t.loc[t["test"] == "actual", "sharpe"].iloc[0]
        fig, ax = plt.subplots(figsize=(7, 3.6))
        ax.hist(sh, bins=25, color="#bbbbbb", label="placebo (a): dates shuffled within month")
        ax.axvline(act, color="#1f5c99", lw=2, label=f"actual ({act:.2f})")
        for lab, col in (("placebo_b_random_contracts", "#2ca02c"), ("placebo_c_reversed", "#d62728")):
            v = t.loc[t["test"] == lab, "sharpe"]
            if len(v):
                ax.axvline(v.iloc[0], color=col, lw=1.5, ls="--", label=f"{lab.split('_', 2)[2].replace('_', ' ')} ({v.iloc[0]:.2f})")
        pct = (sh < act).mean() if len(sh) else np.nan
        ax.set_title(f"{name.replace('_', ' ').title()}: placebo Sharpe ratios (actual beats {pct:.0%} of shuffles)",
                     loc="left", fontsize=9)
        ax.legend(fontsize=7)
        _save(fig, fig_dir / f"{name}_placebos")


def build(cfg: dict | None = None) -> None:
    cfg = cfg or load_config()
    res, fig_dir = rpath("results", cfg), rpath("results", cfg) / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)
    if (res / "strategy_b" / "returns.parquet").exists():
        strategy_b(cfg, res, fig_dir)
    if (res / "strategy_a" / "returns.parquet").exists():
        strategy_a(cfg, res, fig_dir)
    placebos(cfg, res, fig_dir)


if __name__ == "__main__":
    build()
