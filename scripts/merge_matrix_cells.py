#!/usr/bin/env python3
"""
Merge per-arch compatibility-matrix results and create manifest lists.

    merge_matrix_cells.py <amd64-dir> <arm64-dir> <out-dir>

Inputs are the cell-results directories from two arch jobs; each contains
one JSON per cell, shaped like:

    {"python":"3.11","django":"4.2","rdkit":"2024.09",
     "arch":"amd64","lock":"pass","build":"pass",
     "base_tag":"matrix-py311-dj42-rdk202409",
     "tag":"matrix-py311-dj42-rdk202409-amd64",
     "pushed":"ghcr.io/owner/repo:..."}

For each (python, django, rdkit) triple this script:
  - joins the two arch records,
  - creates a manifest list (`docker buildx imagetools create`) under the
    un-suffixed BASE_TAG when BOTH builds passed and were pushed,
  - writes one merged JSON to <out-dir>, shaped like:

    {"python":"3.11","django":"4.2","rdkit":"2024.09",
     "lock":"pass",
     "build_amd64":"pass","build_arm64":"pass",
     "base_tag":"matrix-py311-dj42-rdk202409",
     "tag":"matrix-py311-dj42-rdk202409",   # BASE_TAG if combined,
                                            # arch tag if half-pass
     "pushed":"ghcr.io/owner/repo:..."}     # empty if neither pushed

Half-pass cells (one arch built, the other failed) intentionally do NOT
get a manifest list — the user requested single-arch tags only in that
case so consumers don't get a `not found for your platform` error from
docker pull.
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path


def load_dir(d: Path) -> list[dict]:
    out = []
    for p in sorted(d.glob("*.json")):
        try:
            out.append(json.loads(p.read_text()))
        except Exception as e:
            print(f"warn: skipping {p}: {e}", file=sys.stderr)
    return out


def coerce_lock(amd: dict | None, arm: dict | None) -> str:
    # `uv lock` is platform-independent; if either side passed, we treat
    # the dep graph as resolvable. A divergence is itself a signal but
    # rare enough not to warrant a separate UI state.
    locks = {x["lock"] for x in (amd, arm) if x}
    if "pass" in locks:
        return "pass"
    return "fail"


def merge_one(amd: dict | None, arm: dict | None) -> dict:
    # At least one side is non-None (we only call this for cells that
    # appear in either dir).
    seed = amd or arm
    record = {
        "python":      seed["python"],
        "django":      seed["django"],
        "rdkit":       seed["rdkit"],
        "lock":        coerce_lock(amd, arm),
        "build_amd64": amd["build"] if amd else "missing",
        "build_arm64": arm["build"] if arm else "missing",
        "base_tag":    seed["base_tag"],
    }

    pushed_amd = (amd or {}).get("pushed", "")
    pushed_arm = (arm or {}).get("pushed", "")
    both_pushed = bool(pushed_amd and pushed_arm)

    if record["build_amd64"] == "pass" and record["build_arm64"] == "pass" and both_pushed:
        # Combine into a manifest list under the base tag.
        # Both per-arch tags share the same registry/repo, so derive the
        # manifest target by stripping the arch suffix from one of them.
        base_ref = pushed_amd.rsplit("-amd64", 1)[0]
        if create_manifest(base_ref, pushed_amd, pushed_arm):
            record["tag"] = record["base_tag"]
            record["pushed"] = base_ref
        else:
            # Manifest creation hiccup — fall back to advertising amd64,
            # since both per-arch images are still pushed and usable.
            record["tag"] = amd["tag"]
            record["pushed"] = pushed_amd
    elif record["build_amd64"] == "pass" and pushed_amd:
        record["tag"] = amd["tag"]
        record["pushed"] = pushed_amd
    elif record["build_arm64"] == "pass" and pushed_arm:
        record["tag"] = arm["tag"]
        record["pushed"] = pushed_arm
    else:
        # Nothing pushed (lock failed, both builds failed, or local run
        # without GH_OWNER). Surface the base tag for display only.
        record["tag"] = record["base_tag"]
        record["pushed"] = ""

    return record


def create_manifest(base_ref: str, amd_ref: str, arm_ref: str) -> bool:
    cmd = ["docker", "buildx", "imagetools", "create",
           "-t", base_ref, amd_ref, arm_ref]
    print(f"manifest: {' '.join(cmd)}", file=sys.stderr)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"manifest failed for {base_ref}:\n{r.stderr}", file=sys.stderr)
        return False
    return True


def main() -> int:
    if len(sys.argv) != 4:
        print("usage: merge_matrix_cells.py <amd64-dir> <arm64-dir> <out-dir>",
              file=sys.stderr)
        return 2

    amd_dir, arm_dir, out_dir = (Path(p) for p in sys.argv[1:4])
    out_dir.mkdir(parents=True, exist_ok=True)

    by_key: dict[tuple[str, str, str], dict[str, dict]] = defaultdict(dict)
    for rec in load_dir(amd_dir):
        by_key[(rec["python"], rec["django"], rec["rdkit"])]["amd64"] = rec
    for rec in load_dir(arm_dir):
        by_key[(rec["python"], rec["django"], rec["rdkit"])]["arm64"] = rec

    if not by_key:
        print("warn: no cell results found in either input dir", file=sys.stderr)
        return 0

    for key, sides in sorted(by_key.items()):
        merged = merge_one(sides.get("amd64"), sides.get("arm64"))
        out_path = out_dir / f"{merged['base_tag']}.json"
        out_path.write_text(json.dumps(merged, indent=2) + "\n")

    print(f"wrote {len(by_key)} merged cell results to {out_dir}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
