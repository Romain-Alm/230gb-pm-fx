"""Shared helpers: configuration, paths, DuckDB connection, logging."""
from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path

import duckdb
import yaml

ROOT = Path(__file__).resolve().parents[1]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s",
                    datefmt="%H:%M:%S")


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


@lru_cache(maxsize=1)
def load_config(path: str | None = None) -> dict:
    with open(path or ROOT / "config" / "config.yaml", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def kairos_root(cfg: dict | None = None) -> Path:
    cfg = cfg or load_config()
    return Path(os.environ.get("KAIROS_DATA_ROOT", cfg["paths"]["kairos_data_root"]))


def kpath(key: str, cfg: dict | None = None) -> Path:
    """Path inside the (read-only) Kairos data estate."""
    cfg = cfg or load_config()
    return kairos_root(cfg) / cfg["paths"][key]


def rpath(key: str, cfg: dict | None = None) -> Path:
    """Path inside this repository; created if missing."""
    cfg = cfg or load_config()
    p = ROOT / cfg["paths"][key]
    p.mkdir(parents=True, exist_ok=True)
    return p


def connect(threads: int | None = None) -> duckdb.DuckDBPyConnection:
    """DuckDB connection pinned to UTC (host default is America/Los_Angeles)."""
    con = duckdb.connect()
    con.execute("SET TimeZone='UTC'")
    if threads:
        con.execute(f"SET threads={int(threads)}")
    return con


def sql_path(p: Path | str) -> str:
    """Forward-slash path literal safe for DuckDB on Windows."""
    return str(p).replace("\\", "/").replace("'", "''")
