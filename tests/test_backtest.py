"""Backtest engine tests (spec 12): timing, costs, no-trade band, metrics."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.backtest import engine, metrics

IDX = pd.bdate_range("2024-01-01", periods=6)


def test_positions_earn_next_day_return():
    r = pd.DataFrame({"A": [0.0, 0.01, 0.02, -0.01, 0.0, 0.0]}, index=IDX)
    w = pd.DataFrame({"A": [1.0, 0.0, 0.0, 0.0, 0.0, 0.0]}, index=IDX)
    res = engine.run(w, r)
    # position decided on day 0 earns day 1's return only
    assert res.gross_ret.iloc[1] == 0.01
    assert res.gross_ret.drop(IDX[1]).abs().sum() == 0.0


def test_round_trip_cost():
    r = pd.DataFrame({"A": 0.0}, index=IDX)
    w = pd.DataFrame({"A": [0.0, 2.0, 2.0, 0.0, 0.0, 0.0]}, index=IDX)
    res = engine.run(w, r, half_spread=0.0002)
    # open 2 units then close 2 units at 2 bp half-spread: 2 * 2 * 0.0002
    assert np.isclose(res.costs.sum(), 2 * 2 * 0.0002)
    assert np.isclose(res.net_ret.sum(), -0.0008)


def test_no_trade_band():
    tgt = pd.DataFrame({"A": [1.0, 1.05, 1.2, 0.0]}, index=IDX[:4])
    held = engine.no_trade_band(tgt, 0.10)
    assert list(held["A"]) == [1.0, 1.0, 1.2, 0.0]


def test_vol_target_scales_to_target():
    rng = np.random.default_rng(0)
    idx = pd.bdate_range("2024-01-01", periods=300)
    r = pd.DataFrame(rng.normal(0, 0.01, (300, 2)), index=idx, columns=["A", "B"])
    raw = pd.DataFrame(1.0, index=idx, columns=["A", "B"])
    w = engine.vol_target(raw, r, 0.10, gross_cap=10, single_cap_share=None)
    realised = (w.shift(1) * r).sum(axis=1).iloc[100:].std() * np.sqrt(252)
    assert 0.07 < realised < 0.13


def test_metrics_drawdown():
    r = pd.Series([0.1, -0.5, 0.0, 1.0, 0.0], index=pd.bdate_range("2024-01-01", periods=5))
    s = metrics.perf_stats(r)
    assert np.isclose(s["max_drawdown"], -0.5)
    eps = metrics.drawdown_episodes(r)
    assert eps.loc[0, "trough"] == r.index[1]
    assert eps.loc[0, "recovery"] == r.index[3]
