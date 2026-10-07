"""Strategy A diagnostics (spec 6.4): pooled panel regressions of FX excess returns on
prediction-market theme signals.

  predictive:     rx(p, t+h) = a_p + sum_k b_k x_k(p, t) + e      (h = 1, 5, 20 days)
  contemporaneous: rx(p, t)   = a_p + sum_k c_k dx_k(p, t) + e    (information content)

x_k(p, t) is the signed theory component of theme k for pair p (foreign leg minus US leg,
spillovers included), so the theory predicts b_k > 0 for every k. Pair fixed effects;
Driscoll-Kraay standard errors (robust to cross-pair correlation and serial correlation,
which also covers overlapping multi-day returns). Significance threshold |t| > 3
(spec 6.4, Harvey-Liu-Zhu).

Fiscal heterogeneity (spec 6.4 as amended): b_fiscal = b0 + b1 debt_diff + b2 regime, so
the regression includes x_fiscal, x_fiscal x debt_diff and x_fiscal x regime with
predictions b0 > 0 and b2 < 0. Here x_fiscal is the UNSIGNED fiscal component (the regime
sign is estimated, not imposed).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from linearmodels.panel import PanelOLS


def stack(components: dict[str, pd.DataFrame], rx: pd.DataFrame, horizon: int = 1,
          contemporaneous: bool = False) -> pd.DataFrame:
    """Long panel (pair, date) with the target and one column per component."""
    if contemporaneous:
        y = rx
        xs = {k: v.diff() for k, v in components.items()}
    else:
        # sum of the next `horizon` daily excess returns, aligned on the signal date t
        y = rx.rolling(horizon).sum().shift(-horizon)
        xs = components
    frames = []
    for p in rx.columns:
        d = pd.DataFrame({"y": y[p]})
        for k, v in xs.items():
            d[k] = v[p].reindex(d.index) if p in v else 0.0
        d["pair"] = p
        frames.append(d)
    df = pd.concat(frames).dropna()
    df.index.name = "date"
    return df.reset_index().set_index(["pair", "date"])


def _drop_collinear(x: pd.DataFrame) -> pd.DataFrame:
    """Drop columns that are linear combinations of earlier ones (e.g. a debt interaction
    when only one zone has a fiscal signal, so the debt differential is constant)."""
    keep = []
    for c in x.columns:
        trial = x[keep + [c]].to_numpy()
        if np.linalg.matrix_rank(trial - trial.mean(axis=0)) == len(keep) + 1:
            keep.append(c)
    return x[keep]


def pooled(df: pd.DataFrame, regressors: list[str], bandwidth: int | None = None):
    x = df[regressors]
    x = _drop_collinear(x.loc[:, x.std() > 0])
    mod = PanelOLS(df["y"], x, entity_effects=True)
    kw = {"kernel": "bartlett"}
    if bandwidth:
        kw["bandwidth"] = bandwidth
    return mod.fit(cov_type="kernel", **kw)


def coef_table(res, horizon: int, label: str) -> pd.DataFrame:
    t = pd.DataFrame({"coef": res.params, "se": res.std_errors, "t": res.tstats, "p": res.pvalues})
    t["horizon"] = horizon
    t["model"] = label
    t["n_obs"] = res.nobs
    t["passes_gate"] = (t["t"] > 3)          # predicted sign is positive for every signed component
    return t.reset_index(names="regressor")


def pair_specific_wald(df: pd.DataFrame, regressor: str) -> dict:
    """Wald test that the coefficient on `regressor` is equal across pairs."""
    d = df.copy()
    pairs = d.index.get_level_values("pair").unique()
    cols = []
    for p in pairs:
        c = f"{regressor}__{p}"
        d[c] = d[regressor] * (d.index.get_level_values("pair") == p)
        cols.append(c)
    d = d.loc[:, ["y"] + cols]
    d = d.loc[:, (d.std() > 0) | (d.columns == "y")]
    cols = [c for c in cols if c in d.columns]
    if len(cols) < 2:
        return {"regressor": regressor, "n_pairs": len(cols), "wald": np.nan, "p": np.nan}
    res = PanelOLS(d["y"], d[cols], entity_effects=True).fit(cov_type="kernel", kernel="bartlett")
    k = len(cols)
    R = np.zeros((k - 1, k))
    for i in range(k - 1):
        R[i, i], R[i, i + 1] = 1.0, -1.0
    b, V = res.params.values, res.cov.values
    diff = R @ b
    stat = float(diff @ np.linalg.pinv(R @ V @ R.T) @ diff)
    from scipy import stats
    return {"regressor": regressor, "n_pairs": k, "wald": stat, "p": float(stats.chi2.sf(stat, k - 1))}
