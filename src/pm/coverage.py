"""Coverage table (spec 4.3): first deliverable, decides the final zones and themes.

Per (zone, theme) cell and calendar quarter: number of eligible contracts, traded USD
volume of eligible contracts, and share of weekdays with at least one eligible contract.
A cell enters signal construction only if that share is at least
`coverage.min_share_days_covered_train` over the training period.

Outputs: results/coverage.csv (cell x quarter), results/coverage_cells.csv (cell summary
with the keep flag), results/figures/coverage_heatmap.png
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.common import connect, get_logger, load_config, rpath, sql_path

log = get_logger("coverage")

THEMES = ["MONETARY", "INFLATION", "FISCAL_POLITICAL", "TRADE_TARIFFS", "GEOPOLITICS"]


def build(cfg: dict | None = None, panel_file: str = "contract_days.parquet",
          suffix: str = "") -> pd.DataFrame:
    cfg = cfg or load_config()
    proc, res, fig = rpath("processed", cfg), rpath("results", cfg), rpath("figures", cfg)
    start, train_end, end = cfg["sample"]["start"], cfg["sample"]["train_end"], cfg["sample"]["end"]
    con = connect()
    p = sql_path(proc / panel_file)

    q = con.execute(f"""
        WITH e AS (SELECT * FROM read_parquet('{p}') WHERE eligible AND dayofweek(day) BETWEEN 1 AND 5)
        SELECT zone, theme, CAST(date_trunc('quarter', day) AS DATE) AS quarter,
               count(DISTINCT contract_id) AS n_contracts,
               count(DISTINCT event_key) AS n_events,
               round(sum(vol1d) / 1e6, 3) AS volume_usd_m,
               count(DISTINCT day) AS days_covered
        FROM e GROUP BY ALL
    """).df()
    wd = pd.DataFrame({"day": pd.bdate_range(start, end)})
    wd["quarter"] = wd["day"].dt.to_period("Q").dt.start_time
    n_wd = wd.groupby("quarter").size().rename("weekdays")
    q["quarter"] = pd.to_datetime(q["quarter"])
    q = q.merge(n_wd, left_on="quarter", right_index=True, how="left")
    q["share_days_covered"] = (q["days_covered"] / q["weekdays"]).round(3)
    q = q.sort_values(["zone", "theme", "quarter"])
    q.to_csv(res / f"coverage{suffix}.csv", index=False)

    n_train = len(pd.bdate_range(start, train_end))
    cells = con.execute(f"""
        WITH e AS (SELECT * FROM read_parquet('{p}') WHERE eligible AND dayofweek(day) BETWEEN 1 AND 5)
        SELECT zone, theme,
               count(DISTINCT day) FILTER (WHERE day <= DATE '{train_end}') AS train_days,
               count(DISTINCT day) FILTER (WHERE day > DATE '{train_end}') AS test_days,
               count(DISTINCT contract_id) AS n_contracts,
               count(DISTINCT event_key) AS n_events,
               round(sum(vol1d) / 1e6, 2) AS volume_usd_m
        FROM e GROUP BY ALL
    """).df()
    n_test = len(pd.bdate_range(pd.Timestamp(train_end) + pd.Timedelta(days=1), end))
    cells["share_train"] = (cells["train_days"] / n_train).round(3)
    cells["share_test"] = (cells["test_days"] / n_test).round(3)
    cells["keep"] = cells["share_train"] >= cfg["coverage"]["min_share_days_covered_train"]
    cells = cells.sort_values(["keep", "share_train"], ascending=False)
    cells.to_csv(res / f"coverage_cells{suffix}.csv", index=False)
    log.info("coverage cells (%s):\n%s", panel_file, cells.head(40).to_string(index=False))

    _heatmap(q, fig / f"coverage_heatmap{suffix}.png")
    return cells


def _heatmap(q: pd.DataFrame, path) -> None:
    q = q.copy()
    q["cell"] = q["zone"] + " / " + q["theme"]
    top = (q.groupby("cell")["days_covered"].sum().sort_values(ascending=False).head(30).index)
    piv = (q[q["cell"].isin(top)].pivot_table(index="cell", columns="quarter",
                                               values="share_days_covered", aggfunc="first")
           .reindex(top).fillna(0.0))
    fig, ax = plt.subplots(figsize=(1.0 + 0.55 * piv.shape[1], 0.32 * len(piv) + 1.5))
    im = ax.imshow(piv.values, aspect="auto", cmap="Blues", vmin=0, vmax=1)
    ax.set_yticks(range(len(piv)), piv.index, fontsize=8)
    ax.set_xticks(range(piv.shape[1]), [f"{pd.Timestamp(c).year}Q{pd.Timestamp(c).quarter}"
                                        for c in piv.columns], rotation=45, fontsize=8)
    for i in range(piv.shape[0]):
        for j in range(piv.shape[1]):
            v = piv.values[i, j]
            if v > 0:
                ax.text(j, i, f"{v:.0%}", ha="center", va="center", fontsize=6,
                        color="white" if v > 0.6 else "black")
    ax.set_title("Share of weekdays with at least one eligible contract", fontsize=10)
    fig.colorbar(im, ax=ax, fraction=0.03)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    build()
