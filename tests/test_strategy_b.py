"""Strategy B timing-rule tests on synthetic inputs."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategies import strategy_b as B

IDX = pd.bdate_range("2025-01-01", "2025-04-30")


def test_shock_cut_and_linear_rerisk():
    p = B.TimingParams(shock_cut=0.25, rerisk_days=4)
    esc_z = pd.Series(0.0, index=IDX)
    shocks = pd.Series(False, index=pd.date_range(IDX[0], IDX[-1], freq="D"))
    shocks[pd.Timestamp("2025-02-04")] = True
    w = B.timing_exposure(esc_z, shocks, IDX, p)["w"]
    i = IDX.get_loc(pd.Timestamp("2025-02-04"))
    assert w.iloc[i - 1] == 1.0
    assert w.iloc[i] == 0.25
    assert np.allclose(w.iloc[i + 1:i + 5].values, [0.4375, 0.625, 0.8125, 1.0])


def test_weekend_shock_hits_monday():
    p = B.TimingParams()
    shocks = pd.Series(False, index=pd.date_range(IDX[0], IDX[-1], freq="D"))
    shocks[pd.Timestamp("2025-03-08")] = True          # Saturday
    w = B.timing_exposure(pd.Series(0.0, index=IDX), shocks, IDX, p)
    assert w.loc[pd.Timestamp("2025-03-10"), "shock"]  # Monday
    assert w.loc[pd.Timestamp("2025-03-10"), "w"] == p.shock_cut


def test_escalation_component_monthly():
    p = B.TimingParams()
    z = pd.Series(0.0, index=IDX)
    z.loc["2025-02-15":] = 1.5
    wl = B.escalation_component(z, IDX, p)
    assert wl.loc["2025-02-27"] == 1.0          # before the February month-end
    assert wl.loc["2025-02-28"] == 0.5          # set at month-end with z = 1.5
    assert wl.loc["2025-03-31"] == 0.5


def test_base_carry_long_high_short_low():
    idx = pd.bdate_range("2024-01-01", "2024-06-30")
    rng = np.random.default_rng(1)
    cols = list("ABCDEFG")
    rets = pd.DataFrame(rng.normal(0, 0.005, (len(idx), len(cols))), index=idx, columns=cols)
    carry = pd.DataFrame(np.tile(np.arange(len(cols), dtype=float), (len(idx), 1)), index=idx, columns=cols)
    w = B.base_carry_weights(carry, rets, 3, 3)
    last = w.iloc[-1]
    assert (last[["E", "F", "G"]] > 0).all() and (last[["A", "B", "C"]] < 0).all()
    assert last["D"] == 0
    assert np.isclose(last[last > 0].sum(), -last[last < 0].sum(), rtol=0.5)


def test_tercile_leg_size():
    assert [B.leg_size(n) for n in (2, 4, 6, 9, 17)] == [1, 1, 2, 3, 5]


def test_single_currency_cap_water_filling():
    w, infeasible = B._cap_leg(pd.Series([0.7, 0.2, 0.1, 0.0001]), 0.4)
    assert not infeasible and abs(w.sum() - 1) < 1e-9 and (w <= 0.4 + 1e-9).all()
    w2, infeasible2 = B._cap_leg(pd.Series([0.9, 0.1]), 0.4)
    assert infeasible2 and np.allclose(w2, 0.5)


def test_tercile_weights_two_by_two():
    idx = pd.bdate_range("2024-01-01", "2024-06-30")
    rng = np.random.default_rng(2)
    cols = list("ABCDEF")
    rets = pd.DataFrame(rng.normal(0, 0.005, (len(idx), 6)), index=idx, columns=cols)
    carry = pd.DataFrame(np.tile(np.arange(6, dtype=float), (len(idx), 1)), index=idx, columns=cols)
    last = B.base_carry_weights(carry, rets, leg_rule="tercile").iloc[-1]
    assert (last[["E", "F"]] > 0).all() and (last[["A", "B"]] < 0).all() and (last[["C", "D"]] == 0).all()
