"""Free market data (preliminary, until the Bloomberg export arrives).

Sources (public, no account):
  - Dukascopy hourly candles (bid and ask) for G10 and deliverable EM currencies, used for
    the 16:00 London snapshot and for the weekend gap test (Friday 17:00 New York close,
    Monday 07:00 London reopening). Candles are stamped at their END time, so the value at
    time T is the close of the last candle ending at or before T.
  - FRED: VIX, Brent, US 10-year yield, broad dollar index, S&P 500, OECD 3-month interbank
    rates (monthly) used to approximate 1-month forward carry by covered interest parity,
    and noon New York spot rates for some non-deliverable EM currencies.
Outputs: data/raw/intraday/dukascopy_hourly.parquet, data/raw/free/fred.parquet.
Results built on these data are labelled preliminary (DECISIONS D17).
"""
from __future__ import annotations

import io
import lzma
import time
import subprocess


import numpy as np
import pandas as pd

from src.common import ROOT, get_logger

log = get_logger("download_free")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/129.0 Safari/537.36", "Referer": "https://freeserv.dukascopy.com/"}
# Dukascopy symbol -> (currency code, inverted quote?, reference level for the price scale)
DUKA = {
    "EURUSD": ("EUR", False, 1.1), "GBPUSD": ("GBP", False, 1.3), "AUDUSD": ("AUD", False, 0.67),
    "NZDUSD": ("NZD", False, 0.6), "USDJPY": ("JPY", True, 145), "USDCHF": ("CHF", True, 0.85),
    "USDCAD": ("CAD", True, 1.37), "USDNOK": ("NOK", True, 10.5), "USDSEK": ("SEK", True, 10.0),
    "USDMXN": ("MXN", True, 18.5), "USDZAR": ("ZAR", True, 18.0), "USDTRY": ("TRY", True, 35.0),
    "USDPLN": ("PLN", True, 3.9), "USDHUF": ("HUF", True, 360), "USDCZK": ("CZK", True, 22.5),
    "USDCNH": ("CNH", True, 7.2), "USDTHB": ("THB", True, 34.0), "USDSGD": ("SGD", True, 1.33),
}
DTYPE = np.dtype([("t", ">i4"), ("o", ">i4"), ("c", ">i4"), ("l", ">i4"), ("h", ">i4"), ("v", ">f4")])

FRED = {
    "VIXCLS": "vix", "DCOILBRENTEU": "brent", "DGS10": "y10_US", "DTWEXBGS": "dollar_broad",
    "SP500": "spx", "DFF": "fed_funds",
    # OECD 3-month interbank rates, % p.a., monthly
    **{f"IR3TIB01{c}M156N": f"r3m_{c}" for c in
       ("US", "EZ", "JP", "GB", "CH", "AU", "NZ", "CA", "NO", "SE", "MX", "ZA", "TR", "PL", "HU",
        "CZ", "KR", "IN", "BR", "CL", "CO", "ID", "CN", "TH")},
    # OECD immediate (call money) rates, % p.a., monthly: EM carry
    **{f"IRSTCI01{c}M156N": f"rcall_{c}" for c in
       ("BR", "IN", "ID", "ZA", "MX", "KR", "TR", "PL", "HU", "CZ", "CL")},
    # noon New York spot (H.10): G10 (USD per unit for EUR, GBP, AUD, NZD; units per USD otherwise)
    "DEXUSEU": "h10_EUR", "DEXJPUS": "h10_JPY", "DEXUSUK": "h10_GBP", "DEXSZUS": "h10_CHF",
    "DEXUSAL": "h10_AUD", "DEXUSNZ": "h10_NZD", "DEXCAUS": "h10_CAD", "DEXNOUS": "h10_NOK",
    "DEXSDUS": "h10_SEK",
    # noon New York spot (H.10), units of currency per USD
    "DEXBZUS": "spot_BRL", "DEXKOUS": "spot_KRW", "DEXINUS": "spot_INR", "DEXTAUS": "spot_TWD",
    "DEXMAUS": "spot_MYR", "DEXTHUS": "spot_THB", "DEXMXUS": "spot_MXN", "DEXSFUS": "spot_ZAR",
}


def _get(url: str, retries: int = 6, browser: bool = False) -> bytes | None:
    """HTTP GET through curl (Python's TLS client times out on some of these hosts).
    browser=True sends browser headers (needed by Dukascopy, rejected by FRED's CSV export)."""
    hdr = ["-A", UA["User-Agent"], "-H", f"Referer: {UA['Referer']}"] if browser else []
    for k in range(retries):
        p = subprocess.run(["curl", "-s", "--max-time", "60", *hdr, "-w", "\n%{http_code}", url],
                           capture_output=True)
        body, _, code = p.stdout.rpartition(b"\n")
        code = code.decode().strip()
        if code == "200":
            return body
        if code == "404":
            return None
        time.sleep(2 * (k + 1) + (10 if code in ("429", "503") else 0))
    return None


G10_SYMBOLS = ("EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDJPY", "USDCHF", "USDCAD", "USDNOK", "USDSEK")


def dukascopy_hourly(start: str = "2023-12", end: str = "2026-09", pause: float = 1.0,
                     symbols=G10_SYMBOLS, sides=("BID",), offline: bool = False,
                     out_name: str = "dukascopy_hourly.parquet") -> pd.DataFrame:
    """Hourly candles. Dukascopy throttles heavily (about 20 s per file), so by default only
    G10 bid candles are fetched (weekend gap test); mid = bid when asks are not fetched.
    Progress is cached per month in data/raw/intraday/duka_cache/ so the job can resume."""
    out_path = ROOT / "data" / "raw" / "intraday" / out_name
    cache = ROOT / "data" / "raw" / "intraday" / "duka_cache"
    cache.mkdir(parents=True, exist_ok=True)
    months = pd.period_range(start, end, freq="M")
    frames = []
    for sym in symbols:
        ccy, inv, ref = DUKA[sym]
        scale, n = None, 0
        for m in months:
            got = {}
            for side in sides:
                fc = cache / f"{sym}_{m}_{side}.bi5"
                if fc.exists():
                    raw = fc.read_bytes()
                elif offline:
                    raw = None
                else:
                    url = f"https://datafeed.dukascopy.com/datafeed/{sym}/{m.year}/{m.month - 1:02d}/{side}_candles_hour_1.bi5"
                    raw = _get(url, browser=True)
                    time.sleep(pause)
                    if raw:
                        fc.write_bytes(raw)
                if not raw:
                    continue
                a = np.frombuffer(lzma.decompress(raw), dtype=DTYPE)
                if scale is None:
                    med = float(np.median(a["c"]))
                    scale = 10 ** round(np.log10(med / ref))
                ts = pd.Timestamp(m.start_time, tz="UTC") + pd.to_timedelta(a["t"].astype("int64") + 3600, unit="s")
                got[side] = pd.Series(a["c"] / scale, index=ts)
                got[side + "_vol"] = pd.Series(a["v"].astype(float), index=ts)
            if "BID" in got:
                ask = got.get("ASK", got["BID"])
                d = pd.DataFrame({"bid": got["BID"], "ask": ask, "volume": got["BID_vol"]})
                d = d[d["volume"] > 0]                       # drop flat candles (market closed)
                if inv:                                      # store USD price of one unit of ccy
                    d = pd.DataFrame({"bid": 1 / d["ask"], "ask": 1 / d["bid"], "volume": d["volume"]})
                d["mid"] = (d["bid"] + d["ask"]) / 2
                d["ccy"] = ccy
                frames.append(d.rename_axis("timestamp").reset_index())
                n += len(d)
        log.info("%s: %d hourly candles (scale %s)", sym, n, scale)
    df = pd.concat(frames, ignore_index=True)
    df.to_parquet(out_path, index=False)
    log.info("saved %s (%d rows)", out_path, len(df))
    return df


def _fred_key() -> str | None:
    """FRED API key from the local, git-ignored config/secrets.local.yaml (optional)."""
    import yaml
    p = ROOT / "config" / "secrets.local.yaml"
    return yaml.safe_load(p.read_text(encoding="utf-8")).get("fred_api_key") if p.exists() else None


def _fred_series(sid: str) -> pd.DataFrame | None:
    """FRED API first when a key is configured, public CSV export otherwise."""
    key = _fred_key()
    if key:
        import json
        raw = _get(f"https://api.stlouisfed.org/fred/series/observations?series_id={sid}"
                   f"&api_key={key}&file_type=json", retries=3)
        obs = json.loads(raw).get("observations", []) if raw else []
        if obs:
            s = pd.DataFrame(obs)[["date", "value"]]
            s["value"] = pd.to_numeric(s["value"], errors="coerce")
            return s
    raw = _get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}", retries=2)
    if raw and raw[:4] != b"<!DO":
        s = pd.read_csv(io.BytesIO(raw), na_values=["."])
        s.columns = ["date", "value"]
        return s
    return None


def fred(pause: float = 0.5) -> pd.DataFrame:
    out_path = ROOT / "data" / "raw" / "free" / "fred.parquet"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    series = {}
    for sid, name in FRED.items():
        s = _fred_series(sid)
        time.sleep(pause)
        if s is None:
            log.warning("FRED %s not available", sid)
            continue
        s["date"] = pd.to_datetime(s["date"])
        series[name] = s.set_index("date")["value"].astype(float)
        log.info("FRED %s -> %s: %d obs, last %s", sid, name, s["value"].notna().sum(), s["date"].max().date())
    df = pd.DataFrame(series).loc["2009-06-01":]
    df.to_parquet(out_path)
    return df


def ecb_reference_rates() -> pd.DataFrame:
    """ECB euro foreign exchange reference rates (about 14:15 CET), units per EUR."""
    import zipfile
    out_path = ROOT / "data" / "raw" / "free" / "ecb_eurofxref_hist.csv"
    raw = _get("https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.zip", retries=3)
    z = zipfile.ZipFile(io.BytesIO(raw))
    df = pd.read_csv(z.open(z.namelist()[0]))
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    df.to_csv(out_path, index=False)
    log.info("ECB reference rates: %s, last %s", df.shape, df["Date"].max())
    return df


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2 or sys.argv[1] in ("fred", "all"):
        fred()
    if len(sys.argv) < 2 or sys.argv[1] in ("ecb", "all"):
        ecb_reference_rates()
    if len(sys.argv) < 2 or sys.argv[1] in ("duka", "all"):
        dukascopy_hourly()
