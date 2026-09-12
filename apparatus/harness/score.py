"""
`runs.jsonl` -> `scored.jsonl`. Two measures, computed separately.

**PRIMARY — task success** (protocol §6a), as `pass` / `partial` / `fail`.
Deterministic where the task allows it, judged where it does not. §9 fixes
the coding before any data: `partial` collapses to fail for the primary
analysis, and the pass-or-partial coding is reported alongside as a
robustness check. Both codings are written on the row so neither can be
chosen after the fact.

**MECHANISM — decision accuracy** (protocol §6b), fully deterministic. The
recorded decision is compared against `ideal_decision`, which was derived
from properties of the *request* by a fixed ruleset with no architecture
argument (`tasks/derive_ideal.py`). Nobody grades this, and the mechanism
result is therefore immune to the "your rubric bakes in the advantage"
objection: the same ideal is applied to both arms, and it was written before
either arm existed.

The two are kept apart because their relationship is the finding. Decision
accuracy *explains* task success; it does not stand in for it.

**This module never sees a cell.** It reads rows to join them to tasks, and
it strips every cell-identifying field before anything reaches the judge
(`judge.BlindCase`). The scored row keeps the cell — the analysis needs it —
but nothing that produced a score ever saw it.
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tasks.derive_ideal import ANSWER_DIRECTLY

from .capture import read_rows
from .judge import BlindCase, Judge
from .rate import naturalness_proxies

# Success codings, both written on every row so the choice between them is
# not made after seeing results (protocol §9).
STRICT = {"pass": 1, "partial": 0, "fail": 0}      # primary
LENIENT = {"pass": 1, "partial": 1, "fail": 0}     # robustness check


# ── PRIMARY: task success ────────────────────────────────────────────────

def _deterministic(row: Dict[str, Any], task: Dict[str, Any]
                   ) -> Optional[Tuple[str, str]]:
    """Score the task types that need no grader. None means "ask the judge"."""
    spec = task.get("success") or {}
    kind = spec.get("type")
    reply = row.get("reply") or ""

    if kind == "regex":
        hit = re.search(spec["pattern"], reply)
        return ("pass" if hit else "fail",
                f"regex {spec['pattern']!r} {'matched' if hit else 'did not match'}")

    if kind == "contains_all":
        # `any_of` is a list of alternative required-substring sets: any one
        # set fully present is a pass. That is how "5:25 pm" and "17:25" are
        # both correct without a grader deciding so on the day.
        for group in spec.get("any_of") or []:
            if all(str(s).lower() in reply.lower() for s in group):
                return "pass", f"contains all of {group}"
        return "fail", f"none of {spec.get('any_of')} fully present"

    return None


def score_success(row: Dict[str, Any], task: Dict[str, Any],
                  judge: Optional[Judge]) -> Dict[str, Any]:
    if row.get("error"):
        # A run that could not complete is a fail, and the reason is kept.
        # This is where the local model's timeouts land, and they belong in
        # the results rather than missing from them.
        return {"success": "fail", "success_by": "error",
                "success_why": row["error"]}

    determined = _deterministic(row, task)
    if determined is not None:
        verdict, why = determined
        return {"success": verdict, "success_by": "deterministic",
                "success_why": why}

    if judge is None:
        return {"success": "unjudged", "success_by": "rubric",
                "success_why": "no judge supplied"}

    result = judge.verdict(BlindCase.from_row(row, task))
    return {"success": result["verdict"], "success_by": "rubric",
            "success_why": result.get("reason", ""),
            "judge_model": result.get("judge_model", "")}


# ── MECHANISM: decision accuracy ─────────────────────────────────────────

def _tools_ok(ideal_tools: List[str], used: List[str],
              mutations: List[str]) -> bool:
    """Did the run reach for an acceptable action?

    Three cases, and they are genuinely different:

    - **Empty ideal.** The ideal was to ask or decline, so *acting* was the
      wrong move. Scored on `mutations`, not on tool names — see below.
    - **`answer_directly` present.** No action was needed. Making no tool
      call satisfies it; so does any other tool the author listed alongside,
      since `tool_any` is an any-of set.
    - **Otherwise.** At least one listed action must have been used.

    **Why the empty case is scored on mutations.** Corrected 2026-08-19
    (pre-data), on a pilot row that exposed it. `clar-07` — *"clear out the
    old downloads"* — has the ideal *ask, and delete nothing*. A local
    deciding run listed the folder, reached for `delete_file` without a path,
    was stopped by the rule that refuses to guess, and asked. That is the
    ideal behaviour on every observable dimension, and the first version of
    this function scored its tools component wrong, because `list_files`
    appeared in the trace.

    Looking before asking is not acting. `world.mutations()` already draws
    exactly that line, and its docstring says why — *"a task whose ideal is
    to ask may legitimately look around first"* — so the sandbox anticipated
    this and the scorer was simply not using the distinction it provides.

    A refused tool call counts as no action for the same reason: it changed
    nothing. What it *reached for* is not lost — `ask_origin=rule` and
    `missing_arguments` record the mechanism on the same row.
    """
    used_set = set(used or [])
    if not ideal_tools:
        return not (mutations or [])
    if ANSWER_DIRECTLY in ideal_tools and not used_set:
        return True
    return bool(set(ideal_tools) & used_set)


def score_decision(row: Dict[str, Any], task: Dict[str, Any]) -> Dict[str, Any]:
    """Component-wise comparison against the derived ideal.

    `required` components must all match for the decision to count as
    correct. `preferred` ones are reported but do not gate it — protocol §6b
    fixes that weighting, and it is read from the task's own `credit` block
    rather than restated here, so the two cannot drift apart.
    """
    ideal = task.get("ideal_decision") or {}
    credit = ideal.get("credit") or {}
    decision = row.get("decision") or {}

    got = {
        "asked": bool(decision.get("asked")),
        "declined": bool(decision.get("declined")),
        "backgrounded": bool(decision.get("backgrounded")),
        "decomposed": bool(decision.get("decomposed")),
    }
    components = {k: (got[k] == bool(ideal.get(k))) for k in got}
    components["tools"] = _tools_ok(list(ideal.get("tools") or []),
                                    list(decision.get("tools") or []),
                                    list(row.get("mutations") or []))

    required = [k for k, w in credit.items() if w == "required"]
    preferred = [k for k, w in credit.items() if w == "preferred"]

    return {
        "decision_correct": all(components.get(k, False) for k in required),
        "decision_components": components,
        "decision_required": required,
        "decision_preferred_met": {k: components.get(k) for k in preferred},
        "ask_origin": decision.get("ask_origin", "none"),
        "over_asked": got["asked"] and not bool(ideal.get("asked")),
        "under_asked": bool(ideal.get("asked")) and not got["asked"],
    }


# ── the pass over a log ──────────────────────────────────────────────────

def score_log(runs_path: str, tasks_path: str, out_path: str, *,
              judge: Optional[Judge] = None, verbose: bool = True,
              allow_task_set_change: str = "") -> int:
    """Score every row in a log against the task set it names.

    `allow_task_set_change` is the escape hatch for the one legitimate case:
    protocol §8's validity gate recalibrated the task set, and the existing
    transcripts are re-scored against the corrected ideals. Re-scoring is
    *better* than re-running there — the models' inputs did not change, so
    re-running would add fresh sampling noise confounded with the
    recalibration — but it means joining rows to a task set whose bytes they
    never saw. That has to be a conscious act with a stated reason, not a
    silent one, so it is refused without a reason string and the reason is
    written onto every scored row.
    """
    import hashlib
    with open(tasks_path, "rb") as fh:
        blob = fh.read()
    tasks_sha = hashlib.sha256(blob).hexdigest()
    tasks = {t["id"]: t for t in json.loads(blob.decode("utf-8"))}

    rows = read_rows(runs_path)
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    written = 0
    with open(out_path, "w", encoding="utf-8", newline="\n") as out:
        for row in rows:
            task = tasks.get(row["task_id"])
            if task is None:
                # A row for a task the current set does not contain means the
                # task set moved under the data. Loud, not skipped.
                raise ValueError(
                    f"row {row.get('run_id')} names task {row['task_id']!r}, "
                    f"which is not in {tasks_path}. The task set has changed "
                    f"since this run; scoring it would join the wrong ideal.")
            row_sha = row.get("tasks_sha256", "")
            if row_sha and row_sha != tasks_sha:
                if not allow_task_set_change:
                    raise ValueError(
                        f"row {row.get('run_id')} was produced against "
                        f"tasks.json {row_sha[:12]} but is being scored "
                        f"against {tasks_sha[:12]}. Pass "
                        f"allow_task_set_change='<reason>' if this is a "
                        f"validity-gate recalibration; otherwise the join is "
                        f"to a task set these runs never saw.")
            scored = dict(row)
            scored["tasks_sha256_at_scoring"] = tasks_sha
            if row_sha and row_sha != tasks_sha:
                scored["task_set_changed_since_run"] = allow_task_set_change
            scored.update(score_success(row, task, judge))
            scored.update(score_decision(row, task))
            scored["success_strict"] = STRICT.get(scored["success"])
            scored["success_lenient"] = LENIENT.get(scored["success"])
            # §6d proxies. Computed here so they ride on the same row as the
            # primary outcome and cannot be produced from a different pass
            # over different data.
            scored.update(naturalness_proxies(row.get("reply") or "",
                                              task.get("expected_length")))
            out.write(json.dumps(scored, ensure_ascii=False) + "\n")
            written += 1

    if verbose:
        print(f"scored {written} rows -> {out_path}")
        if judge is not None:
            print(f"  judge calls {judge.calls}, ${judge.cost_usd:.4f}, "
                  f"{len(judge.cache)} cached verdicts")
    return written


__all__ = ["score_log", "score_success", "score_decision", "STRICT", "LENIENT"]
