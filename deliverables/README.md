# MFE 230GB final project: prediction-market signals for global FX strategies

Romain Almeida, Piero Pelosi, Hino Wirachapong, Thomas Claudel.

## What is in this folder

| File | What it is |
|---|---|
| `index.html` | The interactive page (spec 11.2). One self-contained file: open it in a browser, no server or network needed. |
| the presentation | The slides presented on 8 October 2026. |
| `README.md` | This guide. |

The full replication package is the rest of the repository; its `README.md` (at the root) gives
the details. Every number and figure comes from `results/`; `results/RESULTS.md` lists them all.

## How to rerun everything

1. **Python environment** (Python 3.13):

   ```
   python -m venv .venv
   .venv/Scripts/python.exe -m pip install -r requirements.txt
   ```

   On Linux or macOS use `.venv/bin/python` in place of `.venv/Scripts/python.exe`.

2. **Market data (Bloomberg and WRDS, licensed).** Download the two files from the Google Drive
   folder shared with the instructor: DRIVE_LINK

   Put them at these paths in the repository:

   ```
   data/raw/market/priority1_market_data.csv
   data/raw/market_qc/priority1_qc_flags.csv
   ```

   Everything else (prediction-market panels, hourly FX, hand-coded inputs, code) is in the
   repository.

3. **Run** from the repository root:

   ```
   .venv/Scripts/python.exe run_all.py
   .venv/Scripts/python.exe -m pytest tests
   ```

   `run_all.py` rebuilds every processed file, table, figure, `results/RESULTS.md` and
   `deliverables/index.html` (about 50 minutes). To rebuild only the page:
   `run_all.py --stage site` (about one minute).

The raw prediction-market trades tape (about 75 GB) is not shared; the run starts from the four
panels built from it in `data/processed/`. The root `README.md` explains how to rebuild them from
the tape or from the venues' public APIs.
