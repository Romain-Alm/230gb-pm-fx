"""Strategy A explained: diagnostics and documentation only (2026-10-07; DECISIONS, reporting).

No rule, variant or parameter is changed: every series below is rebuilt from the frozen
pipeline (contract changes, cell signals, A1 positions) and only decomposed or compared.
Tables are written to results/notes/strategy_a_explained/; the note itself is
results/notes/strategy_a_explained.md.

  A  unit counts of the contract panel (bp / pp / pct partitions) and unit shares in A1 cells;
  B  US FISCAL_POLITICAL content by sub-type (diagnostic labels defined here, not used by any
     rule), direction rules with examples, sign review, and the A1 gross P&L split
     (leave-one-out counterfactuals and the decisive-term decomposition);
  C  dollar momentum diagnostic: same-day correlation, 1-day and 5-day time-series momentum
     benchmarks with A1's portfolio construction, Newey-West regressions;
  D  A1 in the 2026 Iran war window and in its worst drawdown: net USD position, MONETARY vs
     FISCAL contributions, largest index moves.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd
import statsmodels.api as sm

from src.backtest import engine, metrics
from src.common import get_logger, load_config, rpath
from src.risk.risk import EPISODES
from src.strategies import run_a
from src.strategies import strategy_a as A

log = get_logger("strategy_a_explained")
PPY = 252

# Diagnostic sub-types of US FISCAL_POLITICAL contracts. First match wins, on
# lower(title) + " | " + lower(event_text). Defined for this note after looking at the cell
# content; they label contracts and never enter a rule.
SUBTYPES = [
    ("other (not US fiscal)", r"trudeau|poilievre|ishiba|first leader out|infantino|fifa|kimmel|moltbook"),
    ("government shutdown", r"shut ?down|shut down|funding bill|back pay|government funding|dhs fund"),
    ("debt ceiling", r"debt (ceiling|limit)"),
    ("budget and tax bills", r"budget|reconciliation|\btax|big beautiful bill|deficit|appropriation"),
    ("appointments and departures", r"resign|fired|impeach|\bout as\b|\bleaves?\b|retire|nominat|confirm"),
    ("elections", r"election|presiden|popular vote|electoral college|inaugurat|balance of power|"
                  r"win the (u\.s\. )?(house|senate)|control (the )?(house|senate)|house control|senate control|"
                  r"seats in the house|midterm|blue state|drop out"),
]
ELECTION = "elections"

# Contracts whose assigned sign is questionable on reading (sign review, not a rule change).
SIGN_REVIEW = [
    ("Democratic presidency combination signed +1",
     r"democratic party win the presidency", 1),
    ("Harris Electoral College win signed +1",
     r"harris win the electoral college", 1),
    ("Departure or resignation signed +1 by the generic fiscal:up rule",
     r"resign|drop out|fired|\bout as\b|\bleaves?\b|impeach", 1),
]


def _periods(cfg):
    return {"2024-2025": (cfg["sample"]["start"], cfg["sample"]["train_end"]),
            "2026": (cfg["sample"]["test_start"], cfg["sample"]["end"]),
            "2024-2026": (cfg["sample"]["start"], cfg["sample"]["end"])}


def subtype(text: str) -> str:
    for name, rx in SUBTYPES:
        if re.search(rx, text):
            return name
    return "other"


def _rows(cfg) -> pd.DataFrame:
    """Contract-day rows with their standardised change (same join as indices.load_rows, using
    the change table written by indices.build), plus titles and classification fields."""
    proc = rpath("processed", cfg)
    cd = pd.read_parquet(proc / "contract_days.parquet")
    ch = pd.read_parquet(proc / "contract_changes.parquet")
    cd["day"], ch["day"] = pd.to_datetime(cd["day"]), pd.to_datetime(ch["day"])
    rows = cd.merge(ch[["contract_id", "day", "z", "dv"]], on=["contract_id", "day"], how="inner")
    lab = pd.read_parquet(proc / "contracts_classified.parquet")
    mk = pd.read_parquet(proc / "pm_markets.parquet", columns=["platform", "platform_id", "event_text"])
    lab = lab.merge(mk, on=["platform", "platform_id"], how="left")
    lab["contract_id"] = lab["platform"] + ":" + lab["platform_id"]
    rows = rows.merge(lab[["contract_id", "title", "direction_rule", "event_text"]], on="contract_id", how="left")
    rows["title"] = rows["title"].fillna("[partition EV] " + rows["event_key"].astype(str))
    return rows


def _cell(rows, zone, theme):
    r = rows[(rows["zone"] == zone) & (rows["theme"] == theme) & rows["eligible"] & rows["z"].notna()].copy()
    r["w"] = r["vol7d"] / r.groupby("day")["vol7d"].transform("sum")
    r["contrib"] = r["w"] * r["z"]           # sums to the cell's d_vw on each day
    return r


def _split_cell_signal(cell_idx: pd.DataFrame, parts: dict[str, pd.Series], hl: float) -> dict:
    """Additive split of A.cell_signal: the EWMA is linear and the scale (expanding sd of the
    full smoothed signal up to t-1) is common, so z = sum of the part signals."""
    c = cell_idx.sort_values("day").set_index("day")
    active = c["n_contracts"] > 0
    s = c["d_vw"].where(active, 0.0).ewm(halflife=hl).mean()
    n_active = active.cumsum().shift(1).fillna(0)
    sd = s.where(n_active > 0).expanding(min_periods=A.MIN_ACTIVE).std().shift(1)
    out = {}
    for k, d in parts.items():
        sk = d.reindex(c.index).fillna(0.0).where(active, 0.0).ewm(halflife=hl).mean()
        out[k] = (sk / sd).where(n_active >= A.MIN_ACTIVE).fillna(0.0)
    full = A.cell_signal(cell_idx, hl)
    assert np.allclose(sum(out.values()), full.reindex(c.index), atol=1e-9), "split does not add up"
    return out


def _regime_mult(ctx, days):
    """Multiplier of the US fiscal signal in A1's forecast: y_FIS = mult * z_FIS
    (-1 under monetary dominance, +1 under fiscal dominance; strategy_a.pair_components)."""
    reg = ctx["regime"]["US"].reindex(days, method="ffill").fillna(0.0)
    return pd.Series(np.where(reg == 1, 1.0, -1.0), index=days), reg


def _decisive(a: pd.Series, b: pd.Series, na: str, nb: str) -> pd.Series:
    """Which of two terms sets the sign of a + b: both agree (or one is zero), or the larger one
    against an opposite smaller one."""
    agree = (np.sign(a) == np.sign(b)) | (a == 0) | (b == 0)
    lab = np.where(agree, f"{na} and {nb} agree",
                   np.where(a.abs() > b.abs(), f"{na} sets the sign ({nb} opposite)",
                            f"{nb} sets the sign ({na} opposite)"))
    return pd.Series(lab, index=a.index).where((a + b) != 0, "flat")


def _stats(r: pd.Series) -> dict:
    s = metrics.perf_stats(r.dropna())
    return {"ann_mean": s.get("ann_mean"), "ann_vol": s.get("ann_vol"), "sharpe": s.get("sharpe")}


def _nw(y: pd.Series, x: pd.Series) -> dict:
    d = pd.concat([y, x], axis=1).dropna()
    T = len(d)
    lags = int(np.floor(4 * (T / 100) ** (2 / 9)))
    res = sm.OLS(d.iloc[:, 0], sm.add_constant(d.iloc[:, 1])).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return {"n": T, "nw_lags": lags, "beta": res.params.iloc[1], "t_beta": res.tvalues.iloc[1],
            "alpha_ann": res.params.iloc[0] * PPY, "t_alpha": res.tvalues.iloc[0],
            "corr": d.iloc[:, 0].corr(d.iloc[:, 1]), "r2": res.rsquared}


def run(cfg: dict | None = None) -> dict:
    cfg = cfg or load_config()
    out = rpath("results", cfg) / "notes" / "strategy_a_explained"
    out.mkdir(parents=True, exist_ok=True)
    per = _periods(cfg)
    hl = cfg["smoothing"]["ewma_halflife_days"]
    proc = rpath("processed", cfg)
    rows = _rows(cfg)
    idx = pd.read_parquet(proc / "theme_index.parquet")
    idx["day"] = pd.to_datetime(idx["day"])

    # ---------------- A. Units of the contract panel.
    cd = pd.read_parquet(proc / "contract_days.parquet", columns=["contract_id", "unit", "zone", "theme", "eligible", "n_buckets"])
    u = cd.drop_duplicates("contract_id").groupby("unit").size().rename("n_contracts_panel")
    ue = cd[cd["eligible"]].drop_duplicates("contract_id").groupby("unit").size().rename("n_contracts_eligible_once")
    units = pd.concat([u, ue], axis=1).fillna(0).astype(int)
    units.to_csv(out / "a_units.csv")
    part = (cd[cd["unit"].isin(["bp", "pp", "pct"])].drop_duplicates(["contract_id", "zone"])
              .groupby(["unit", "zone", "theme"]).size().rename("n_contracts").reset_index())
    part.to_csv(out / "a_partition_cells.csv", index=False)
    a1_units = []
    for theme in ("MONETARY", "FISCAL_POLITICAL"):
        c = _cell(rows, "US", theme)
        g = c.groupby("unit").agg(n_contracts=("contract_id", "nunique"), abs_contrib=("contrib", lambda s: s.abs().sum()))
        g["share_abs_contrib"] = g["abs_contrib"] / g["abs_contrib"].sum()
        a1_units.append(g.reset_index().assign(cell=f"US {theme}"))
    pd.concat(a1_units).to_csv(out / "a_units_in_a1_cells.csv", index=False)

    # ---------------- B. US FISCAL_POLITICAL content.
    fis = _cell(rows, "US", "FISCAL_POLITICAL")
    fis["text"] = (fis["title"].str.lower() + " | " + fis["event_text"].fillna("").str.lower())
    fis["subtype"] = fis["text"].map(subtype)
    tot_abs = fis["contrib"].abs().sum()
    b1 = fis.groupby("subtype").agg(n_contracts=("contract_id", "nunique"), n_contract_days=("day", "size"),
                                    volume_usd_m=("vol1d", lambda s: s.sum() / 1e6),
                                    abs_contrib=("contrib", lambda s: s.abs().sum()),
                                    signed_contrib=("contrib", "sum"))
    b1["share_contracts"] = b1["n_contracts"] / fis["contract_id"].nunique()
    b1["share_volume"] = b1["volume_usd_m"] / b1["volume_usd_m"].sum()
    b1["share_abs_contrib"] = b1["abs_contrib"] / tot_abs
    b1.sort_values("share_abs_contrib", ascending=False).to_csv(out / "b1_us_fiscal_subtypes.csv")
    con = (fis.groupby(["contract_id"]).agg(title=("title", "first"), subtype=("subtype", "first"),
                                            sign=("sign", "first"), rule=("direction_rule", "first"),
                                            volume_usd_m=("vol1d", lambda s: s.sum() / 1e6),
                                            abs_contrib=("contrib", lambda s: s.abs().sum()),
                                            first_day=("day", "min"), last_day=("day", "max"))
              .sort_values("volume_usd_m", ascending=False))
    con["share_abs_contrib"] = con["abs_contrib"] / tot_abs
    con.to_csv(out / "b_us_fiscal_contracts.csv")
    b2 = (fis.groupby(["subtype", "direction_rule", "sign"]).agg(n_contracts=("contract_id", "nunique"),
                                                                abs_contrib=("contrib", lambda s: s.abs().sum()))
             .reset_index())
    b2["share_abs_contrib"] = b2["abs_contrib"] / tot_abs
    b2.to_csv(out / "b2_rules_by_subtype.csv", index=False)
    rev = []
    for label, rx, sgn in SIGN_REVIEW:
        m = con["title"].str.lower().str.contains(rx, regex=True) & (con["sign"] == sgn)
        if label.startswith("Departure"):
            m &= con["rule"].eq("fiscal:up") & con["subtype"].isin(["appointments and departures", ELECTION])
        for cid, r in con[m].iterrows():
            rev.append({"issue": label, "contract_id": cid, "title": r["title"], "sign": r["sign"],
                        "rule": r["rule"], "volume_usd_m": r["volume_usd_m"], "share_abs_contrib": r["share_abs_contrib"]})
    nonus = con[con["subtype"] == "other (not US fiscal)"]
    for cid, r in nonus.iterrows():
        rev.append({"issue": "Not a US fiscal market (zone defaulted to US)", "contract_id": cid, "title": r["title"],
                    "sign": r["sign"], "rule": r["rule"], "volume_usd_m": r["volume_usd_m"],
                    "share_abs_contrib": r["share_abs_contrib"]})
    pd.DataFrame(rev).to_csv(out / "b2_sign_review.csv", index=False)

    # B.3 A1 gross P&L. A1 keeps only the sign of y (the volatility target removes its size), so
    # splitting the P&L in proportion to the terms of y is not meaningful (the shares explode when
    # y is close to zero). Reported instead: (i) leave-one-out counterfactuals, A1 rebuilt with a
    # component removed; (ii) the decisive-term decomposition: each day is classified by which
    # term sets the sign of y. The fiscal signal splits exactly into sub-type parts (linear EWMA,
    # common scale), which gives the fiscal terms of y.
    ctx = run_a.prepare(cfg)
    days, rx, hs = ctx["days"], ctx["rx"].reindex(ctx["days"]), ctx["hs"].reindex(ctx["days"])
    mult, reg = _regime_mult(ctx, days)
    sig = ctx["sig50"]
    cal = pd.date_range(cfg["sample"]["start"], cfg["sample"]["end"], freq="D")
    fis_parts = {k: g.groupby("day")["contrib"].sum().reindex(cal).fillna(0.0) for k, g in fis.groupby("subtype")}
    cell_fis = idx[(idx["zone"] == "US") & (idx["theme"] == "FISCAL_POLITICAL")]
    z_fis_parts = _split_cell_signal(cell_fis, fis_parts, hl)
    z_mon = sig[("US", "MONETARY")].reindex(days, method="ffill").fillna(0.0)
    y_parts = {"MONETARY": -z_mon}
    for k, z in z_fis_parts.items():
        y_parts[f"FISCAL: {k}"] = mult * z.reindex(days, method="ffill").fillna(0.0)
    y = run_a.forecast(ctx, "A1")["EUR"]
    assert np.allclose(sum(y_parts.values()), y, atol=1e-9), "A1 forecast decomposition does not add up"
    y_mon = y_parts["MONETARY"]
    y_fis = sum(v for k, v in y_parts.items() if k.startswith("FISCAL"))
    a1 = run_a.evaluate(ctx, "A1", False)
    usd = -a1.weights.reindex(days).sum(axis=1)             # > 0: long USD against the G10 basket
    lab_mf = _decisive(y_mon, y_fis, "MONETARY", "FISCAL")
    g = a1.gross_ret.reindex(days)
    b3 = []
    for lab_, (s0, s1) in per.items():
        l = lab_mf.shift(1).loc[s0:s1]                      # decision at t, return on row t+1
        gg = g.loc[s0:s1]
        for k in l.dropna().unique():
            m = l == k
            b3.append({"period": lab_, "bucket": k, "share_days": m.mean(), "cum_gross": gg[m].sum(),
                       "ann_gross_contribution": gg[m].sum() / (len(gg) / PPY), "hit_rate": (gg[m] > 0).mean()})
    pd.DataFrame(b3).to_csv(out / "b3_decisive_terms.csv", index=False)
    chk = pd.DataFrame({"period": list(per), "share_days_position_sign_equals_signal_sign": [
        (np.sign(usd.loc[a_:b_]) == np.sign(-y.loc[a_:b_])).mean() for a_, b_ in per.values()]})
    chk.to_csv(out / "b3_position_vs_signal_sign.csv", index=False)

    def with_fis(part_keys):
        sub = fis[fis["subtype"].isin(part_keys)]
        d = sub.groupby("day").apply(lambda g: (g["z"] * g["vol7d"]).sum() / g["vol7d"].sum())
        n = sub.groupby("day")["contract_id"].nunique()
        cell = pd.DataFrame({"day": cal, "d_vw": d.reindex(cal).fillna(0.0).values,
                             "n_contracts": n.reindex(cal).fillna(0).values})
        s = dict(sig)
        s[("US", "FISCAL_POLITICAL")] = A.cell_signal(cell, hl)
        return s

    zero = pd.Series(0.0, index=cal)
    others = [k for k in fis_parts if k != ELECTION]
    cf = {"A1": None,
          "A1 MONETARY only": {**sig, ("US", "FISCAL_POLITICAL"): zero},
          "A1 FISCAL only": {**sig, ("US", "MONETARY"): zero},
          "A1, fiscal cell = election contracts only": with_fis([ELECTION]),
          "A1, fiscal cell without election contracts": with_fis(others),
          "A1 FISCAL only, election contracts only": {**with_fis([ELECTION]), ("US", "MONETARY"): zero},
          "A1 FISCAL only, without election contracts": {**with_fis(others), ("US", "MONETARY"): zero}}
    b3b, cf_res = [], {}
    for name, s in cf.items():
        res = run_a.evaluate(ctx, "A1", False, sigs=s)
        cf_res[name] = res
        for lab_, (s0, s1) in per.items():
            b3b.append({"run": name, "period": lab_, **{f"gross_{k}": v for k, v in _stats(res.gross_ret.loc[s0:s1]).items()},
                        "net_sharpe": _stats(res.net_ret.loc[s0:s1])["sharpe"]})
    pd.DataFrame(b3b).to_csv(out / "b3_counterfactuals.csv", index=False)
    loo = []
    for comp, without in (("US MONETARY", "A1 FISCAL only"), ("US FISCAL_POLITICAL", "A1 MONETARY only"),
                          ("FISCAL: election contracts", "A1, fiscal cell without election contracts"),
                          ("FISCAL: rest of the cell", "A1, fiscal cell = election contracts only")):
        for lab_, (s0, s1) in per.items():
            full, wo = cf_res["A1"].gross_ret.loc[s0:s1], cf_res[without].gross_ret.loc[s0:s1]
            loo.append({"component": comp, "period": lab_, "a1_gross_ann": full.mean() * PPY,
                        "without_gross_ann": wo.mean() * PPY, "marginal_gross_ann": (full.mean() - wo.mean()) * PPY,
                        "a1_gross_sharpe": _stats(full)["sharpe"], "without_gross_sharpe": _stats(wo)["sharpe"]})
    pd.DataFrame(loo).to_csv(out / "b3_leave_one_out.csv", index=False)

    # Sign of "Trump wins": regime around the 2024 election.
    reg_e = pd.DataFrame({"us_regime_fiscal_dominance": reg, "fiscal_multiplier": mult,
                          "z_us_fiscal": sig[("US", "FISCAL_POLITICAL")].reindex(days, method="ffill"),
                          "y_fiscal": sum(v for k, v in y_parts.items() if k.startswith("FISCAL")),
                          "y_monetary": y_parts["MONETARY"], "y": y,
                          "usd_position": -a1.weights.reindex(days).sum(axis=1)}).loc["2024-10-28":"2024-11-15"]
    reg_e.to_csv(out / "b2_election_window.csv")

    # ---------------- C. Dollar momentum diagnostic.
    logs = np.log(ctx["fx"].spot[A.PAIRS.keys()]).reindex(ctx["days_warm"])
    usd_ret = -logs.diff().mean(axis=1)                    # USD against the equal-weighted G10 basket
    u = -y                                                 # > 0: A1 long USD
    c1 = []
    for lab_, (s0, s1) in per.items():
        uu, bb = u.loc[s0:s1], usd_ret.reindex(days).loc[s0:s1]
        row = {"period": lab_, "n": int(len(uu)),
               "corr_signal_sameday": uu.corr(bb), "corr_sign_sameday": np.sign(uu).corr(bb),
               "corr_signal_prev_day": uu.corr(usd_ret.shift(1).reindex(days).loc[s0:s1]),
               "corr_signal_past5": uu.corr(usd_ret.rolling(5).sum().reindex(days).loc[s0:s1]),
               "corr_signal_next_day": uu.corr(usd_ret.shift(-1).reindex(days).loc[s0:s1])}
        c1.append(row)
    pd.DataFrame(c1).to_csv(out / "c1_correlations.csv", index=False)
    rx_w = ctx["rx"].reindex(ctx["days_warm"])
    fb = rx_w.mean(axis=1)                                 # foreign-basket excess return, row t = t-1 -> t
    bench = {}
    for k in (1, 5):
        f = np.sign(fb.rolling(k).sum()).reindex(days).fillna(0.0)
        F = pd.DataFrame({c: f for c in A.PAIRS}, index=days)
        w = A.positions(F, rx, cfg, False)
        bench[f"TSMOM {k}d"] = engine.run(w, rx, hs)
    a1w = engine.run(run_a.hold_weights(a1.weights.reindex(days), days, "weekly"), rx, hs)
    strategies = {"A1": a1, "A1 weekly": a1w}
    c2, c3 = [], []
    for name, res in {**bench, **strategies}.items():
        for lab_, (s0, s1) in per.items():
            c2.append({"series": name, "period": lab_, **{f"gross_{k}": v for k, v in _stats(res.gross_ret.loc[s0:s1]).items()},
                       "net_sharpe": _stats(res.net_ret.loc[s0:s1])["sharpe"]})
    for sname, sres in strategies.items():
        for bname, bres in bench.items():
            ua = -sres.weights.reindex(days).sum(axis=1)
            ub = -bres.weights.reindex(days).sum(axis=1)
            for lab_, (s0, s1) in per.items():
                r = _nw(sres.gross_ret.loc[s0:s1], bres.gross_ret.loc[s0:s1])
                agree = (np.sign(ua.loc[s0:s1]) == np.sign(ub.loc[s0:s1])).mean()
                c3.append({"strategy": sname, "benchmark": bname, "period": lab_, **r,
                           "share_days_same_usd_sign": agree})
    pd.DataFrame(c2).to_csv(out / "c2_benchmarks.csv", index=False)
    pd.DataFrame(c3).to_csv(out / "c3_regressions.csv", index=False)

    # ---------------- D. Iran war and the worst drawdown.
    eps = metrics.drawdown_episodes(a1.net_ret.loc[per["2024-2026"][0]:], 1)
    dd = (eps["peak"].iloc[0], eps["trough"].iloc[0])
    iran = tuple(pd.Timestamp(x) for x in EPISODES["Iran war (Feb-Apr 2026)"])
    windows = {"Iran war (Feb-Apr 2026)": iran, "Worst drawdown": dd}
    dser = pd.DataFrame({"usd_position": usd, "gross_exposure": a1.weights.reindex(days).abs().sum(axis=1),
                         "y": y, "y_monetary": y_parts["MONETARY"], "y_fiscal": y_fis,
                         "us_fiscal_dominance": reg, "gross_ret": a1.gross_ret.reindex(days),
                         "gross_ret_monetary_only": cf_res["A1 MONETARY only"].gross_ret.reindex(days),
                         "gross_ret_fiscal_only": cf_res["A1 FISCAL only"].gross_ret.reindex(days),
                         "decisive_term": lab_mf})
    dser.loc["2026-01-01":].to_csv(out / "d_daily_2026.csv")
    d1 = []
    for wname, (s0, s1) in windows.items():
        seg = dser.loc[s0:s1]
        d1.append({"window": wname, "start": s0.date(), "end": s1.date(), "days": len(seg),
                   "share_days_long_usd": (seg["usd_position"] > 0).mean(),
                   "share_days_short_usd": (seg["usd_position"] < 0).mean(),
                   "mean_usd_position": seg["usd_position"].mean(),
                   "usd_sign_changes": int((np.sign(seg["usd_position"]).diff().fillna(0) != 0).sum()),
                   "share_days_fiscal_dominance": seg["us_fiscal_dominance"].mean(),
                   "share_days_mon_fis_same_sign": (np.sign(seg["y_monetary"]) == np.sign(seg["y_fiscal"])).mean(),
                   "share_days_monetary_dominates_y": (seg["y_monetary"].abs() > seg["y_fiscal"].abs()).mean(),
                   "a1_gross_cum": seg["gross_ret"].sum(),
                   "monetary_only_gross_cum": seg["gross_ret_monetary_only"].sum(),
                   "fiscal_only_gross_cum": seg["gross_ret_fiscal_only"].sum(),
                   **{f"a1_gross_cum_days_{k}": seg["gross_ret"][seg["decisive_term"].shift(1) == k].sum()
                      for k in lab_mf.unique()}})
    pd.DataFrame(d1).to_csv(out / "d1_windows.csv", index=False)
    weekly = dser.loc[min(iran[0], dd[0]):max(iran[1], dd[1])].resample("W-FRI").agg(
        {"usd_position": "mean", "y_monetary": "mean", "y_fiscal": "mean", "us_fiscal_dominance": "mean",
         "gross_ret": "sum", "gross_ret_monetary_only": "sum", "gross_ret_fiscal_only": "sum"})
    weekly.to_csv(out / "d2_weekly.csv")
    mon = _cell(rows, "US", "MONETARY")
    moves = []
    s0, s1 = min(iran[0], dd[0]), max(iran[1], dd[1])
    for cname, c in (("US MONETARY", mon), ("US FISCAL_POLITICAL", fis)):
        d = c[(c["day"] >= s0) & (c["day"] <= s1)]
        tot = d.groupby("day")["contrib"].sum()
        for day in tot.abs().sort_values(ascending=False).head(8).index:
            top = d[d["day"] == day].assign(a=lambda x: x["contrib"].abs()).sort_values("a", ascending=False).head(3)
            for r in top.itertuples():
                moves.append({"cell": cname, "day": day.date(), "cell_d_vw": tot[day], "title": r.title,
                              "unit": r.unit, "sign": r.sign, "value": r.value, "z": r.z, "weight": r.w,
                              "contribution": r.contrib})
    pd.DataFrame(moves).to_csv(out / "d3_largest_moves.csv", index=False)
    lev = []
    for cname, theme in (("US MONETARY", "MONETARY"), ("US FISCAL_POLITICAL", "FISCAL_POLITICAL")):
        g = idx[(idx["zone"] == "US") & (idx["theme"] == theme)].set_index("day")
        zz = sig[("US", theme)]
        for wname, (a0, a1_) in windows.items():
            lev.append({"cell": cname, "window": wname, "index_change": g["index_vw"].loc[a1_] - g["index_vw"].loc[a0],
                        "z_start": zz.loc[a0], "z_end": zz.loc[a1_], "z_mean": zz.loc[a0:a1_].mean()})
    pd.DataFrame(lev).to_csv(out / "d4_index_levels.csv", index=False)
    _figure(dser, windows, out / "a1_2026_decomposition.png")
    log.info("strategy A explained: tables in %s", out)
    return {"dser": dser}


def _figure(dser: pd.DataFrame, windows: dict, path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    d = dser.loc["2026-01-01":]
    fig, ax = plt.subplots(3, 1, figsize=(11, 8), sharex=True)
    ax[0].plot(d.index, d["gross_ret"].cumsum(), color="black", label="A1 gross")
    ax[0].plot(d.index, d["gross_ret_monetary_only"].cumsum(), color="tab:blue", label="A1 with US MONETARY only")
    ax[0].plot(d.index, d["gross_ret_fiscal_only"].cumsum(), color="tab:red", label="A1 with US FISCAL only")
    ax[0].set_ylabel("cumulative return")
    ax[1].plot(d.index, d["usd_position"], color="black")
    ax[1].set_ylabel("net USD position\n(> 0 long USD)")
    ax[2].plot(d.index, -d["y_monetary"], color="tab:blue", label="US MONETARY term (USD view)")
    ax[2].plot(d.index, -d["y_fiscal"], color="tab:red", label="US FISCAL term (USD view)")
    ax[2].set_ylabel("signal term\n(> 0 favours USD)")
    for a_ in ax:
        a_.axhline(0, color="grey", lw=0.6)
        for (name, (s0, s1)), col in zip(windows.items(), ("orange", "grey")):
            a_.axvspan(s0, s1, color=col, alpha=0.15)
    ax[0].legend(loc="upper left", fontsize=8)
    ax[2].legend(loc="upper left", fontsize=8)
    ax[0].set_title("A1 in 2026: shaded orange = Iran war (Feb-Apr 2026), grey = worst drawdown")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


if __name__ == "__main__":
    run()
