"""Hand-labelled validation of the rule-based classification (spec 4.2).

`make_sheet` draws a seeded random sample of events, stratified by predicted theme
(including OTHER, to measure missed macro contracts), among events with at least
USD 10k of traded volume. For each sampled event one market is drawn at random; the
labeller sees the event and that market only (blind sheet) and fills
`theme`, `zone` and `direction` for the market. Predictions are stored separately in
the key file. `score` merges the two and reports accuracy per field.

Outputs: ai_log/classification/validation_sheet.csv (to fill; also split into
         validation_sheet_1.csv to _4.csv, 50 rows each, merged by `score`),
         ai_log/classification/validation_key.csv (predictions, do not open before labelling),
         ai_log/classification/validation_scores.csv (after labelling)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.common import ROOT, connect, get_logger, load_config, rpath, sql_path

log = get_logger("validation")
OUT = ROOT / "ai_log" / "classification"
PER_STRATUM = {"MONETARY": 30, "INFLATION": 25, "FISCAL_POLITICAL": 40, "TRADE_TARIFFS": 25,
               "GEOPOLITICS": 40, "OTHER": 40}
INSTRUCTIONS = (
    "Fill the three label_* columns for the market shown (blind: do not open validation_key.csv). "
    "label_theme: MONETARY, INFLATION, FISCAL_POLITICAL, TRADE_TARIFFS, GEOPOLITICS or OTHER "
    "(OTHER = no clear macro channel). label_zone: main zone(s) separated by '|' among US, EA, JP, UK, "
    "CH, AU, NZ, CA, NO, SE, CN, an EM ISO code, or GLOBAL (geopolitics always includes GLOBAL). "
    "label_direction: +1 if a higher Yes price means a higher theme index (more hawkish, higher "
    "inflation, more fiscal expansion or risk, more trade restriction, more escalation), -1 if "
    "lower, 0 if ambiguous; write B if the market is one bucket of a mutually exclusive set "
    "(e.g. one Fed decision outcome or one CPI range)."
)


def make_sheet(cfg: dict | None = None, seed: int | None = None) -> pd.DataFrame:
    cfg = cfg or load_config()
    seed = cfg["seed"] if seed is None else seed
    proc = rpath("processed", cfg)
    OUT.mkdir(parents=True, exist_ok=True)
    con = connect()
    lab = con.execute(f"""
        WITH v AS (SELECT platform, platform_id, sum(volume_usd) AS vol
                   FROM read_parquet('{sql_path(proc / "pm_daily.parquet")}') GROUP BY 1, 2)
        SELECT c.*, v.vol, sum(v.vol) OVER (PARTITION BY c.platform, c.event_key) AS event_vol
        FROM read_parquet('{sql_path(proc / "contracts_classified.parquet")}') c
        JOIN v USING (platform, platform_id)
    """).df()
    lab = lab[lab["event_vol"] >= 10_000]
    rng = np.random.default_rng(seed)
    rows = []
    for theme, n in PER_STRATUM.items():
        events = lab.loc[lab["theme"] == theme, ["platform", "event_key"]].drop_duplicates()
        take = events.iloc[rng.permutation(len(events))[:n]]
        for ev in take.itertuples(index=False):
            mk = lab[(lab["platform"] == ev.platform) & (lab["event_key"] == ev.event_key)]
            rows.append(mk.iloc[rng.integers(len(mk))])
    sample = pd.DataFrame(rows).sample(frac=1.0, random_state=seed).reset_index(drop=True)
    sample.insert(0, "item", np.arange(1, len(sample) + 1))
    sheet = sample[["item", "platform", "event_key", "platform_id", "title"]].copy()
    sheet["label_theme"] = ""
    sheet["label_zone"] = ""
    sheet["label_direction"] = ""
    sheet["notes"] = ""
    key = sample[["item", "platform", "platform_id", "theme", "zones", "direction", "partition",
                  "theme_rule", "direction_rule", "event_vol"]].copy()
    key["zones"] = key["zones"].apply(lambda z: "|".join(z) if z is not None else "")
    sheet_path, key_path = OUT / "validation_sheet.csv", OUT / "validation_key.csv"
    if sheet_path.exists() and pd.read_csv(sheet_path)["label_theme"].notna().any():
        raise FileExistsError(f"{sheet_path} already has labels; refusing to overwrite")
    sheet.to_csv(sheet_path, index=False, encoding="utf-8-sig")
    key.to_csv(key_path, index=False, encoding="utf-8-sig")
    (OUT / "VALIDATION_INSTRUCTIONS.txt").write_text(INSTRUCTIONS + "\n", encoding="utf-8")
    log.info("validation sheet with %d items written to %s", len(sheet), sheet_path)
    return sheet


def load_labels() -> pd.DataFrame:
    """Labelled sheet: the four 50-row files validation_sheet_1.csv to _4.csv merged when they
    exist (one per labeller), otherwise the single validation_sheet.csv."""
    parts = sorted(OUT.glob("validation_sheet_[0-9].csv"))
    files = parts if parts else [OUT / "validation_sheet.csv"]
    sheet = pd.concat([pd.read_csv(f, dtype=str, encoding="utf-8-sig").fillna("") for f in files], ignore_index=True)
    if sheet["item"].duplicated().any():
        raise ValueError("the same item appears in several validation sheets")
    sheet.to_csv(OUT / "validation_sheet_merged.csv", index=False, encoding="utf-8-sig")
    log.info("labels read from %s (%d rows)", ", ".join(f.name for f in files), len(sheet))
    return sheet


def score() -> pd.DataFrame:
    sheet = load_labels()
    key = pd.read_csv(OUT / "validation_key.csv", dtype=str).fillna("")
    m = sheet.merge(key, on=["item", "platform", "platform_id"])
    m = m[m["label_theme"] != ""]
    pred_dir = np.where(m["partition"].str.lower() == "true", "B", m["direction"].str.replace(r"\.0$", "", regex=True))
    m["ok_theme"] = m["label_theme"].str.upper().str.strip() == m["theme"]
    macro = m["label_theme"].str.upper() != "OTHER"
    m["ok_zone"] = [set(a.upper().split("|")) == set(b.split("|")) if mac else np.nan
                    for a, b, mac in zip(m["label_zone"], m["zones"], macro)]
    m["ok_direction"] = [str(a).strip().replace("+", "") == str(b) if mac else np.nan
                         for a, b, mac in zip(m["label_direction"], pred_dir, macro)]
    res = pd.DataFrame({
        "n_labelled": [len(m)],
        "theme_accuracy": [m["ok_theme"].mean()],
        "zone_accuracy_macro": [m.loc[macro, "ok_zone"].astype(float).mean()],
        "direction_accuracy_macro": [m.loc[macro, "ok_direction"].astype(float).mean()],
    })
    by_theme = m.groupby("label_theme")[["ok_theme"]].mean()
    res.to_csv(OUT / "validation_scores.csv", index=False)
    by_theme.to_csv(OUT / "validation_scores_by_theme.csv")
    m.to_csv(OUT / "validation_merged.csv", index=False)
    log.info("validation:\n%s\n%s", res.to_string(index=False), by_theme.to_string())
    return res


if __name__ == "__main__":
    import sys
    score() if len(sys.argv) > 1 and sys.argv[1] == "score" else make_sheet()
