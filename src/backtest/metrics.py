"""Performance measures (spec 10.1) on daily strategy returns."""
from __future__ import annotations

import numpy as np
import pandas as pd

PPY = 252


def drawdown(r: pd.Series) -> pd.Series:
    """Drawdown of the cumulative (compounded) return path, as a fraction of the peak."""
    w = (1 + r.fillna(0)).cumprod()
    return w / w.cummax() - 1


def drawdown_episodes(r: pd.Series, n: int = 10) -> pd.DataFrame:
    """The n deepest peak-to-trough episodes with peak, trough and recovery dates."""
    dd = drawdown(r)
    # Each group starts at a new high (dd == 0) and runs until the next new high.
    groups = list(dd.groupby((dd == 0).cumsum()))
    eps = []
    for k, (_, seg) in enumerate(groups):
        if seg.min() < 0:
            recovery = groups[k + 1][1].index[0] if k + 1 < len(groups) else pd.NaT
            eps.append((seg.index[0], seg.idxmin(), recovery, seg.min()))
    out = pd.DataFrame(eps, columns=["peak", "trough", "recovery", "depth"])
    if out.empty:
        return out
    out["days_to_trough"] = (out["trough"] - out["peak"]).dt.days
    out["duration_days"] = (out["recovery"].fillna(r.index[-1]) - out["peak"]).dt.days
    return out.sort_values("depth").head(n).reset_index(drop=True)


def sharpe_block_bootstrap(r: pd.Series, block: int = 20, n_draws: int = 1000, seed: int = 230,
                           level: float = 0.90) -> tuple[float, float]:
    """Moving-block bootstrap confidence interval of the annualised Sharpe ratio."""
    x = r.dropna().to_numpy()
    T = len(x)
    if T < 2 * block:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    nb = int(np.ceil(T / block))
    starts = rng.integers(0, T - block + 1, size=(n_draws, nb))
    idx = (starts[:, :, None] + np.arange(block)).reshape(n_draws, -1)[:, :T]
    s = x[idx]
    sh = s.mean(axis=1) / s.std(axis=1, ddof=1) * np.sqrt(PPY)
    a = (1 - level) / 2
    return float(np.nanquantile(sh, a)), float(np.nanquantile(sh, 1 - a))


def perf_stats(r: pd.Series, turnover: pd.Series | None = None, gross: pd.Series | None = None,
               costs: pd.Series | None = None, bootstrap: bool = False) -> dict:
    """Standard statistics on daily returns.

    turnover: daily one-way traded notional per unit of capital (sum |dw|);
    gross: daily gross exposure (sum |w|); costs: daily cost in return units.
    """
    r = r.dropna()
    if len(r) < 2:
        return {"n_days": len(r)}
    mu, sd = r.mean() * PPY, r.std(ddof=1) * np.sqrt(PPY)
    down = r[r < 0]
    dsd = np.sqrt((down ** 2).sum() / len(r)) * np.sqrt(PPY)
    dd = drawdown(r)
    eps = drawdown_episodes(r, 1)
    out = {
        "n_days": len(r),
        "cum_return": float((1 + r).prod() - 1),
        "ann_mean": float(mu),
        "ann_vol": float(sd),
        "sharpe": float(mu / sd) if sd > 0 else np.nan,
        "sortino": float(mu / dsd) if dsd > 0 else np.nan,
        "max_drawdown": float(dd.min()),
        "max_dd_duration_days": int(eps["duration_days"].iloc[0]) if len(eps) else 0,
        "calmar": float(mu / -dd.min()) if dd.min() < 0 else np.nan,
        "hit_rate": float((r > 0).mean()),
        "skew": float(r.skew()),
        "excess_kurtosis": float(r.kurt()),
        # approximate t-statistic of the Sharpe ratio: annualised Sharpe x sqrt(years)
        "sharpe_t": float(mu / sd * np.sqrt(len(r) / PPY)) if sd > 0 else np.nan,
    }
    if bootstrap:
        out["sharpe_ci90_low"], out["sharpe_ci90_high"] = sharpe_block_bootstrap(r)
    if turnover is not None:
        to = turnover.reindex(r.index).fillna(0)
        out["turnover_ann"] = float(to.mean() * PPY)
        if gross is not None:
            g = gross.reindex(r.index).fillna(0)
            # Average holding period (days) = average gross exposure / average daily turnover.
            out["avg_holding_days"] = float(g.mean() / to.mean()) if to.mean() > 0 else np.nan
            out["avg_gross"] = float(g.mean())
    if costs is not None:
        out["cost_drag_ann"] = float(costs.reindex(r.index).fillna(0).mean() * PPY)
    return out


def stats_table(series: dict[str, pd.Series], **kw) -> pd.DataFrame:
    return pd.DataFrame({k: perf_stats(v, **kw) for k, v in series.items()}).T
