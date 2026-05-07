#!/usr/bin/env python3
"""
Render compatibility-matrix.md from JSON cell results.

    render_matrix_md.py <cell-results-dir>

Reads every *.json file in the directory; each is shaped like:

    {"python":"3.11","django":"4.2","rdkit":"2024.09",
     "lock":"pass","build":"pass","tag":"...","pushed":"..."}

Writes Markdown to stdout. The workflow pipes it into docs/compatibility-matrix.md.

Env (optional):
    RUN_URL  — link to the GitHub Actions run (header)
    GH_OWNER — owner used to construct ghcr package page links
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
from collections import defaultdict
from pathlib import Path


def load_cells(d):
    cells = []
    for p in sorted(d.glob("*.json")):
        try:
            cells.append(json.loads(p.read_text()))
        except Exception as e:
            print(f"warn: skipping {p}: {e}", file=sys.stderr)
    return cells


def cell_md(c, gh_owner):
    if c is None:
        return "—"
    lock = c.get("lock", "fail")
    build = c.get("build", "skip")
    tag = c.get("tag", "")
    pushed = c.get("pushed", "")

    if lock == "fail":
        return "❌ lock"
    if build == "fail":
        return "❌ build"
    if build == "pass":
        if pushed:
            url = (
                f"https://github.com/{gh_owner}/protwis_django_docker"
                "/pkgs/container/protwis_django_docker"
            )
            return f"[`{tag}`]({url}) ✅"
        return f"`{tag}` ✅ (local)"
    return "?"


def ver_key(v):
    return tuple(int(x) for x in v.split("."))


def main():
    if len(sys.argv) != 2:
        print("usage: render_matrix_md.py <cell-results-dir>", file=sys.stderr)
        sys.exit(2)
    cells = load_cells(Path(sys.argv[1]))

    out = []
    if not cells:
        out.append("# Compatibility Matrix\n")
        out.append("_(no cell results found)_\n")
        print("\n".join(out))
        return

    pythons = sorted({c["python"] for c in cells}, key=ver_key)
    djangos = sorted({c["django"] for c in cells}, key=ver_key)
    rdkits = sorted({c["rdkit"] for c in cells}, key=ver_key)

    gh_owner = os.environ.get("GH_OWNER", "iskoldt-x")
    run_url = os.environ.get("RUN_URL", "")
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    total = len(cells)
    green = sum(1 for c in cells if c.get("lock") == "pass" and c.get("build") == "pass")
    red_lock = sum(1 for c in cells if c.get("lock") == "fail")
    red_build = sum(
        1 for c in cells if c.get("lock") == "pass" and c.get("build") == "fail"
    )

    out.append("# Compatibility Matrix\n")
    header_line = f"_Last run: {now}_"
    if run_url:
        header_line += f" · [workflow run]({run_url})"
    out.append(header_line + "\n")
    out.append(
        f"**Summary:** {green} / {total} green · "
        f"{red_lock} red (lock) · {red_build} red (build).\n"
    )
    out.append(
        "Each green cell links to the ghcr package page; the tag in the cell "
        "is what you `docker pull`.\n"
    )
    out.append("---\n")

    by_py = defaultdict(list)
    for c in cells:
        by_py[c["python"]].append(c)

    for py in pythons:
        out.append(f"## Python {py}\n")
        idx = {(c["django"], c["rdkit"]): c for c in by_py[py]}
        out.append("| Django \\ RDKit | " + " | ".join(rdkits) + " |")
        out.append("|" + "|".join(["---"] * (len(rdkits) + 1)) + "|")
        for dj in djangos:
            row = [f"**{dj}**"]
            for rdk in rdkits:
                row.append(cell_md(idx.get((dj, rdk)), gh_owner))
            out.append("| " + " | ".join(row) + " |")
        out.append("")

    out.append("---\n")
    out.append("## Failure legend\n")
    out.append("- **❌ lock** — `uv lock` did not resolve.")
    out.append(
        "- **❌ build** — lock resolved but `docker build` failed "
        "(typically a missing system library or native-extension break)."
    )
    out.append("- **—** — no result (cell skipped or workflow interrupted).\n")

    out.append("## Reproduce a cell locally\n")
    out.append("```bash")
    out.append("# Example: py3.11 / dj4.2 / rdk2024.09")
    out.append("PY_MIN=3.11 PY_MAX=3.12 \\")
    out.append("DJANGO_MAJOR=4.2 DJANGO_NEXT=5.0 \\")
    out.append("RDKIT_MAJOR=2024.09 RDKIT_NEXT=2024.10 \\")
    out.append("envsubst < pyproject.matrix.toml.tmpl > pyproject.toml")
    out.append("uv lock                                                 # gate 1")
    out.append("docker build --build-arg PYTHON_VERSION=3.11 -t probe . # gate 2")
    out.append("```\n")

    print("\n".join(out))


if __name__ == "__main__":
    main()
