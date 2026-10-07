"""Strategy A signal-construction tests on synthetic inputs."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategies import strategy_a as A

DAYS = pd.date_range("2024-01-01", "2024-12-31", freq="D")


def _cell(values, active=None):
    active = np.ones(len(values), bool) if active is None else active
    return pd.DataFrame({"day": DAYS[:len(values)], "d_vw": values, "n_contracts": active.astype(int)})


def test_cell_signal_is_causal():
    rng = np.random.default_rng(0)
    v = rng.normal(size=len(DAYS))
    z1 = A.cell_signal(_cell(v), 5)
    v2 = v.copy()
    v2[200:] += 100.0          # change the future only
    z2 = A.cell_signal(_cell(v2), 5)
    assert np.allclose(z1.iloc[:200], z2.iloc[:200])


def test_cell_signal_needs_history():
    z = A.cell_signal(_cell(np.ones(30)), 5)
    assert (z.iloc[:A.MIN_ACTIVE] == 0).all()


def test_us_hawkish_shorts_every_pair():
    td = pd.bdate_range("2024-03-01", "2024-03-29")
    sig = {("US", "MONETARY"): pd.Series(1.0, index=DAYS)}
    y = A.pair_forecasts(sig, td, {("US", "MONETARY")})
    assert (y < 0).all().all()


def test_fiscal_sign_flips_with_regime():
    td = pd.bdate_range("2024-03-01", "2024-03-29")
    sig = {("US", "FISCAL_POLITICAL"): pd.Series(1.0, index=DAYS)}
    md = A.pair_forecasts(sig, td, {("US", "FISCAL_POLITICAL")},
                          regime=pd.DataFrame({"US": 0.0}, index=td))
    fd = A.pair_forecasts(sig, td, {("US", "FISCAL_POLITICAL")},
                          regime=pd.DataFrame({"US": 1.0}, index=td))
    assert (md < 0).all().all() and (fd > 0).all().all()   # MD: USD up; FD: USD down


def test_geo_spillover_long_safe_havens():
    td = pd.bdate_range("2024-03-01", "2024-03-29")
    sig = {("GLOBAL", "GEOPOLITICS"): pd.Series(1.0, index=DAYS)}
    y = A.pair_forecasts(sig, td, {("GLOBAL", "GEOPOLITICS")})
    assert (y[["JPY", "CHF"]] > 0).all().all()
    assert (y.drop(columns=["JPY", "CHF"]) == 0).all().all()


def test_fiscal_regime_negative_correlation():
    idx = pd.bdate_range("2024-01-01", periods=200)
    rng = np.random.default_rng(3)
    dy = rng.normal(size=200)
    y = pd.DataFrame({"US": np.cumsum(dy)}, index=idx)
    fx = pd.DataFrame({"US": np.cumsum(-dy + 0.1 * rng.normal(size=200))}, index=idx)
    r = A.fiscal_regime(y, fx, 60)
    assert r["US"].iloc[70:].eq(1.0).all()


def test_pure_dollar_signal_has_no_dollar_neutral_position():
    rng = np.random.default_rng(5)
    idx = pd.bdate_range("2024-01-01", periods=200)
    rets = pd.DataFrame(rng.normal(0, 0.005, (200, 9)), index=idx, columns=list(A.PAIRS))
    y = pd.DataFrame(np.tile(rng.normal(size=(200, 1)), (1, 9)) * 0.37, index=idx, columns=list(A.PAIRS))
    cfg = {"strategy_a": {"cov_ewma_span_days": 60, "vol_target_annual": 0.1, "gross_leverage_cap": 3.0,
                          "single_pair_cap_share": 0.3, "no_trade_band": 0.1}}
    w = A.positions(y, rets, cfg, dollar_neutral=True)
    assert (w.abs().to_numpy() < 1e-12).all()
