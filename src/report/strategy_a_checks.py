"""Strategy A checks for the presentation (2026-10-08; DECISIONS, diagnostic). No rule change.

Section 3 of results/notes/strategy_a_checks.md (sections 1 and 2 come from
`src.report.strategy_a_explained`). Tables in results/notes/strategy_a_checks/.

  3a  Fed-related contracts (chair nomination, removal of Fed officials, political pressure on
      the Fed): theme, direction, panel status, traded volume by year; share of the US MONETARY
      index contribution by year;
  3b  A1 USD position and MONETARY vs FISCAL contributions in three windows: Iran war, worst
      drawdown, the 2026-09-16 FOMC meeting;
  3c  average A1 USD position by period and the part due to the residual drift of the US
      MONETARY index (counterfactuals with the MONETARY cell change demeaned).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.backtest import metrics
from src.common import connect, get_logger, load_config, rpath, sql_path
from src.report.strategy_a_explained import _cell, _decisive, _periods, _regime_mult, _rows, _stats
from src.risk.risk import EPISODES
from src.strategies import run_a
from src.strategies import strategy_a as A

log = get_logger("strategy_a_checks")
PPY = 252

# Fed-related contracts, matched on the lower-case title (diagnostic labels, no rule).
FED_GROUPS = [
    ("removal or departure of Fed officials",
     r"(powell|lisa cook|cook|miran|jefferson|kugler|barr|governor|fed chair).{0,80}"
     r"(fire|fired|remov|out|resign|leave|depart|step down|replace)|(fire|remove|oust).{0,40}(powell|cook|fed|governor)"),
    ("Fed chair nomination",
     r"(fed|federal reserve|fomc|federal open market).{0,40}chair|chair.{0,40}(fed|federal reserve)|"
     r"nominat.{0,80}(fed|federal reserve|chair)|(warsh|hassett|rieder|shelton|zervos|bullard|waller|bowman).{0,80}(chair|nominat|confirm)"),
    ("political pressure on the Fed",
     r"(fed|federal reserve|central bank).{0,30}independen|independen.{0,30}(fed|federal reserve|central bank)|"
     r"audit the fed|end the fed|end the federal reserve|trump.{0,60}(powell|the fed|fed chair)|"
     r"lisa cook.{0,60}(court|lawsuit)|supreme court.{0,60}(cook|fed)"),
]
# People and pressure words inside the US MONETARY cell (contracts that do carry a direction).
PEOPLE = r"powell|warsh|hassett|trump|chair|governor|independen|bessent|miran|cook"


def _fed_group(t: str) -> str | None:
    import re
    for name, rx in FED_GROUPS:
        if re.search(rx, t):
            return name
    return None


def run(cfg: dict | None = None) -> None:
    cfg = cfg or load_config()
    out = rpath("results", cfg) / "notes" / "strategy_a_checks"
    out.mkdir(parents=True, exist_ok=True)
    proc = rpath("processed", cfg)
    per = _periods(cfg)
    hl = cfg["smoothing"]["ewma_halflife_days"]

    # ---------------- 3a. Fed-related contracts.
    lab = pd.read_parquet(proc / "contracts_classified.parquet")
    lab["group"] = lab["title"].fillna("").str.lower().map(_fed_group)
    fed = lab[lab["group"].notna()].copy()
    fed["contract_id"] = fed["platform"] + ":" + fed["platform_id"]
    cd = pd.read_parquet(proc / "contract_days.parquet", columns=["contract_id", "eligible"])
    in_panel = set(cd["contract_id"])
    elig = set(cd.loc[cd["eligible"], "contract_id"])
    fed["in_panel"] = fed["contract_id"].isin(in_panel)
    fed["eligible_once"] = fed["contract_id"].isin(elig)
    con = connect()
    con.register("ids", fed[["platform", "platform_id"]])
    vol = con.execute(f"""
        SELECT p.platform, p.platform_id, year(p.snap_date) AS year, sum(p.volume_usd) AS volume_usd
        FROM read_parquet('{sql_path(proc / "pm_daily.parquet")}') p
        SEMI JOIN ids ON p.platform = ids.platform AND p.platform_id = ids.platform_id
        GROUP BY ALL""").df()
    vy = vol.pivot_table(index=["platform", "platform_id"], columns="year", values="volume_usd", aggfunc="sum").fillna(0.0)
    vy.columns = [f"volume_usd_m_{c}" for c in vy.columns]
    fed = fed.merge(vy / 1e6, left_on=["platform", "platform_id"], right_index=True, how="left")
    vcols = [c for c in fed if c.startswith("volume_usd_m_")]
    fed[vcols] = fed[vcols].fillna(0.0)
    fed[["group", "title", "theme", "direction", "direction_rule", "in_panel", "eligible_once"] + vcols].sort_values(
        ["group", vcols[-1]], ascending=[True, False]).to_csv(out / "a_fed_contracts.csv", index=False)
    summ = fed.groupby(["group", "theme", "direction", "direction_rule"]).agg(
        n_contracts=("contract_id", "size"), in_panel=("in_panel", "sum"), eligible_once=("eligible_once", "sum"),
        **{c: (c, "sum") for c in vcols}).reset_index()
    summ.to_csv(out / "a_fed_summary.csv", index=False)
    # Inside the US MONETARY cell: contracts whose title names people or pressure words.
    rows = _rows(cfg)
    mon = _cell(rows, "US", "MONETARY")
    mon["people"] = mon["title"].str.lower().str.contains(PEOPLE, regex=True)
    mon["fed_group"] = mon["title"].str.lower().map(_fed_group)
    mon["year"] = mon["day"].dt.year
    by = mon.groupby("year").apply(lambda g: pd.Series({
        "n_contracts": g["contract_id"].nunique(),
        "share_abs_contrib_fed_groups": g.loc[g["fed_group"].notna(), "contrib"].abs().sum() / g["contrib"].abs().sum(),
        "share_abs_contrib_people_words": g.loc[g["people"], "contrib"].abs().sum() / g["contrib"].abs().sum(),
        "n_contracts_people_words": g.loc[g["people"], "contract_id"].nunique()}))
    by.to_csv(out / "a_us_monetary_share_by_year.csv")
    mon.loc[mon["people"]].groupby(["contract_id", "title", "unit", "sign"]).agg(
        days=("day", "size"), abs_contrib=("contrib", lambda s: s.abs().sum())).reset_index().sort_values(
        "abs_contrib", ascending=False).to_csv(out / "a_us_monetary_people_contracts.csv", index=False)

    # ---------------- 3b. Windows.
    ctx = run_a.prepare(cfg)
    days, rx = ctx["days"], ctx["rx"].reindex(ctx["days"])
    sig = ctx["sig50"]
    cal = pd.date_range(cfg["sample"]["start"], cfg["sample"]["end"], freq="D")
    zero = pd.Series(0.0, index=cal)
    y = run_a.forecast(ctx, "A1")["EUR"]
    y_mon = -sig[("US", "MONETARY")].reindex(days, method="ffill").fillna(0.0)
    y_fis = y - y_mon
    mult, reg = _regime_mult(ctx, days)
    a1 = run_a.evaluate(ctx, "A1", False)
    mon_only = run_a.evaluate(ctx, "A1", False, sigs={**sig, ("US", "FISCAL_POLITICAL"): zero})
    fis_only = run_a.evaluate(ctx, "A1", False, sigs={**sig, ("US", "MONETARY"): zero})
    usd = -a1.weights.reindex(days).sum(axis=1)
    lab_mf = _decisive(y_mon, y_fis, "MONETARY", "FISCAL")
    idx = pd.read_parquet(proc / "theme_index.parquet")
    idx["day"] = pd.to_datetime(idx["day"])
    d_cell = {t: idx[(idx["zone"] == "US") & (idx["theme"] == t)].set_index("day")["d_vw"]
              for t in ("MONETARY", "FISCAL_POLITICAL")}
    daily = pd.DataFrame({
        "usd_position": usd, "y": y, "usd_view_monetary": -y_mon, "usd_view_fiscal": -y_fis,
        "us_fiscal_dominance": reg, "decisive_term": lab_mf,
        "d_us_monetary": d_cell["MONETARY"].reindex(days), "d_us_fiscal": d_cell["FISCAL_POLITICAL"].reindex(days),
        "a1_gross": a1.gross_ret.reindex(days), "a1_net": a1.net_ret.reindex(days),
        "a1_monetary_only_gross": mon_only.gross_ret.reindex(days),
        "a1_fiscal_only_gross": fis_only.gross_ret.reindex(days),
        "usd_basket_ret": -rx.mean(axis=1)})
    eps = metrics.drawdown_episodes(a1.net_ret.loc[per["2024-2026"][0]:], 1)
    windows = {"Iran war (Feb-Apr 2026)": tuple(pd.Timestamp(x) for x in EPISODES["Iran war (Feb-Apr 2026)"]),
               "Worst drawdown": (eps["peak"].iloc[0], eps["trough"].iloc[0]),
               "FOMC 2026-09-16 (2026-09-09 to end of sample)": (pd.Timestamp("2026-09-09"), pd.Timestamp(cfg["sample"]["end"]))}
    rows_w = []
    for name, (s0, s1) in windows.items():
        seg = daily.loc[s0:s1]
        lab_prev = seg["decisive_term"].shift(1)
        rows_w.append({"window": name, "start": s0.date(), "end": s1.date(), "days": len(seg),
                       "mean_usd_position": seg["usd_position"].mean(),
                       "share_days_long_usd": (seg["usd_position"] > 0).mean(),
                       "usd_sign_changes": int((np.sign(seg["usd_position"]).diff().fillna(0) != 0).sum()),
                       "share_days_fiscal_dominance": seg["us_fiscal_dominance"].mean(),
                       "mean_usd_view_monetary": seg["usd_view_monetary"].mean(),
                       "mean_usd_view_fiscal": seg["usd_view_fiscal"].mean(),
                       "share_days_terms_agree": (np.sign(seg["usd_view_monetary"]) == np.sign(seg["usd_view_fiscal"])).mean(),
                       "a1_gross_cum": seg["a1_gross"].sum(), "a1_net_cum": seg["a1_net"].sum(),
                       "monetary_only_gross_cum": seg["a1_monetary_only_gross"].sum(),
                       "fiscal_only_gross_cum": seg["a1_fiscal_only_gross"].sum(),
                       "usd_basket_cum": seg["usd_basket_ret"].sum(),
                       **{f"a1_gross_cum_days_{k}": seg["a1_gross"][lab_prev == k].sum()
                          for k in ("MONETARY and FISCAL agree", "MONETARY sets the sign (FISCAL opposite)",
                                    "FISCAL sets the sign (MONETARY opposite)")}})
    pd.DataFrame(rows_w).to_csv(out / "b_windows.csv", index=False)
    s0, s1 = windows["FOMC 2026-09-16 (2026-09-09 to end of sample)"]
    daily.loc[s0:s1].to_csv(out / "b_fomc_daily.csv")
    moves = []
    for cname, theme in (("US MONETARY", "MONETARY"), ("US FISCAL_POLITICAL", "FISCAL_POLITICAL")):
        c = _cell(rows, "US", theme)
        c = c[(c["day"] >= s0) & (c["day"] <= s1)]
        for day, g in c.groupby("day"):
            for r in g.assign(a=g["contrib"].abs()).sort_values("a", ascending=False).head(3).itertuples():
                moves.append({"cell": cname, "day": day.date(), "cell_d_vw": g["contrib"].sum(), "title": r.title,
                              "unit": r.unit, "sign": r.sign, "value": r.value, "z": r.z, "weight": r.w,
                              "contribution": r.contrib})
    pd.DataFrame(moves).to_csv(out / "b_fomc_contracts.csv", index=False)

    # ---------------- 3c. Average USD position and the MONETARY drift.
    cell_mon = idx[(idx["zone"] == "US") & (idx["theme"] == "MONETARY")]
    act = cell_mon.set_index("day")["n_contracts"] > 0
    d_mon = cell_mon.set_index("day")["d_vw"]
    full_mean = d_mon[act].mean()
    ex_post = cell_mon.assign(d_vw=np.where(cell_mon["n_contracts"] > 0, cell_mon["d_vw"] - full_mean, 0.0))
    runs = {"A1": a1,
            "A1, MONETARY change demeaned causally (expanding mean to t-1, D12 method)":
                run_a.evaluate(ctx, "A1", False, sigs={**sig, ("US", "MONETARY"): A.cell_signal(cell_mon, hl, demean=True)}),
            "A1, MONETARY change demeaned ex post (2024-2026 mean, look-ahead)":
                run_a.evaluate(ctx, "A1", False, sigs={**sig, ("US", "MONETARY"): A.cell_signal(ex_post, hl)}),
            "A1 MONETARY only": mon_only,
            "A1 MONETARY only, demeaned causally":
                run_a.evaluate(ctx, "A1", False, sigs={**sig, ("US", "FISCAL_POLITICAL"): zero,
                                                       ("US", "MONETARY"): A.cell_signal(cell_mon, hl, demean=True)})}
    c_rows = []
    for name, res in runs.items():
        u = -res.weights.reindex(days).sum(axis=1)
        for lab_, (a_, b_) in per.items():
            c_rows.append({"run": name, "period": lab_, "mean_usd_position": u.loc[a_:b_].mean(),
                           "share_days_long_usd": (u.loc[a_:b_] > 0).mean(),
                           "gross_ann_mean": _stats(res.gross_ret.loc[a_:b_])["ann_mean"],
                           "gross_sharpe": _stats(res.gross_ret.loc[a_:b_])["sharpe"],
                           "net_sharpe": _stats(res.net_ret.loc[a_:b_])["sharpe"]})
    pd.DataFrame(c_rows).to_csv(out / "c_usd_position_drift.csv", index=False)
    zm = sig[("US", "MONETARY")]
    mon["sgn_contrib"] = mon["contrib"]
    drift = []
    for lab_, (a_, b_) in per.items():
        dd = d_mon.loc[a_:b_]
        aa = act.loc[a_:b_]
        mm = mon[(mon["day"] >= a_) & (mon["day"] <= b_)]
        n_act = int(aa.sum())
        drift.append({"period": lab_, "active_days": n_act, "mean_d_active": dd[aa].mean(),
                      "t_mean_d": dd[aa].mean() / dd[aa].std() * np.sqrt(n_act),
                      "index_change": dd.sum(), "mean_z_monetary": zm.loc[a_:b_].mean(),
                      "share_days_z_monetary_positive": (zm.reindex(days).loc[a_:b_] > 0).mean(),
                      **{f"index_change_from_{u}": mm.loc[mm["unit"] == u, "contrib"].sum() for u in ("bp", "hazard", "prob")}})
    pd.DataFrame(drift).to_csv(out / "c_monetary_drift.csv", index=False)
    log.info("strategy A checks: tables in %s", out)


if __name__ == "__main__":
    run()
