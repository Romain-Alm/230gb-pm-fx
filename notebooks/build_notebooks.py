"""Build and execute the two summary notebooks.

    .venv/Scripts/python.exe notebooks/build_notebooks.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from nb01_cells import CELLS as C1  # noqa: E402
from nb02_cells import CELLS as C2  # noqa: E402

NOTEBOOKS = {"01_prediction_market_layer.ipynb": C1, "02_strategies_tests_results.ipynb": C2}


def make(cells) -> nbformat.NotebookNode:
    nb = nbformat.v4.new_notebook()
    nb.cells = [nbformat.v4.new_markdown_cell(src) if kind == "md" else nbformat.v4.new_code_cell(src)
                for kind, src in cells]
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    return nb


def main():
    for name, cells in NOTEBOOKS.items():
        nb = make(cells)
        NotebookClient(nb, timeout=900, kernel_name="python3", resources={"metadata": {"path": str(HERE)}}).execute()
        nbformat.write(nb, HERE / name)
        print("written", HERE / name)


if __name__ == "__main__":
    main()
