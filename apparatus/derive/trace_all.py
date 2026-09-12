"""
trace_all — drive the four cells and merge their traces into one import log.

The merged log (import_log.json) is the evidence CHARTER.md §3 requires:
the record of what the experiment actually touched, produced by running it
rather than by choosing. Its union is the keep-list; everything in the
snapshot that is absent from it comes out.

A module reached by only some cells is still apparatus — the arms differ, so
the deciding loop legitimately imports things the routing pass never does.
The log records per-cell reachability so that asymmetry is visible instead
of averaged away.

Usage:
    python trace_all.py                 # all four cells
    python trace_all.py --cells C2,C4   # local only (free; no API calls)
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PAPER_ROOT = os.path.dirname(os.path.dirname(HERE))
FROZEN = os.path.join(PAPER_ROOT, "frozen_v1")
CONFIGS = os.path.join(FROZEN, "research", "configs")
OUT = os.path.join(HERE, "trace_out")

CELLS = {
    "C1": "C1_brain_cloud.env",
    "C2": "C2_brain_local.env",
    "C3": "C3_pipeline_cloud.env",
    "C4": "C4_pipeline_local.env",
}


def main() -> int:
    wanted = list(CELLS)
    for i, a in enumerate(sys.argv):
        if a == "--cells" and i + 1 < len(sys.argv):
            wanted = [c.strip().upper() for c in sys.argv[i + 1].split(",")]

    os.makedirs(OUT, exist_ok=True)
    results = {}
    for cell in wanted:
        env_path = os.path.join(CONFIGS, CELLS[cell])
        mods = os.path.join(OUT, f"{cell}_modules.json")
        runs = os.path.join(OUT, f"{cell}_runs.jsonl")
        if os.path.exists(runs):
            os.remove(runs)
        print(f"\n=== {cell} ===", flush=True)
        subprocess.run(
            [sys.executable, os.path.join(HERE, "trace_cell.py"),
             env_path, mods, runs],
            cwd=FROZEN,
        )
    # Merge every cell trace present, not just the ones run this
    # invocation. The log is the union over the whole 2x2; tracing cells one
    # at a time (local first, cloud after) must not silently drop the rest.
    for cell in CELLS:
        mods = os.path.join(OUT, f"{cell}_modules.json")
        if os.path.exists(mods):
            with open(mods, encoding="utf-8") as fh:
                results[cell] = json.load(fh)

    if not results:
        print("no cells traced", file=sys.stderr)
        return 1

    incomplete = [c for c, p in results.items()
                  if p["error"] or p["rows_written"] < p["tasks"]]
    if incomplete:
        print(f"\nWARNING: incomplete cells {sorted(incomplete)} -- the union "
              f"is a floor, not the keep-list, until every cell completes.",
              file=sys.stderr)

    # Union across cells, with per-module attribution.
    union = {}
    for cell, payload in results.items():
        for name, relpath in payload["modules"].items():
            entry = union.setdefault(name, {"path": relpath, "cells": []})
            entry["cells"].append(cell)
    for entry in union.values():
        entry["cells"].sort()

    log = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "rule": ("CHARTER.md §3 — a module belongs in the apparatus only if "
                 "it is reachable on the path from finalized text input to "
                 "final response. Applied by running, not by reading."),
        "snapshot": "frozen_v1 @ 5cbd13e (tag paper-frozen-v1)",
        "python": sys.version.split()[0],
        "cells": {
            c: {k: p[k] for k in
                ("architecture", "deployment", "model", "tasks",
                 "rows_written", "elapsed_s", "error", "traced_at")}
            for c, p in sorted(results.items())
        },
        "complete": not incomplete,
        "incomplete_cells": sorted(incomplete),
        "module_count": len(union),
        "modules": dict(sorted(union.items())),
    }
    log_path = os.path.join(HERE, "import_log.json")
    with open(log_path, "w", encoding="utf-8") as fh:
        json.dump(log, fh, indent=2)

    # Top-level package rollup — the shape of the cut, at a glance.
    pkgs = {}
    for name, entry in union.items():
        top = entry["path"].split("/")[0]
        if top.endswith(".py"):
            top = "(root)"
        pkgs[top] = pkgs.get(top, 0) + 1

    print(f"\nunion: {len(union)} modules across {sorted(results)}")
    for pkg, n in sorted(pkgs.items(), key=lambda kv: -kv[1]):
        print(f"  {n:4d}  {pkg}")
    print(f"\n-> {log_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
