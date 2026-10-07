"""Panel regression diagnostics on synthetic data with a known coefficient."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategies import diagnostics as D


def test_pooled_recovers_coefficient():
    rng = np.random.default_rng(0)
    idx = pd.bdate_range("2024-01-01", periods=400)
    pairs = ["EUR", "JPY", "GBP"]
    x = pd.DataFrame(rng.normal(size=(400, 3)), index=idx, columns=pairs)
    rx = 0.002 * x.shift(1) + rng.normal(0, 0.005, (400, 3))     # x(t) predicts rx(t+1)
    df = D.stack({"x": x}, rx, horizon=1)
    res = D.pooled(df, ["x"])
    tab = D.coef_table(res, 1, "test")
    assert abs(tab.loc[0, "coef"] - 0.002) < 0.0006
    assert tab.loc[0, "t"] > 3


def test_wald_equal_coefficients():
    rng = np.random.default_rng(1)
    idx = pd.bdate_range("2024-01-01", periods=400)
    pairs = ["EUR", "JPY", "GBP"]
    x = pd.DataFrame(rng.normal(size=(400, 3)), index=idx, columns=pairs)
    rx = 0.002 * x.shift(1) + rng.normal(0, 0.005, (400, 3))
    df = D.stack({"x": x}, rx, horizon=1)
    w = D.pair_specific_wald(df, "x")
    assert w["n_pairs"] == 3 and w["p"] > 0.01
