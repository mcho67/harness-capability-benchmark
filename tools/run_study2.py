"""Run Study 2 — the capability sweep and the ablation.

Registered in `docs/protocol_ext.md`, tag `study2-registered`. Nothing here
decides anything: the model list, the variants, the repetition count and the
budget were all fixed before this file could produce a row, and this is the
machinery that carries them out.

**Everything goes through the frozen harness.** The arms are registered into
`arms.ARMS` and the configurations into `run_cell.CELLS` at runtime, so every
Study 2 row is produced by the same runner, the same sandbox, the same task
order seed and the same row schema as Study 1's. That is what makes the two
studies comparable at all. Runtime registration does not touch a file, so
`git diff paper-baseline` over the instrument directories still prints
nothing.

**The ablation is gated.** Two of the three variants rely on a `take_turn`
rewritten outside the freeze, and §4 of the registration makes the
faithfulness check a precondition of producing any ablation row. This file
refuses to run them until `runs/ablation_faithfulness.json` records a pass —
not as a courtesy, but because an unverified rewrite would turn an unrelated
difference into an apparent ablation effect.

**Resuming is safe and re-running is not silent.** Each configuration writes
its own row file. A configuration whose file already holds a complete set of
rows is skipped and said to be skipped; a partial file is refused rather than
appended to, because `capture.py` opens in append mode and a half-finished
cell topped up later would mix two passes in one file.

Usage:
    python tools/run_study2.py --plan                 # print, run nothing
    python tools/run_study2.py --sweep --on-device    # free
    python tools/run_study2.py --sweep --cloud        # ~$1.25
    python tools/run_study2.py --ablation --on-device # free, gated
    python tools/run_study2.py --ablation --cloud     # ~$5.60, gated
    python tools/run_study2.py --score                # ~$2.80
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apparatus"))
sys.path.insert(0, str(ROOT / "tools"))

import arms as frozen_arms                                   # noqa: E402
from harness.capture import read_rows                        # noqa: E402
from harness.judge import Judge                              # noqa: E402
from harness.score import score_log                          # noqa: E402
from ablations.arms import (NoAskArm, NoIterationArm,        # noqa: E402
                            NoMultiDispatchArm)

run_cell_mod = importlib.import_module("harness.run_cell")

OUT = ROOT / "runs" / "study2"
TASKS = ROOT / "apparatus" / "tasks" / "tasks.json"
FAITHFULNESS = ROOT / "runs" / "ablation_faithfulness.json"

REPETITIONS = 3          # protocol_ext §3; Study 1 used 5
N_TASKS = 48

# The ladder, exactly as registered. Study 1's own two models are absent:
# their rows exist and are not re-run.
SWEEP_MODELS = [
    ("claude-haiku-4-5-20251001", "anthropic"),
    ("llama3.2:3b",               "ollama"),
    ("qwen2.5:7b",                "ollama"),
    ("qwen2.5:3b",                "ollama"),
    ("qwen2.5:1.5b",              "ollama"),
    ("mistral:7b",                "ollama"),
]

# Both designs, under their frozen names.
SWEEP_ARMS = ["deciding", "routing"]

# The three variants, against Study 1's own models so the comparison is with
# C1 through C4 rather than with a differently-modelled baseline.
ABLATION_ARMS = [NoIterationArm, NoMultiDispatchArm, NoAskArm]
ABLATION_MODELS = [("claude-sonnet-4-6", "anthropic"),
                   ("llama3.1:8b",       "ollama")]


def register() -> None:
    for arm in ABLATION_ARMS:
        frozen_arms.ARMS[arm.name] = arm


def cell_id(arm: str, model: str) -> str:
    """A configuration's name, readable and unique.

    Study 1 used C1-C4. Study 2's names carry the arm and the model instead,
    because a ladder of eight models times four arms has no natural ordering
    and a numbered cell would need a lookup table to mean anything.
    """
    return f"{arm}@{model}".replace(":", "-").replace("/", "-")


def plan() -> list:
    jobs = []
    for model, provider in SWEEP_MODELS:
        for arm in SWEEP_ARMS:
            jobs.append({"kind": "sweep", "arm": arm, "model": model,
                         "provider": provider})
    for arm in ABLATION_ARMS:
        for model, provider in ABLATION_MODELS:
            jobs.append({"kind": "ablation", "arm": arm.name, "model": model,
                         "provider": provider})
    for job in jobs:
        job["cell"] = cell_id(job["arm"], job["model"])
        job["rows"] = N_TASKS * REPETITIONS
        job["path"] = OUT / f"{job['cell']}.jsonl"
    return jobs


def gate_ablations() -> None:
    """Refuse to produce an ablation row without a passing faithfulness check."""
    if not FAITHFULNESS.exists():
        raise SystemExit(
            "docs/protocol_ext.md §4 requires the faithfulness check to pass "
            "before any ablation row exists, and "
            f"{FAITHFULNESS.relative_to(ROOT)} is not there. Run "
            "tools/ablations/faithfulness.py first.")
    report = json.loads(FAITHFULNESS.read_text(encoding="utf-8"))
    if report.get("verdict") != "PASS":
        raise SystemExit(
            f"the faithfulness check records {report.get('verdict')!r}. Per "
            "docs/protocol_ext.md §4 no ablation row may be produced until "
            "that is understood.")
    if not report.get("tasks_scored"):
        raise SystemExit(
            "the faithfulness check scored no tasks — its noise floor "
            "excluded the whole set, so it establishes nothing.")
    print(f"faithfulness: PASS on {report['tasks_scored']} reproducible "
          f"tasks, {len(report.get('tasks_excluded_noise_floor') or [])} "
          f"excluded by the measured noise floor.\n")


def already_done(job: dict) -> bool:
    path = job["path"]
    if not path.exists():
        return False
    n = len(read_rows(str(path)))
    if n == job["rows"]:
        return True
    raise SystemExit(
        f"{path.name} holds {n} rows, not {job['rows']}. `capture.py` appends, "
        f"so continuing would mix two passes in one file. Delete it to redo "
        f"the configuration, or move it aside to keep it.")


def run_job(job: dict) -> None:
    run_cell_mod.CELLS[job["cell"]] = (job["arm"], job["provider"])
    spec = run_cell_mod.CellSpec(
        cell=job["cell"],
        model=job["model"],
        out_path=str(job["path"]),
        scratch_dir=str(OUT / f"scratch-{job['cell']}"),
        repetitions=REPETITIONS,
        tasks_path=str(TASKS),
    )
    job["path"].parent.mkdir(parents=True, exist_ok=True)
    written = run_cell_mod.run_cell(spec, repo_root=str(ROOT))
    if written != job["rows"]:
        raise SystemExit(f"{job['cell']} wrote {written} rows, expected "
                         f"{job['rows']}; the cell did not complete")


def score() -> None:
    """Score every Study 2 row file with the study's own grader.

    One judge cache across all of Study 2, for the same reason Study 1 kept
    one: scoring is re-runnable, and a per-file cache would let the same
    transcript be graded twice and answered differently.
    """
    judge = Judge(str(OUT / "judge_cache.json"))
    total = 0
    for path in sorted(OUT.glob("*.jsonl")):
        if path.name.endswith(".scored.jsonl"):
            continue
        out = path.with_suffix(".scored.jsonl")
        n = score_log(str(path), str(TASKS), str(out), judge=judge)
        total += n
        print(f"  {path.name}: {n} rows -> {out.name}")
    print(f"\nscored {total} rows; judge spent ${judge.cost_usd:.4f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--ablation", action="store_true")
    ap.add_argument("--cloud", action="store_true")
    ap.add_argument("--on-device", action="store_true")
    ap.add_argument("--score", action="store_true")
    args = ap.parse_args()

    register()
    jobs = plan()

    if args.plan or not any((args.sweep, args.ablation, args.score)):
        cloud = [j for j in jobs if j["provider"] == "anthropic"]
        print(f"{len(jobs)} configurations, {sum(j['rows'] for j in jobs)} rows "
              f"({len(cloud)} configurations on the paid provider)\n")
        for job in jobs:
            state = "done" if job["path"].exists() else "    "
            print(f"  [{state}] {job['kind']:8s} {job['cell']:44s} "
                  f"{job['rows']:4d} rows  {job['provider']}")
        return

    if args.score:
        score()
        return

    wanted = []
    if args.sweep:
        wanted += [j for j in jobs if j["kind"] == "sweep"]
    if args.ablation:
        gate_ablations()
        wanted += [j for j in jobs if j["kind"] == "ablation"]
    if args.cloud or args.on_device:
        providers = ({"anthropic"} if args.cloud else set()) | \
                    ({"ollama"} if args.on_device else set())
        wanted = [j for j in wanted if j["provider"] in providers]

    for job in wanted:
        if already_done(job):
            print(f"skip {job['cell']}: {job['rows']} rows already on disk")
            continue
        print(f"\n=== {job['kind']}: {job['cell']} ===")
        run_job(job)


if __name__ == "__main__":
    main()
