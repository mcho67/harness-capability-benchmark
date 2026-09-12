"""
One cell of the 2x2, over the whole task set, R times.

A cell is a pair of switch settings — architecture x deployment — and nothing
else. Everything a cell does not set is held constant by living in `core/`
or in the shared half of `arms/`. `CellSpec` is therefore very short, and
that is the point: if a cell could configure anything else, "controlled
variable" would be a claim rather than a structural fact.

**What this file is responsible for, in order:**

1. **Preflight, before any task runs.** CHARTER §7: missing capability aborts
   the run. The provider is asked to prove it can answer with the pinned
   model before a single row is written, because rows that look complete
   while a capability was absent are worse than no rows.
2. **A warm-up pass** (protocol §5) whose row is discarded, so cold-start
   latency is excluded from the measured runs rather than averaged into them.
3. **Task order shuffled per repetition from a logged seed** (protocol §8.3),
   so order and learning effects are controlled and the exact order is
   reproducible. The seed and each task's position are on every row.
4. **A fresh world and a fresh conversation per task.** CHARTER §7 puts the
   isolation boundary at the task, not the turn: the pilot found a fact
   learned in one task appearing in an unrelated later one, and because order
   is shuffled, that contamination is order-dependent and makes runs
   non-independent — which the per-task random intercept in protocol §9 does
   not model and cannot repair.
5. **Telling a broken cell from a hard task.** A different model answering,
   or a provider that cannot be reached, invalidates every row the cell has
   written, so the cell aborts. A timeout or error on one task after its
   retries is a *result*: recorded as a failed run with a degradation note,
   and the cell continues (`docs/harness.md` §7).

**What this file must never do:** score anything. It writes what happened.
`score.py` reads it, and does so cell-blind.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import shutil
import tempfile
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from arms import build_arm
from core.llm import build_provider
from core.llm.types import LLMConfig, LLMError, ModelMismatch
from core.sandbox import new_world

from .capture import RunLog, RunRow, baseline_commit

# The four cells, named once. The labels are the paper's (`docs/protocol.md`
# §3) and are the only place architecture and deployment are paired, so a
# typo cannot invent a fifth cell.
CELLS = {
    "C1": ("deciding", "anthropic"),
    "C2": ("deciding", "ollama"),
    "C3": ("routing",  "anthropic"),
    "C4": ("routing",  "ollama"),
}

# One warm-up turn, discarded. Deliberately not a task from the set: warming
# on a scored task would give that task a rehearsal no other task gets.
WARMUP_TURN = "say ready"


@dataclass
class CellSpec:
    """Everything one cell may set. Two switches, plus where to write."""
    cell: str
    model: str
    out_path: str
    scratch_dir: str
    repetitions: int = 1
    order_seed: int = 20260819
    tasks_path: str = ""
    # Pilot conveniences, both unused by the real run: `limit` takes the
    # first N tasks, `only` takes named ids. Neither is a way to drop an
    # inconvenient task — CHARTER §7 forbids post-hoc task edits, and a
    # subset run is labelled as a subset by the rows it fails to produce.
    limit: int = 0                 # 0 = the whole set
    only: tuple = ()

    @property
    def architecture(self) -> str:
        return CELLS[self.cell][0]

    @property
    def provider(self) -> str:
        return CELLS[self.cell][1]

    @property
    def deployment(self) -> str:
        return "local" if self.provider == "ollama" else "cloud"

    def llm_config(self) -> LLMConfig:
        return LLMConfig(provider=self.provider, model=self.model)


def load_tasks(path: str) -> tuple:
    """The task set and its hash. The hash goes on every row.

    CHARTER §8 freezes the task set by file hash rather than by "whatever the
    code happened to do", so the row must carry the hash of the bytes it was
    actually run against.
    """
    with open(path, "rb") as fh:
        blob = fh.read()
    return json.loads(blob.decode("utf-8")), hashlib.sha256(blob).hexdigest()


def _order_for(tasks: List[Dict[str, Any]], repetition: int,
               seed: int) -> List[Dict[str, Any]]:
    """Task order for one repetition: shuffled, reproducible, logged.

    Seeded on `seed + repetition` so each repetition gets a different order
    and the whole schedule is recoverable from the seed on the row. The same
    order is used in all four cells for a given repetition, which is what
    makes order a *controlled* variable rather than a randomised one.
    """
    order = list(tasks)
    random.Random(seed + repetition).shuffle(order)
    return order


def run_cell(spec: CellSpec, *, repo_root: str, verbose: bool = True) -> int:
    """Run one cell. Returns the number of rows written."""
    tasks, tasks_sha = load_tasks(spec.tasks_path)
    if spec.only:
        tasks = [t for t in tasks if t["id"] in set(spec.only)]
    if spec.limit:
        tasks = tasks[:spec.limit]
    commit = baseline_commit(repo_root)

    provider = build_provider(spec.llm_config())
    # Before anything. A cell that cannot answer must not produce rows.
    provider.preflight()

    scratch = os.path.join(spec.scratch_dir, f"{spec.cell}-{int(time.time())}")
    os.makedirs(scratch, exist_ok=True)

    written = 0
    try:
        with RunLog(spec.out_path) as log:
            already = log.done()
            if already and verbose:
                print(f"  resuming: {len(already)} rows already on disk")

            # Warm-up (protocol §5). Its cost is real and is spent; its
            # latency is what we are excluding, so no row is written.
            _warm_up(spec, provider, scratch)

            for rep in range(1, spec.repetitions + 1):
                order = _order_for(tasks, rep, spec.order_seed)
                for position, task in enumerate(order):
                    key = (spec.cell, task["id"], rep)
                    if key in already:
                        continue
                    row = _run_one(spec, provider, task, rep, position,
                                   scratch, commit, tasks_sha)
                    log.write(row)
                    written += 1
                    if verbose:
                        _report(row)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    if verbose:
        print(f"\n{spec.cell}: {written} rows -> {spec.out_path}")
        print(f"  cloud spend this cell: ${provider.total_cost_usd:.4f}")
    return written


def _warm_up(spec: CellSpec, provider: Any, scratch: str) -> None:
    world = new_world("warmup", scratch)
    try:
        build_arm(spec.architecture, provider, world).take_turn(WARMUP_TURN)
    except ModelMismatch:
        raise
    except LLMError:
        # A warm-up that fails is not itself a result, but it is a signal.
        # It is not fatal: preflight already proved the cell can answer.
        pass
    finally:
        world.close()


def _run_one(spec: CellSpec, provider: Any, task: Dict[str, Any],
             repetition: int, position: int, scratch: str,
             commit: str, tasks_sha: str) -> RunRow:
    row = RunRow(
        run_id=f"{spec.cell}-{task['id']}-r{repetition}",
        cell=spec.cell,
        architecture=spec.architecture,
        deployment=spec.deployment,
        provider=spec.provider,
        model_pinned=spec.model,
        repetition=repetition,
        order_index=position,
        order_seed=spec.order_seed,
        task_id=task["id"],
        category=task.get("category", ""),
        difficulty=int(task.get("difficulty", 0)),
        started_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        baseline_commit=commit,
        tasks_sha256=tasks_sha,
    )

    started = time.perf_counter()
    world = new_world(task["id"], scratch, fixtures=task.get("fixtures"))
    try:
        arm = build_arm(spec.architecture, provider, world)
        results = arm.run_task(task["turns"])

        for i, result in enumerate(results):
            row.turns.append({
                "index": i,
                "user": task["turns"][i],
                "reply": result.text,
                "decision": result.trace.as_row(),
                "latency_s": result.latency_s,
                "cost_usd": result.cost_usd,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
            })
            row.latency_s += result.latency_s
            row.cost_usd += result.cost_usd
            row.input_tokens += result.input_tokens
            row.output_tokens += result.output_tokens
            row.model_calls += result.trace.model_calls
            row.models_reported.extend(result.trace.models_reported)
            if result.trace.hit_iteration_cap:
                row.note_degradation(
                    "iteration_cap", f"turn {i} exhausted the loop bound",
                    turn=i)
            if result.trace.unknown_tools:
                row.note_degradation(
                    "unknown_tool", "the model named a tool that does not exist",
                    turn=i, names=result.trace.unknown_tools)

        last = results[-1]
        row.reply = last.text
        row.decision = last.trace.as_row()

    except ModelMismatch as exc:
        # Study-fatal. Every row this cell has written was produced under an
        # assumption that has just been shown false, so the cell stops here
        # rather than adding another.
        world.close()
        raise
    except LLMError as exc:
        # This task degraded. A result, not a crash: recorded as a failed run
        # so the local model's failure modes are in the data rather than
        # missing from it (`docs/harness.md` §7).
        row.error = f"{type(exc).__name__}: {exc}"
        row.note_degradation("llm_error", str(exc))
    except Exception as exc:                     # pragma: no cover
        row.error = f"{type(exc).__name__}: {exc}"
        row.note_degradation("harness_error", str(exc))

    row.latency_s = round(row.latency_s, 4)
    row.cost_usd = round(row.cost_usd, 8)
    row.models_reported = sorted(set(row.models_reported))
    row.effects = world.log()
    row.final_state = world.state()
    row.mutations = [f"{e.kind}:{e.target}" for e in world.mutations()]
    row.wall_s = round(time.perf_counter() - started, 4)
    world.close()

    # The check that the whole seam exists for. `_check_model` already
    # enforces it per call; this is the row-level restatement, so a row can
    # be audited without trusting the code that wrote it.
    if row.models_reported and row.model_pinned not in " ".join(row.models_reported):
        row.note_degradation(
            "model_identity", "no reported model matched the pinned name",
            pinned=row.model_pinned, reported=row.models_reported)

    return row


def _report(row: RunRow) -> None:
    flag = ""
    if row.error:
        flag = "  ERROR"
    elif row.degradation:
        flag = "  " + ",".join(d["kind"] for d in row.degradation)
    d = row.decision
    print(f"  {row.task_id:10s} r{row.repetition} "
          f"{row.wall_s:6.2f}s ${row.cost_usd:.5f} "
          f"tools={d.get('tools', [])} ask={d.get('ask_origin', '-')}{flag}")


__all__ = ["CELLS", "CellSpec", "run_cell", "load_tasks"]
