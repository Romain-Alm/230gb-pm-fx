"""Risk analysis (spec 10.3, 10.4)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

from src.backtest.metrics import PPY, drawdown, drawdown_episodes

# Named stress episodes (illustration and exposure measurement; dates are the episode
# windows, not inputs to any trading rule).
EPISODES = {
    "Yen carry unwind (Aug 2024)": ("2024-07-31", "2024-08-09"),
    "Liberation Day tariffs (Apr 2025)": ("2025-04-02", "2025-04-11"),
    "Israel-Iran war (Jun 2025)": ("2025-06-12", "2025-06-24"),
    "Iran war (Feb-Apr 2026)": ("2026-02-26", "2026-04-10"),
}


def betas(r: pd.Series, factors: pd.DataFrame, nw_lags: int = 5) -> pd.DataFrame:
    """Univariate betas of daily strategy returns on each factor, Newey-West t-stats."""
    out = []
    for f in factors.columns:
        d = pd.concat([r.rename("r"), factors[f].rename("f")], axis=1).dropna()
        if len(d) < 30:
            continue
        res = sm.OLS(d["r"], sm.add_constant(d["f"])).fit(cov_type="HAC", cov_kwds={"maxlags": nw_lags})
        out.append({"factor": f, "beta": res.params["f"], "t": res.tvalues["f"], "n": len(d),
                    "corr": d["r"].corr(d["f"])})
    return pd.DataFrame(out)


def downside_beta(r: pd.Series, mkt: pd.Series, k: float = 1.0) -> dict:
    """Lettau, Maggiori, Weber (2014): beta conditional on market return below mean - k sd."""
    d = pd.concat([r.rename("r"), mkt.rename("m")], axis=1).dropna()
    beta = d["r"].cov(d["m"]) / d["m"].var()
    low = d[d["m"] < d["m"].mean() - k * d["m"].std()]
    dbeta = low["r"].cov(low["m"]) / low["m"].var() if len(low) > 10 else np.nan
    return {"beta": beta, "downside_beta": dbeta, "n_down": len(low),
            "mean_return_down_days_bp": low["r"].mean() * 1e4 if len(low) else np.nan}


def episode_returns(r: pd.Series, episodes: dict = EPISODES) -> pd.DataFrame:
    out = []
    for name, (a, b) in episodes.items():
        seg = r.loc[a:b].dropna()
        out.append({"episode": name, "start": a, "end": b, "n_days": len(seg),
                    "cum_return": float((1 + seg).prod() - 1) if len(seg) else np.nan,
                    "worst_day": float(seg.min()) if len(seg) else np.nan})
    return pd.DataFrame(out)


def conditional_performance(r: pd.Series, cond: pd.Series, labels: list[str] | None = None,
                            q: int | None = 3) -> pd.DataFrame:
    """Performance by bucket of a conditioning variable known at t (terciles by default),
    or by its categories if q is None."""
    d = pd.concat([r.rename("r"), cond.rename("c")], axis=1).dropna()
    if q:
        d["bucket"] = pd.qcut(d["c"], q, labels=labels or [f"q{i + 1}" for i in range(q)])
    else:
        d["bucket"] = d["c"]
    g = d.groupby("bucket", observed=True)["r"]
    return pd.DataFrame({"n_days": g.size(), "ann_mean": g.mean() * PPY,
                         "ann_vol": g.std() * np.sqrt(PPY),
                         "sharpe": g.mean() / g.std() * np.sqrt(PPY),
                         "hit_rate": g.apply(lambda s: (s > 0).mean())}).reset_index()


def concentration(contrib: pd.DataFrame) -> pd.DataFrame:
    """P&L share of each column (currency, theme, event or month) and Herfindahl index of
    absolute contributions."""
    tot = contrib.sum()
    share = tot / tot.abs().sum()
    hhi = float(((tot.abs() / tot.abs().sum()) ** 2).sum())
    out = pd.DataFrame({"pnl": tot, "share_of_abs": share})
    out.attrs["hhi"] = hhi
    return out.sort_values("pnl")


def drawdown_table(r: pd.Series, n: int = 10, tags: pd.Series | None = None) -> pd.DataFrame:
    """Worst drawdowns, optionally tagged (e.g. 'geopolitical' if a confirmed shock occurred
    between peak and trough)."""
    eps = drawdown_episodes(r, n)
    if tags is not None and len(eps):
        eps["tag"] = [", ".join(sorted(set(tags.loc[p:t].dropna().astype(str)))) or "other"
                      for p, t in zip(eps["peak"], eps["trough"])]
    return eps


def correlation_report(a: pd.Series, b: pd.Series) -> dict:
    d = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    dda, ddb = drawdown(d["a"]), drawdown(d["b"])
    return {"return_corr": d["a"].corr(d["b"]), "drawdown_corr": dda.corr(ddb),
            "weekly_return_corr": d.resample("W").sum().corr().iloc[0, 1], "n_days": len(d)}
