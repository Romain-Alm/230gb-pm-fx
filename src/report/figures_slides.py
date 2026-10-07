"""Figures for the presentation slides: 1920 x 1080 PNG and SVG, large fonts, no in-figure title.

Outputs in results/figures/slides/; the data behind every figure is written next to it in
results/figures/slides/data/ (copied to results/site_data/ by site_data.py). Existing figures
in results/figures/ are not touched.
  slide_a_cumulative        A1 and A2, cumulative net and gross returns, OOS boundary
  slide_b_cumulative        base carry, PM overlay, VIX overlay (net), June 2024 shaded, D29 line
  slide_coverage_heatmap    2024-2025 coverage share, zone x theme
  slide_leadlag             hourly event studies, both directions, mean and 95% CI
  slide_d30_phase           2026 Sharpe of the D30 rule for the 20 rebalancing phases
  slide_b_composition       average base-carry weight per currency and Brent beta
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from src.common import get_logger, load_config, rpath  # noqa: E402

log = get_logger("figures_slides")
SIZE, DPI = (19.2, 10.8), 100
COL = {"A1": "#1f5c99", "A2": "#d9822b", "base": "#555555", "pm": "#1f5c99", "vix": "#c0392b", "hl": "#d9822b"}
ZONES = ["US", "EA", "JP", "UK", "CH", "AU", "NZ", "CA", "NO", "SE", "CN", "KR", "MX", "BR", "TW", "GLOBAL"]
THEMES = ["MONETARY", "INFLATION", "FISCAL_POLITICAL", "TRADE_TARIFFS", "GEOPOLITICS"]


def _style():
    plt.rcParams.update({"font.size": 22, "axes.labelsize": 24, "xtick.labelsize": 20, "ytick.labelsize": 20,
                         "legend.fontsize": 20, "axes.spines.top": False, "axes.spines.right": False,
                         "lines.linewidth": 3})


def _save(fig, out, name, data: pd.DataFrame):
    fig.tight_layout()
    fig.savefig(out / f"{name}.png", dpi=DPI)
    fig.savefig(out / f"{name}.svg")
    plt.close(fig)
    (out / "data").mkdir(exist_ok=True)
    data.to_csv(out / "data" / f"{name}.csv", index=isinstance(data.index, pd.DatetimeIndex))


def _cum(r: pd.Series) -> pd.Series:
    return 100 * ((1 + r.fillna(0)).cumprod() - 1)


def _boundary(ax, cfg):
    t = pd.Timestamp(cfg["sample"]["test_start"])
    ax.axvline(t, color="black", lw=1.5, ls=":")
    ax.text(t, ax.get_ylim()[1], "  out-of-sample", va="top", ha="left", fontsize=18)


def fig_a(cfg, res, out):
    r = pd.read_parquet(res / "strategy_a" / "returns.parquet").loc[cfg["sample"]["start"]:cfg["sample"]["end"]]
    d = pd.DataFrame({f"{v}_{k}": _cum(r[f"{v}_theory_with_dollar" + ("_gross" if k == "gross" else "")])
                      for v in ("A1", "A2") for k in ("net", "gross")})
    fig, ax = plt.subplots(figsize=SIZE)
    for v in ("A1", "A2"):
        ax.plot(d.index, d[f"{v}_net"], color=COL[v], label=f"{v} net of costs")
        ax.plot(d.index, d[f"{v}_gross"], color=COL[v], ls="--", lw=2, label=f"{v} gross")
    ax.axhline(0, color="grey", lw=1)
    ax.set_ylabel("Cumulative return (%)")
    ax.legend(loc="upper left", frameon=False)
    _boundary(ax, cfg)
    _save(fig, out, "slide_a_cumulative", d)


def fig_b(cfg, res, out):
    r = pd.read_parquet(res / "strategy_b" / "returns.parquet").loc[cfg["sample"]["start"]:cfg["sample"]["end"]]
    d = pd.DataFrame({"base_carry": _cum(r["base_carry"]), "pm_timed": _cum(r["pm_timed"]),
                      "vix_timed": _cum(r["vix_timed"])})
    f = res / "strategy_b" / "returns_pm_timed_without_event.parquet"
    if f.exists():
        w = pd.read_parquet(f)["pm_timed_without_event"].loc[cfg["sample"]["start"]:cfg["sample"]["end"]]
        d["pm_timed_without_event"] = _cum(w.reindex(d.index))
    fig, ax = plt.subplots(figsize=SIZE)
    ax.axvspan(pd.Timestamp("2024-06-01"), pd.Timestamp("2024-06-30"), color="#f2e6c9", label="June 2024")
    ax.plot(d.index, d["base_carry"], color=COL["base"], label="EM carry (base)")
    ax.plot(d.index, d["pm_timed"], color=COL["pm"], label="with PM geopolitical overlay")
    ax.plot(d.index, d["vix_timed"], color=COL["vix"], label="with VIX overlay")
    if "pm_timed_without_event" in d:
        ax.plot(d.index, d["pm_timed_without_event"], color=COL["pm"], ls="--", lw=2.5,
                label="PM overlay without the 2024 Taiwan contract (D29)")
    ax.axhline(0, color="grey", lw=1)
    ax.set_ylabel("Cumulative return, net of costs (%)")
    ax.legend(loc="upper left", frameon=False)
    _boundary(ax, cfg)
    _save(fig, out, "slide_b_cumulative", d)


def fig_coverage(cfg, res, out):
    c = pd.read_csv(res / "coverage_cells.csv")
    m = c.pivot_table(index="zone", columns="theme", values="share_train").reindex(index=ZONES, columns=THEMES).fillna(0)
    keep = c[c["keep"]].set_index(["zone", "theme"]).index
    fig, ax = plt.subplots(figsize=SIZE)
    im = ax.imshow(100 * m.values, cmap="Blues", vmin=0, vmax=100, aspect="auto")
    ax.set_xticks(range(len(THEMES)), [t.replace("_", " ").title() for t in THEMES])
    ax.set_yticks(range(len(ZONES)), ZONES)
    for i, z in enumerate(ZONES):
        for j, t in enumerate(THEMES):
            v = 100 * m.loc[z, t]
            if v > 0:
                kept = (z, t) in keep
                ax.text(j, i, f"{v:.0f}%", ha="center", va="center", fontsize=17,
                        color="white" if v > 55 else "black", fontweight="bold" if kept else "normal")
    cb = fig.colorbar(im, ax=ax, fraction=0.03)
    cb.set_label("Weekdays covered, 2024-2025 (%); bold = kept (60% rule)")
    ax.spines[["left", "bottom"]].set_visible(False)
    _save(fig, out, "slide_coverage_heatmap", (100 * m).round(1))


def fig_leadlag(cfg, res, out):
    f = res / "leadlag" / "event_study.csv"
    if not f.exists():
        return
    ll = pd.read_csv(f)
    ll = ll[ll["hour"].between(-6, 6)]
    fig, axes = plt.subplots(1, 2, figsize=SIZE, sharex=True)
    cols = ["#1f5c99", "#d9822b", "#2e7d32"]
    for ax, key, unit, scale, ylab in ((axes[0], "FX top", "sd", 1.0, "Prediction-market index change (sd)"),
                                       (axes[1], "PM ", "bp", 1e4, "Dollar-basket return (bp)")):
        sub = ll[ll["study"].str.startswith(key)]
        for c, (study, g) in zip(cols, sub.groupby("study")):
            lab = study.split("->")[1].strip() if key == "FX top" else study.split(" top")[0].replace("PM ", "")
            ax.plot(g["hour"], scale * g["mean"], "o-", color=c, label=lab, ms=7)
            ax.fill_between(g["hour"], scale * g["ci_low"], scale * g["ci_high"], color=c, alpha=0.15)
        ax.axhline(0, color="grey", lw=1)
        ax.axvline(0, color="black", lw=1.5, ls=":")
        ax.set_xlabel("Hours from the event (interval end)")
        ax.set_ylabel(ylab)
        ax.legend(frameon=False, fontsize=17, loc="upper left")
    axes[0].text(0.98, 0.02, "event = top 1% hourly dollar moves", transform=axes[0].transAxes, ha="right", fontsize=17)
    axes[1].text(0.98, 0.02, "event = top 1% hourly index moves", transform=axes[1].transAxes, ha="right", fontsize=17)
    _save(fig, out, "slide_leadlag", ll)


def fig_phase(cfg, res, out):
    f = res / "strategy_a" / "d30_checks" / "phase.csv"
    if not f.exists():
        return
    ph = pd.read_csv(f)
    fig, ax = plt.subplots(figsize=SIZE)
    colors = [COL["hl"] if o == 0 else "#9db4cc" for o in ph["offset"]]
    ax.bar(ph["offset"], ph["sharpe_2026"], color=colors)
    ax.axhline(ph["sharpe_2026"].mean(), color="black", ls="--", lw=2,
               label=f"mean of the 20 phases: {ph['sharpe_2026'].mean():.2f}")
    ax.axhline(0, color="grey", lw=1)
    ax.set_xticks(ph["offset"])
    ax.set_xlabel("Start offset of the 20-day rebalancing (trading days); orange = published phase")
    ax.set_ylabel("2026 Sharpe ratio, net (D30 rule)")
    ax.legend(frameon=False, loc="upper right")
    _save(fig, out, "slide_d30_phase", ph)


def fig_b_composition(cfg, res, out):
    from src.data import market
    from src.strategies.run_b import em_universe
    w = pd.read_parquet(res / "strategy_b" / "weights_base_carry.parquet").loc[cfg["sample"]["start"]:cfg["sample"]["end"]]
    raw, mp = market.read_raw(cfg), market.series_map(cfg)
    ccys = em_universe(cfg, mp)
    days = pd.bdate_range(cfg["sample"]["start"], cfg["sample"]["end"])
    rx = market.fx_panel(raw, mp, ccys, days).rx
    brent = np.log(market.simple_series(raw, mp, "risk", days)["brent"]).diff()
    rw, bw = rx.resample("W-FRI").sum(min_count=1), brent.resample("W-FRI").sum(min_count=1)
    beta = {}
    for c in ccys:
        d = pd.concat([rw[c], bw], axis=1).dropna()
        beta[c] = float(np.polyfit(d.iloc[:, 1], d.iloc[:, 0], 1)[0]) if len(d) > 20 else np.nan
    tab = pd.DataFrame({"average_weight": w.reindex(columns=ccys).mean(),
                        "share_of_gross": w.reindex(columns=ccys).abs().mean() / w.abs().sum(axis=1).mean(),
                        "brent_beta_weekly": pd.Series(beta)})
    tab = tab.sort_values("average_weight", ascending=False)
    bt = pd.read_csv(res / "risk" / "betas_weekly.csv")
    pb = bt[(bt.strategy == "base_carry") & (bt.factor == "brent")]
    fig, ax = plt.subplots(figsize=SIZE)
    x = np.arange(len(tab))
    ax.bar(x, 100 * tab["average_weight"], color=["#2e7d32" if v > 0 else "#c62828" for v in tab["average_weight"]], width=0.55)
    ax.axhline(0, color="grey", lw=1)
    ax.set_xticks(x, tab.index)
    ax.set_ylabel("Average weight, 2024-2026 (% of capital; > 0 = long vs USD)")
    ax2 = ax.twinx()
    ax2.plot(x, tab["brent_beta_weekly"], "D", color="black", ms=14, label="currency's weekly beta to Brent")
    # Same zero on both axes: scale the beta axis to the weight axis.
    lo, hi = ax.get_ylim()
    k = 1.15 * np.nanmax(np.abs(tab["brent_beta_weekly"])) / max(abs(lo), abs(hi))
    ax2.set_ylim(lo * k, hi * k)
    ax2.set_ylabel("Weekly beta of the currency to Brent")
    ax2.spines["right"].set_visible(True)
    if len(pb):
        ax2.text(0.98, 0.95, f"portfolio beta to Brent: {pb['beta'].iloc[0]:.2f} (t = {pb['t'].iloc[0]:.1f})",
                 transform=ax2.transAxes, ha="right", va="top", fontsize=20)
    ax2.legend(frameon=False, loc="lower left")
    _save(fig, out, "slide_b_composition", tab.rename_axis("currency"))


def build(cfg: dict | None = None) -> None:
    cfg = cfg or load_config()
    res = rpath("results", cfg)
    out = res / "figures" / "slides"
    out.mkdir(parents=True, exist_ok=True)
    _style()
    for f in (fig_a, fig_b, fig_coverage, fig_leadlag, fig_phase, fig_b_composition):
        f(cfg, res, out)
    log.info("slide figures written to %s", out)


if __name__ == "__main__":
    build()
