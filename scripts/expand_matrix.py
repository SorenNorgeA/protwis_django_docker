#!/usr/bin/env python3
"""Print the full compatibility-matrix as CSV rows on stdout.

Reads scripts/matrix_versions.py (the single source of truth for axis
values) and emits one CSV row per Cartesian-product cell. The workflow
pipes this into a `while read` loop that calls scripts/run_matrix_cell.sh
for each cell.

Output columns (no header — the cell driver expects positional args):

    py_min, py_max, django_major, django_next, rdkit_major, rdkit_next

Run locally to preview / count cells:

    python3 scripts/expand_matrix.py            # full list
    python3 scripts/expand_matrix.py | wc -l    # cell count

Stdlib only, Python 3.6+.
"""
from __future__ import annotations

import itertools
import sys
from pathlib import Path

# Import the sibling versions module without making scripts/ a package.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from matrix_versions import PYTHON, DJANGO, RDKIT  # noqa: E402


def main() -> None:
    for (py, py_next), (dj, dj_next), (rdk, rdk_next) in itertools.product(
        PYTHON, DJANGO, RDKIT
    ):
        print(f"{py},{py_next},{dj},{dj_next},{rdk},{rdk_next}")


if __name__ == "__main__":
    main()
