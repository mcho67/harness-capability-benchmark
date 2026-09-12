"""
M4 — the pilot, and the go/no-go gate it exists to face.

One full pass, R=1, all 48 tasks, all four cells (protocol §8.6). Its job is
not to produce a result. It is to answer two questions before any expensive
run happens:

1. **Does every cell run every category?** A pipeline arm that silently
   cannot reach a task type would make the comparison meaningless
   (`docs/harness.md` §7).
2. **Does the local model show intermediate variance?** Protocol §10 calls
   this *the make-or-break risk*. If the local model fails nearly everything
   or passes nearly everything, there is no gradient for architecture to
   interact with and the study collapses to a trivial main effect. The band
   is 0.15–0.85, overall and per category, and it was written into
   `analyze.validity_gate` before this ever ran.

**The order is local first, deliberately.** C2 and C4 cost nothing, so any
harness bug is found before a cent of cloud inference is spent on it.

**Nothing here writes inside the instrument tree** (CHARTER §7). The output
directory is passed in and lands beside the repo, not under `apparatus/`.

Run it from the apparatus directory, as a module, so the package-relative
imports resolve:

    cd apparatus && python -m harness.pilot <absolute-out-dir>

**If the gate fails, the task set is recalibrated and the pilot is re-run.**
That is the pre-registered response and it is why the freeze happens *after*
the gate rather than before it (CHARTER §8). Recalibrating after seeing the
full run would be a different act entirely, and is forbidden.
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any, Dict, List, Optional

from .analyze import analyze, print_report
from .judge import Judge
from .run_cell import CELLS, CellSpec, run_cell
from .score import score_log

CLOUD_MODEL = "claude-sonnet-4-6"
LOCAL_MODEL = "llama3.1:8b"

# Local cells first: they are free, so a harness bug costs nothing to find.
CELL_ORDER = ("C2", "C4", "C1", "C3")


def model_for(cell: str) -> str:
    return LOCAL_MODEL if CELLS[cell][1] == "ollama" else CLOUD_MODEL


def run_pilot(out_dir: str, *, repo_root: str, apparatus_dir: str,
              repetitions: int = 1, cells: tuple = CELL_ORDER,
              resamples: int = 5000) -> Dict[str, Any]:
    os.makedirs(out_dir, exist_ok=True)
    runs_path = os.path.join(out_dir, "runs.jsonl")
    scored_path = os.path.join(out_dir, "scored.jsonl")
    report_path = os.path.join(out_dir, "report.json")
    tasks_path = os.path.join(apparatus_dir, "tasks", "tasks.json")
    scratch = os.path.join(out_dir, "scratch")

    started = time.time()
    counts: Dict[str, int] = {}
    for cell in cells:
        print(f"\n{'=' * 62}\n{cell}  {CELLS[cell][0]}  {model_for(cell)}\n{'=' * 62}",
              flush=True)
        spec = CellSpec(cell=cell, model=model_for(cell), out_path=runs_path,
                        scratch_dir=scratch, tasks_path=tasks_path,
                        repetitions=repetitions)
        counts[cell] = run_cell(spec, repo_root=repo_root)

    print(f"\n{'=' * 62}\nscoring\n{'=' * 62}", flush=True)
    judge = Judge(cache_path=os.path.join(out_dir, "judge_cache.json"))
    score_log(runs_path, tasks_path, scored_path, judge=judge)

    report = analyze(scored_path, out_path=report_path, resamples=resamples)
    report["rows_per_cell"] = counts
    report["wall_minutes"] = round((time.time() - started) / 60, 1)
    report["judge_cost_usd"] = round(judge.cost_usd, 4)
    with open(report_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)

    print_report(report)
    _gate_verdict(report)
    return report


def _gate_verdict(report: Dict[str, Any]) -> None:
    """State the gate's answer plainly, including what it does not license."""
    gate = report["validity_gate"]
    print(f"\n{'=' * 62}")
    print("VALIDITY GATE (protocol §8.6)")
    print(f"  criterion met: {'YES' if gate['criterion_met'] else 'NO'}")
    print(f"  proceed:       {'YES' if gate['proceed'] else 'NO'}")
    if not gate["local_overall_in_band"]:
        print(f"\n  local overall {gate['local_overall']:.3f} is outside "
              f"{gate['band']}")
    for cat in gate["categories_out_of_band"]:
        v = gate["per_category"][cat]
        documented = cat in gate["exceptions_invoked"]
        print(f"\n  {cat}: {v['rate']:.3f} (n={v['n']}) — "
              f"{'documented exception' if documented else 'UNDOCUMENTED'}")
        if documented:
            print(f"    {gate['exceptions_invoked'][cat]}")
    if gate["undocumented_failures"]:
        print("\n  Pre-registered response to an undocumented failure: "
              "recalibrate the task set,\n  then re-run the pilot. The full "
              "run does not proceed.")
    elif gate["criterion_met"]:
        print("\n  The local model shows intermediate variance overall and in "
              "every non-exempt category.")
    print(f"\n  This is a pilot. R=1, so no cell mean here is a result, and "
          f"the\n  interaction contrast is reported only to confirm it "
          f"computes.\n{'=' * 62}")


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])
    apparatus_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    repo_root = os.path.dirname(apparatus_dir)
    out_dir = argv[0] if argv else os.path.join(
        repo_root, "runs", f"pilot-{time.strftime('%Y-%m-%d')}")
    run_pilot(out_dir, repo_root=repo_root, apparatus_dir=apparatus_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["run_pilot", "main", "CELL_ORDER", "CLOUD_MODEL", "LOCAL_MODEL"]
