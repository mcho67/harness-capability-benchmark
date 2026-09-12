"""Does the finding depend on who graded it?

Thirty-three of the 48 tasks are scored by a model reading the transcript
against the task's own pre-written criterion. That model is
`claude-sonnet-4-6` — which is also the cloud treatment model, a coincidence
`harness/judge.py` names as a threat rather than hides. A grader that prefers
output from its own family would push toward the cloud configurations, in
both designs.

This re-grades every rubric case with two further graders and asks whether
anything moves.

**The two graders were chosen to have opposite expected biases.** If
self-preference is real, `claude-haiku-4-5` shares the cloud model's family
and should lean the same way the original grader does; `llama3.1:8b` *is* the
on-device treatment model and should lean the other way. A contrast that
survives both is one that self-preference cannot be steering, because no
single direction of bias explains all three results. That argument is
stronger than adding one more grader of unknown allegiance.

**Nothing under the freeze is touched.** `apparatus/` is frozen at
`paper-baseline` and a change to it invalidates the run, so this file imports
`BlindCase`, the system prompt and the verdict tool rather than copying or
editing them. The blinding guarantee is therefore the same object the study
used, not a reconstruction of it: `BlindCase.from_row` still raises if a
cell-identifying field is present.

**Cases, not runs.** Temperature was pinned to zero, so the 660 rubric-scored
runs collapse to 214 distinct transcripts. Grading is per distinct case and
is cached, which is why a full re-grade is cents rather than dollars.

Usage:
    python tools/grader_crosscheck.py --grader haiku      # ~$0.20
    python tools/grader_crosscheck.py --grader llama      # free, local
    python tools/grader_crosscheck.py --report            # no API calls
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apparatus"))

from core.llm import LLMConfig, build_provider          # noqa: E402
from harness.capture import read_rows                   # noqa: E402
from harness.judge import (BlindCase, JUDGE_SYSTEM,     # noqa: E402
                           VERDICT_TOOL, VERDICTS)
from harness.score import STRICT, LENIENT               # noqa: E402

SCORED = ROOT / "runs" / "full-2026-08-20" / "scored.jsonl"
TASKS = ROOT / "apparatus" / "tasks" / "tasks.json"
OUT = ROOT / "runs" / "grader_crosscheck"

# The grader of record, and the two the study did not use. Named here rather
# than passed loose, so which graders were tried is part of the file.
GRADERS = {
    "sonnet": {"provider": "anthropic", "model": "claude-sonnet-4-6",
               "note": "the grader of record; shares a family with the cloud "
                       "treatment model"},
    "haiku":  {"provider": "anthropic", "model": "claude-haiku-4-5-20251001",
               "note": "same family as the cloud treatment, different model"},
    "llama":  {"provider": "ollama", "model": "llama3.1:8b",
               "note": "is the on-device treatment model; expected bias runs "
                       "opposite to the grader of record"},
}


def rubric_cases() -> tuple:
    """Every distinct rubric transcript, and the rows that map onto it."""
    rows = read_rows(str(SCORED))
    tasks = {t["id"]: t for t in json.loads(TASKS.read_text(encoding="utf-8"))}
    cases, index = {}, []
    for row in rows:
        task = tasks[row["task_id"]]
        if (task.get("success") or {}).get("type") != "rubric":
            continue
        case = BlindCase.from_row(row, task)
        cases[case.case_id] = case
        index.append({"case_id": case.case_id, "task_id": row["task_id"],
                      "cell": row["cell"], "repetition": row["repetition"],
                      "sonnet": row["success"]})
    return cases, pd.DataFrame(index)


def grade(cases: dict, label: str, limit: int = 0) -> dict:
    """Grade every case with one grader, caching by case id."""
    spec = GRADERS[label]
    cache_path = OUT / f"verdicts_{label}.json"
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}

    todo = [c for cid, c in cases.items() if cid not in cache]
    if limit:
        todo = todo[:limit]
    if not todo:
        print(f"[{label}] nothing to grade; {len(cache)} cached")
        return cache

    provider = build_provider(LLMConfig(provider=spec["provider"],
                                        model=spec["model"]))
    provider.preflight()
    print(f"[{label}] grading {len(todo)} of {len(cases)} cases with "
          f"{spec['model']}")

    OUT.mkdir(parents=True, exist_ok=True)
    for i, case in enumerate(todo, 1):
        completion = provider.complete(
            system=JUDGE_SYSTEM,
            messages=[{"role": "user", "content": case.prompt()}],
            tools=[VERDICT_TOOL])
        verdict, reason = None, ""
        for call in completion.tool_calls:
            if call.name == VERDICT_TOOL["name"]:
                verdict = str(call.arguments.get("verdict") or "").strip().lower()
                reason = str(call.arguments.get("reason") or "").strip()
        if verdict not in VERDICTS:
            # Recorded, never guessed. A grader that would not answer in the
            # required form is a fact about that grader, and silently
            # coercing it to `fail` would invent agreement.
            verdict = "unparseable"
        cache[case.case_id] = {"verdict": verdict, "reason": reason,
                               "grader": spec["model"]}
        if i % 25 == 0 or i == len(todo):
            cache_path.write_text(json.dumps(cache, indent=2, ensure_ascii=False),
                                  encoding="utf-8")
            print(f"  {i}/{len(todo)}  spent ${provider.total_cost_usd:.4f}")

    cache_path.write_text(json.dumps(cache, indent=2, ensure_ascii=False),
                          encoding="utf-8")
    print(f"[{label}] done. {len(todo)} calls, ${provider.total_cost_usd:.4f}")
    return cache


def kappa(a: pd.Series, b: pd.Series, labels: list) -> float:
    """Cohen's kappa — chance-corrected agreement, as §3.7 already reports."""
    n = len(a)
    observed = float((a.to_numpy() == b.to_numpy()).mean())
    expected = sum((a == k).mean() * (b == k).mean() for k in labels)
    return float((observed - expected) / (1.0 - expected)) if expected < 1 else 1.0


def report() -> None:
    cases, index = rubric_cases()
    print(f"{len(cases)} distinct rubric transcripts across {len(index)} runs\n")

    for label in ("haiku", "llama"):
        path = OUT / f"verdicts_{label}.json"
        if not path.exists():
            print(f"[{label}] not graded yet\n")
            continue
        cache = json.loads(path.read_text(encoding="utf-8"))
        index[label] = index["case_id"].map(lambda c: (cache.get(c) or {}).get("verdict"))

    graded = [g for g in ("haiku", "llama") if g in index.columns]
    if not graded:
        return

    frame = index.dropna(subset=graded)
    unparseable = {g: int((frame[g] == "unparseable").sum()) for g in graded}
    frame = frame[~(frame[graded] == "unparseable").any(axis=1)]

    print("agreement with the grader of record, over the three verdicts:")
    for g in graded:
        raw = float((frame["sonnet"] == frame[g]).mean())
        k = kappa(frame["sonnet"], frame[g], list(VERDICTS))
        print(f"  {g:8s} raw {raw:.3f}   kappa {k:.3f}   "
              f"unparseable {unparseable[g]}")

    print("\nagreement on the primary coding (partial counts as failure):")
    for g in graded:
        a = frame["sonnet"].map(STRICT)
        b = frame[g].map(STRICT)
        print(f"  {g:8s} raw {float((a == b).mean()):.3f}   "
              f"kappa {kappa(a, b, [0, 1]):.3f}")

    print("\nthe compensation contrast under each grader:")
    for coding, table in (("strict", STRICT), ("lenient", LENIENT)):
        print(f"  {coding}")
        for g in ["sonnet"] + graded:
            wide = (frame.assign(y=frame[g].map(table))
                    .pivot_table(index="task_id", columns="cell",
                                 values="y", aggfunc="mean"))
            if wide.isna().any().any() or not {"C1", "C2", "C3", "C4"} <= set(wide.columns):
                print(f"    {g:8s} (incomplete cells; not computed)")
                continue
            d = ((wide["C3"] - wide["C4"]) - (wide["C1"] - wide["C2"])).to_numpy()
            rng = np.random.default_rng(20260819)
            draws = d[rng.integers(0, d.size, size=(5000, d.size))].mean(axis=1)
            print(f"    {g:8s} {d.mean():+.4f}  "
                  f"CI [{np.percentile(draws, 2.5):+.4f}, "
                  f"{np.percentile(draws, 97.5):+.4f}]   (rubric tasks only, "
                  f"n={d.size})")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--grader", choices=["haiku", "llama"])
    ap.add_argument("--limit", type=int, default=0,
                    help="grade at most this many new cases (cost control)")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    cases, _ = rubric_cases()
    if args.grader:
        grade(cases, args.grader, args.limit)
    if args.report or not args.grader:
        report()


if __name__ == "__main__":
    main()
