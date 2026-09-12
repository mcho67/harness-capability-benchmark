"""
trace_cell — run ONE cell against the frozen snapshot and record every
module the run actually imported.

This is the mechanical half of CHARTER.md §3. The inclusion rule ("a module
belongs in the apparatus only if it is reachable on the path from finalized
text input to final response") is not applied by reading imports, because
the runtime imports lazily in several places and a static list would be
silently incomplete. It is applied by running the thing and asking the
interpreter afterwards what it loaded.

One cell per process, for the same reason the study itself uses one process
per cell: config binds at import time, so the only clean way to flip the
architecture or the provider is a fresh interpreter.

Nothing here writes into frozen_v1/. Run rows and the module list go to
paths passed in from outside.

Usage (driven by trace_all.py, but runnable alone):
    python trace_cell.py <cell.env> <modules_out.json> <runs_out.jsonl>
"""

from __future__ import annotations

import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PAPER_ROOT = os.path.dirname(os.path.dirname(HERE))
FROZEN = os.path.join(PAPER_ROOT, "frozen_v1")


def main() -> int:
    cell_env, modules_out, runs_out = sys.argv[1], sys.argv[2], sys.argv[3]

    # The snapshot must resolve as if it were the working tree: its own
    # top-level packages (cognitive, skills, metrics, ...) are imported by
    # bare name.
    os.chdir(FROZEN)
    sys.path.insert(0, FROZEN)

    from research.run_cell import (
        load_env_file, boot_research_runtime, run_cell, _cell_meta_from_env,
    )
    from research.schema import load_tasks

    load_env_file(cell_env)
    # The trace needs coverage, not statistics: one pass over every task.
    os.environ.setdefault("RESEARCH_TURN_TIMEOUT_S", "180")

    meta = _cell_meta_from_env()
    tasks = load_tasks(os.path.join(FROZEN, "research", "tasks.json"))

    # Baseline: everything already loaded before JARVIS is touched. Anything
    # that appears after this point was pulled in by the run itself.
    before = set(sys.modules)

    print(f"[trace] cell={meta['cell']} arch={meta['architecture']} "
          f"deploy={meta['deployment']} model={meta['model']} "
          f"tasks={len(tasks)}", flush=True)

    t0 = time.time()
    error = ""
    rows = 0
    try:
        jarvis = boot_research_runtime()
        rows = run_cell(jarvis, tasks, meta, runs_out, reps=1, seed=0)
    except Exception as e:                     # a failed cell still traced
        error = f"{type(e).__name__}: {e}"
        print(f"[trace] ERROR {error}", file=sys.stderr, flush=True)
    elapsed = round(time.time() - t0, 1)

    # What did the run load, of the snapshot's own code? Third-party and
    # stdlib modules are dependencies, not apparatus, so they are filtered
    # out by path: only files living under frozen_v1/ and outside
    # site-packages count.
    frozen_real = os.path.realpath(FROZEN)
    imported = {}
    for name, mod in list(sys.modules.items()):
        f = getattr(mod, "__file__", None)
        if not f:
            continue
        p = os.path.realpath(f)
        if not p.startswith(frozen_real + os.sep):
            continue
        if "site-packages" in p:
            continue
        imported[name] = os.path.relpath(p, frozen_real).replace(os.sep, "/")

    payload = {
        "cell": meta["cell"],
        "architecture": meta["architecture"],
        "deployment": meta["deployment"],
        "model": meta["model"],
        "tasks": len(tasks),
        "rows_written": rows,
        "elapsed_s": elapsed,
        "error": error,
        "python": sys.version.split()[0],
        "traced_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "preloaded_before_boot": sorted(n for n in before if n in imported),
        "modules": dict(sorted(imported.items())),
    }
    os.makedirs(os.path.dirname(modules_out) or ".", exist_ok=True)
    with open(modules_out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)

    print(f"[trace] {meta['cell']}: {len(imported)} snapshot modules, "
          f"{rows} rows, {elapsed}s -> {modules_out}", flush=True)
    return 1 if error else 0


if __name__ == "__main__":
    raise SystemExit(main())
