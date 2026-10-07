"""Risk analysis of both strategies (spec 10.3, 10.4), from the saved strategy returns.

Equity and commodity series close in New York, after the 16:00 London FX snapshot, so
betas are estimated on weekly (Friday-to-Friday) returns to avoid asynchronous-close
bias; daily-frequency measures are reported only where timing does not matter.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.backtest import engine
from src.common import get_logger, load_config, rpath
from src.data import market
from src.risk import risk as R
from src.strategies import strategy_b as B

log = get_logger("run_risk")
G10 = ["EUR", "JPY", "GBP", "CHF", "AUD", "NZD", "CAD", "NOK", "SEK"]


def factors(cfg) -> tuple[pd.DataFrame, pd.DataFrame]:
    raw, mp = market.read_raw(cfg), market.series_map(cfg)
    days = pd.bdate_range("2023-06-01", cfg["sample"]["end"])
    rs = market.simple_series(raw, mp, "risk", days)
    fx = market.fx_panel(raw, mp, G10, days)
    g10_carry = engine.run(B.base_carry_weights(fx.carry, fx.rx, 3, 3), fx.rx).gross_ret
    daily = pd.DataFrame({
        "spx": np.log(rs["spx_tr"]).diff(), "msci_world": np.log(rs["msci_world_tr"]).diff(),
        "d_vix": rs["vix"].diff(), "brent": np.log(rs["brent"]).diff(),
        "dollar": np.log(rs["dxy"]).diff(), "g10_carry": g10_carry})
    return daily, rs


def weekly(x: pd.DataFrame | pd.Series):
    return x.resample("W-FRI").sum(min_count=1)


def news_tags(cfg) -> pd.Series:
    proc = rpath("processed", cfg)
    geo = pd.read_parquet(proc / "geo_signals.parquet").set_index("day")
    idx = pd.read_parquet(proc / "theme_index.parquet")
    tags = pd.Series(dtype=object)
    tags = pd.concat([tags, pd.Series("geopolitical shock", index=geo.index[geo["confirmed"]])])
    for (z, t), lab in ((("US", "MONETARY"), "US monetary news"), (("US", "FISCAL_POLITICAL"), "US fiscal news")):
        s = idx[(idx["zone"] == z) & (idx["theme"] == t)].set_index("day")["d_vw"]
        tags = pd.concat([tags, pd.Series(lab, index=s.index[s.abs() > 3])])
    return tags.sort_index()


def run(cfg: dict | None = None) -> dict:
    cfg = cfg or load_config()
    res_dir = rpath("results", cfg)
    out = res_dir / "risk"
    out.mkdir(parents=True, exist_ok=True)
    fac, rs = factors(cfg)
    ra = pd.read_parquet(res_dir / "strategy_a" / "returns.parquet")
    rb = pd.read_parquet(res_dir / "strategy_b" / "returns.parquet")
    fac["em_carry"] = rb["base_carry"]
    strategies = {**{c: ra[c] for c in ra.columns if not c.endswith("_gross") and "gated" not in c},
                  **{c: rb[c] for c in ("base_carry", "pm_timed", "vix_timed")}}
    tags = news_tags(cfg)
    vix_prev = rs["vix"].shift(1)
    dollar_month = np.sign(np.log(rs["dxy"]).resample("ME").last().diff()).reindex(rs.index, method="bfill")
    brent_w = weekly(fac["brent"])
    brent_big = (brent_w.abs() > 1.5 * brent_w.std()).reindex(rs.index, method="bfill")
    geo = pd.read_parquet(rpath("processed", cfg) / "geo_signals.parquet").set_index("day")
    shock_day = geo["confirmed"].reindex(rs.index, fill_value=False)
    # Liquidity (reporting only): average 1-month forward half-spread of the strategy's own
    # universe, same causal 20-day median as the costs, known at t-1.
    from src.strategies.run_b import em_universe
    raw_m, mp_m = market.read_raw(cfg), market.series_map(cfg)
    hsd = cfg["costs"].get("half_spread_median_days", 1)
    liq = {"A": market.fx_panel(raw_m, mp_m, G10, rs.index, hsd).half_spread.mean(axis=1).shift(1),
           "B": market.fx_panel(raw_m, mp_m, em_universe(cfg, mp_m), rs.index, hsd).half_spread.mean(axis=1).shift(1)}

    beta_rows, down_rows, cond_rows, ep_rows, dd_rows = [], [], [], [], []
    for name, r in strategies.items():
        r = r.dropna()
        f_use = fac.drop(columns=["em_carry"]) if name == "base_carry" else fac   # no beta on itself
        wb = R.betas(weekly(r), weekly(f_use.drop(columns=["d_vix"])).join(weekly(f_use["d_vix"])), nw_lags=4)
        beta_rows.append(wb.assign(strategy=name))
        for mkt in ("msci_world", "em_carry"):
            if mkt == "em_carry" and name in ("base_carry",):
                continue
            down_rows.append({"strategy": name, "market": mkt, **R.downside_beta(weekly(r), weekly(fac[mkt]))})
        liq_s = liq["A"] if name.startswith("A") else liq["B"]
        for lab, cond, q in (("VIX tercile", vix_prev, 3), ("dollar month", dollar_month, None),
                             ("large Brent week", brent_big, None), ("geo shock day", shock_day, None),
                             ("half-spread tercile", liq_s, 3)):
            if cond.notna().sum() < 30:          # no bid/ask in the data (free-data run)
                continue
            c = R.conditional_performance(r, cond, q=q)
            cond_rows.append(c.assign(strategy=name, conditioner=lab))
        ep_rows.append(R.episode_returns(r).assign(strategy=name))
        dd_rows.append(R.drawdown_table(r, 10, tags).assign(strategy=name))
    pd.concat(beta_rows).to_csv(out / "betas_weekly.csv", index=False)
    pd.DataFrame(down_rows).to_csv(out / "downside_beta.csv", index=False)
    pd.concat(cond_rows).to_csv(out / "conditional_performance.csv", index=False)
    pd.concat(ep_rows).to_csv(out / "episodes.csv", index=False)
    pd.concat(dd_rows).to_csv(out / "worst_drawdowns.csv", index=False)

    # Concentration of P&L (by currency and by month) for the main variants.
    conc = []
    for sub, name in (("strategy_a", "A1_theory_with_dollar"), ("strategy_a", "A1_theory_dollar_neutral"),
                      ("strategy_b", "pm_timed"), ("strategy_b", "base_carry")):
        f = res_dir / sub / f"pnl_by_asset_{name}.parquet"
        if f.exists():
            pnl = pd.read_parquet(f)
            c = R.concentration(pnl)
            conc.append(c.assign(strategy=name, dimension="currency", hhi=c.attrs["hhi"]).reset_index(names="key"))
            m = pnl.sum(axis=1).resample("ME").sum().to_frame("pnl").T
            c = R.concentration(m)
            conc.append(c.assign(strategy=name, dimension="month", hhi=c.attrs["hhi"]).reset_index(names="key"))
    if conc:
        pd.concat(conc).to_csv(out / "concentration.csv", index=False)

    # Strategy A versus Strategy B (spec 10.4: they must be meaningfully different).
    corr = []
    for a_name in [c for c in strategies if c.startswith("A")]:
        corr.append({"a": a_name, "b": "pm_timed", **R.correlation_report(strategies[a_name], strategies["pm_timed"])})
    pd.DataFrame(corr).to_csv(out / "a_vs_b_correlation.csv", index=False)
    log.info("risk analysis written to %s", out)
    return {"factors": fac}


if __name__ == "__main__":
    run()
