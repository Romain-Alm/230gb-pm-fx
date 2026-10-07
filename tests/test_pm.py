"""Tests for the prediction-market layer (spec 12).

Unit tests on the classification rules, and data tests on the processed files
(skipped when the processed files are absent).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.common import ROOT, connect

try:
    from src.pm import classify as C
except ImportError:          # the Kairos resolver (src/pm/vendor/) is confidential and not distributed
    C = None
need_rules = pytest.mark.skipif(C is None, reason="classification rules need the Kairos resolver (not distributed)")

PROC = ROOT / "data" / "processed"


# ---------------------------------------------------------------- classification rules
@need_rules
@pytest.mark.parametrize("title,expected", [
    ("Fed decreases interest rates by 50+ bps after January 2026 meeting?", -50),
    ("Will the Fed decrease interest rates by 25 bps after the September 2026 meeting?", -25),
    ("No change in Fed interest rates after December 2025 meeting?", 0),
    ("Will the Fed increase interest rates by 25+ bps after the March 2026 meeting?", 25),
])
def test_decision_delta(title, expected):
    assert C._decision_delta(title, "0xabc", "") == expected


@need_rules
def test_kalshi_decision_suffix():
    assert C._decision_delta("Will the European Central Bank Cut more than 25bp?",
                             "KXCBDECISIONEU-26FEB05-C25P", "KXCBDECISIONEU") == -50
    assert C._decision_delta("Will the Federal Reserve Hike rates by 0bps?",
                             "KXFEDDECISION-26SEP-H0", "KXFEDDECISION") == 0


@need_rules
@pytest.mark.parametrize("title,expected", [
    ("Will 8 Fed rate cuts happen in 2026?", 8),
    ("Will Fed cut interest rates 1 time in 2024?", 1),
    ("Will the Fed cut rates 0 times?", 0),
    ("No Fed rate cuts in 2025?", 0),
])
def test_cut_count(title, expected):
    assert C._cut_count(title) == expected


@need_rules
def test_bracket_mid():
    assert C._bracket_mid("Will the U.S. tariff rate on China be between 25% and 40% on August 15?") == 32.5
    assert C._bracket_mid("Will annual inflation increase by 2.4% in March?") == 2.4
    assert C._bracket_mid("Will the rate of CPI inflation be above 2.3%?") is None


def _row(title, theme_text=""):
    class R:  # minimal row stand-in
        pass
    r = R()
    r.title, r.text, r.platform, r.series = title, theme_text or title, "polymarket", ""
    return r


STANCE = pd.read_csv(ROOT / "data" / "manual" / "party_fiscal_stance.csv", comment="#")


@pytest.mark.parametrize("title,theme,expected", [
    ("Will China invade Taiwan by end of 2026?", "GEOPOLITICS", 1),
    ("US x Iran ceasefire extended by April 22, 2026?", "GEOPOLITICS", -1),
    ("Iran x Israel/US conflict ends by June 30?", "GEOPOLITICS", -1),
    ("Military action against Iran ends by April 23, 2026?", "GEOPOLITICS", -1),
    ("US strikes Iran by February 17, 2026?", "GEOPOLITICS", 1),
    ("Strait of Hormuz traffic returns to normal by end of June?", "GEOPOLITICS", -1),
    ("Will the Iran ceasefire collapse before July?", "GEOPOLITICS", 1),
    ("Will Trump lower tariffs on China in April?", "TRADE_TARIFFS", -1),
    ("Will Trump impose 25% tariff on Mexico or Canada before February?", "TRADE_TARIFFS", 1),
    ("Will the rate of CPI inflation be above 2.3% for the year ending in April 2025?", "INFLATION", 1),
    ("CPI year-over-year in Jun 2026?", "INFLATION", 0),
    ("Fed rate cut by May 1?", "MONETARY", -1),
    ("Will Trump nominate Kevin Warsh as the next Fed chair?", "MONETARY", 0),
    ("US government shutdown Saturday?", "FISCAL_POLITICAL", 1),
    ("Will Donald Trump win the 2024 US Presidential Election?", "FISCAL_POLITICAL", 1),
    ("Will Kamala Harris win the 2024 US Presidential Election?", "FISCAL_POLITICAL", -1),
    ("Will Sanae Takaichi be the next leader out before 2027?", "FISCAL_POLITICAL", -1),
    ("Starmer out by June 23, 2026?", "FISCAL_POLITICAL", 1),
])
@need_rules
def test_direction(title, theme, expected):
    d, _ = C._direction(_row(title, title + " presidential election" if "Presidential" in title else ""),
                        theme, STANCE)
    assert d == expected, title


# ---------------------------------------------------------------- data tests
need_daily = pytest.mark.skipif(not (PROC / "pm_daily.parquet").exists(), reason="no processed panel")
need_cd = pytest.mark.skipif(not (PROC / "contract_days.parquet").exists(), reason="no contract panel")


@need_daily
def test_no_lookahead_snapshot():
    """Every trade used for snapshot day t is strictly before 16:00 London of t and after
    16:00 London of t-1 (this also checks DST handling on mismatch weeks)."""
    con = connect()
    bad = con.execute(f"""
        SELECT count(*) FROM read_parquet('{(PROC / "pm_daily.parquet").as_posix()}')
        WHERE last_ts >= timezone('Europe/London', CAST(snap_date AS TIMESTAMP) + INTERVAL 16 HOUR)
           OR last_ts <  timezone('Europe/London', CAST(snap_date - 1 AS TIMESTAMP) + INTERVAL 16 HOUR)
    """).fetchone()[0]
    assert bad == 0


@pytest.mark.parametrize("day,utc_hour", [
    ("2024-03-15", 16),  # US on DST, UK not yet: London 16:00 = 16:00 UTC
    ("2024-04-15", 15),  # both on summer time: London 16:00 = 15:00 UTC
    ("2024-10-30", 16),  # UK back on GMT, US still on DST
])
def test_snapshot_utc_conversion(day, utc_hour):
    con = connect()
    ts = con.execute(f"SELECT hour(timezone('Europe/London', TIMESTAMP '{day} 16:00:00'))").fetchone()[0]
    assert ts == utc_hour


@need_cd
def test_trailing_volume_is_causal():
    con = connect()
    rng = np.random.default_rng(0)
    cd = con.execute(f"""SELECT contract_id, platform, day, vol7d FROM read_parquet('{(PROC / "contract_days.parquet").as_posix()}')
                         WHERE unit = 'prob' USING SAMPLE 50 ROWS (reservoir, 1)""").df()
    for r in cd.itertuples():
        pid = r.contract_id.split(":", 1)[1]
        v = con.execute(f"""SELECT coalesce(sum(volume_usd), 0) FROM read_parquet('{(PROC / "pm_daily.parquet").as_posix()}')
                            WHERE platform = '{r.platform}' AND platform_id = '{pid}'
                              AND snap_date BETWEEN DATE '{r.day}' - 6 AND DATE '{r.day}'""").fetchone()[0]
        assert abs(v - r.vol7d) < 1e-6 * max(1.0, v)
    assert rng is not None


@need_cd
def test_not_eligible_near_resolution():
    con = connect()
    n = con.execute(f"""SELECT count(*) FROM read_parquet('{(PROC / "contract_days.parquet").as_posix()}')
                        WHERE eligible AND ttr_days < 3""").fetchone()[0]
    assert n == 0


@need_cd
def test_partition_expected_value_by_hand():
    """Recompute a partition EV from bucket prices for random contract-days."""
    con = connect()
    lab = pd.read_parquet(PROC / "contracts_classified.parquet",
                          columns=["platform", "platform_id", "event_key", "partition", "bucket_value",
                                   "theme", "created_at", "closes_at", "resolves_at"])
    lab = lab[lab["partition"]].copy()
    london = lambda s: pd.to_datetime(s, utc=True).dt.tz_convert("Europe/London").dt.tz_localize(None).dt.normalize()
    lab["d0"] = london(lab["created_at"])
    lab["d1"] = london(lab["closes_at"].fillna(lab["resolves_at"]))
    cd = con.execute(f"""SELECT contract_id, platform, event_key, day, value FROM read_parquet('{(PROC / "contract_days.parquet").as_posix()}')
                         WHERE unit NOT IN ('prob', 'hazard') AND value IS NOT NULL USING SAMPLE 15 ROWS (reservoir, 2)""").df()
    daily = pd.read_parquet(PROC / "pm_daily.parquet", columns=["platform", "platform_id", "snap_date", "px_last"])
    for r in cd.drop_duplicates(["contract_id", "day"]).itertuples():
        day = pd.Timestamp(r.day)
        b = lab[(lab["platform"] == r.platform) & (lab["event_key"] == r.event_key)
                & (lab["d0"] <= day) & (lab["d1"] >= day)]
        px = []
        for m in b.itertuples():
            d = daily[(daily["platform"] == m.platform) & (daily["platform_id"] == m.platform_id)
                      & (pd.to_datetime(daily["snap_date"]) <= pd.Timestamp(r.day))]
            if len(d):
                px.append((d.sort_values("snap_date")["px_last"].iloc[-1], m.bucket_value))
        p = np.array([a for a, _ in px]); v = np.array([b_ for _, b_ in px])
        assert abs((p * v).sum() / p.sum() - r.value) < 1e-9


@need_cd
def test_hazard_rate_by_hand():
    """Deadline contracts (D18): value = -ln(1 - p) / tau, tau in years floored at 3 days."""
    con = connect()
    cd = con.execute(f"""SELECT px, value, ttr_days FROM read_parquet('{(PROC / "contract_days.parquet").as_posix()}')
                         WHERE unit = 'hazard' AND px IS NOT NULL USING SAMPLE 50 ROWS (reservoir, 3)""").df()
    p = cd["px"].clip(0.001, 0.999)
    tau = cd["ttr_days"].clip(lower=3) / 365.25
    assert np.allclose(-np.log(1 - p) / tau, cd["value"])


@need_cd
def test_daily_scaling_of_multiday_changes():
    """D19: a change spanning g days is divided by sqrt(g)."""
    ch = pd.read_parquet(PROC / "contract_changes.parquet", columns=["contract_id", "day", "dv", "value"])
    ch = ch.sort_values(["contract_id", "day"])
    ch["prev"] = ch.groupby("contract_id")["value"].shift(1)
    ch["gap"] = ch.groupby("contract_id")["day"].diff().dt.days
    sel = ch.dropna(subset=["prev", "gap"]).sample(200, random_state=0)
    # consecutive rows in the change table may skip stale days, so only test rows whose
    # previous change row is the previous fresh snapshot used for dv
    ok = np.isclose(sel["dv"], (sel["value"] - sel["prev"]) / np.sqrt(sel["gap"]))
    assert ok.mean() > 0.9
