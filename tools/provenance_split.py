"""The compensation contrast, split by where each task came from.

Answers one question a reader is entitled to ask about any study whose task
set was assembled by the person testing the hypothesis: was the task set
built around the result?

Every task carries an `origin` field, written when the task was written.
Twenty-two are taken unchanged from a set of test requests that predates this
study; five are adapted from that set; twenty-one were authored for this
experiment. The conservative cut is therefore 22 that could not have been
shaped by the hypotheses against 26 that could.

If the contrast is null on both halves, the finding does not depend on the
tasks this study created for itself.

Nothing here re-implements the estimator. `bootstrap_contrast` and
`cell_means` are imported from the analysis module that produced every other
number in the paper, so a difference between this and §4.2 can only come from
the subset, never from the method.

Usage:  python tools/provenance_split.py [--out runs/provenance_split.json]
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apparatus"))

A = importlib.import_module("harness.analyze")

# `scored.jsonl` and not `runs.csv`. The CSV is a later conversion of the
# same 960 rows, sorted by task id; the bootstrap draws tasks with
# `rng.choice` over `task_id.unique()`, so a different row order consumes the
# generator differently and shifts the interval bounds by a few thousandths.
# The point estimate is identical either way, but a subset interval computed
# off the CSV would not sit consistently beside §4.2's, which came from this
# file.
RUNS = ROOT / "runs" / "full-2026-08-20" / "scored.jsonl"
TASKS = ROOT / "apparatus" / "tasks" / "tasks.json"

# The `origin` value marking a task taken unchanged from the pre-existing
# pool. The pool's internal name is not the paper's vocabulary — the paper
# calls it "a set of test requests that predates this study" — so the label is
# confined to this constant and never printed into a caption.
PRE_EXISTING = "frozen_v1"


def load() -> pd.DataFrame:
    frame = A.load_scored(str(RUNS))
    tasks = json.loads(TASKS.read_text(encoding="utf-8"))
    origin = {t["id"]: t["origin"] for t in tasks}
    frame["origin"] = frame["task_id"].map(origin)
    if frame["origin"].isna().any():
        missing = sorted(frame.loc[frame["origin"].isna(), "task_id"].unique())
        raise SystemExit(f"tasks with no origin recorded: {missing}")
    # Unchanged only. An adapted task was touched during this study, so it
    # belongs on the same side of the line as an authored one.
    frame["pre_existing"] = frame["origin"].eq(PRE_EXISTING)
    return frame


def contrast(frame: pd.DataFrame, coding: str) -> dict:
    boot = A.bootstrap_contrast(frame, coding=coding)
    means = A.cell_means(frame, coding)
    boot["cell_means"] = {c: means[c]["mean"] for c in sorted(A.CELLS)}
    boot["n_runs"] = int(len(frame))
    return boot


def halves_differ(frame: pd.DataFrame, coding: str) -> dict:
    """Do the two halves disagree by more than sampling noise?

    Reporting two subset intervals invites the reader to compare their point
    estimates by eye, which is not a test. This resamples the halves
    independently and gives the interval on their difference, so "the halves
    do not differ detectably" is a measured statement rather than an
    impression.

    Uses the task-level identity: on a design with the same repetition count
    in every cell, the pre-registered contrast is the mean of one number per
    task, so a subset contrast is the mean over that subset's tasks.
    """
    wide = frame.pivot_table(index="task_id", columns="cell",
                             values=coding, aggfunc="mean")
    d = (wide["C3"] - wide["C4"]) - (wide["C1"] - wide["C2"])
    pre = frame.groupby("task_id")["pre_existing"].first().reindex(d.index)
    a = d[pre].to_numpy(dtype=float)
    b = d[~pre].to_numpy(dtype=float)

    rng = np.random.default_rng(A.BOOTSTRAP_SEED)
    draws = np.empty(A.BOOTSTRAP_RESAMPLES)
    for i in range(A.BOOTSTRAP_RESAMPLES):
        draws[i] = (b[rng.integers(0, b.size, b.size)].mean()
                    - a[rng.integers(0, a.size, a.size)].mean())
    return {
        "difference": float(b.mean() - a.mean()),
        "ci_low": float(np.percentile(draws, 2.5)),
        "ci_high": float(np.percentile(draws, 97.5)),
        "direction": "study_written minus pre_existing",
    }


def category_mix(frame: pd.DataFrame) -> dict:
    """The category counts on each side.

    The halves were not matched on category — they could not be, since
    provenance was fixed when each task was written. `action` is the extreme
    case and it is the hardest category, so part of any gap between the halves
    is category mix rather than provenance. Printed so the caveat is carried
    by the numbers instead of by a sentence.
    """
    per_task = frame.groupby("task_id").agg(
        category=("category", "first"), pre_existing=("pre_existing", "first"))
    table = pd.crosstab(per_task["category"], per_task["pre_existing"])
    table.columns = ["study_written" if c is False else "pre_existing"
                     for c in table.columns]
    return {str(k): {c: int(v[c]) for c in table.columns}
            for k, v in table.iterrows()}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "runs" / "provenance_split.json"))
    args = ap.parse_args()

    frame = load()
    subsets = {
        "all": frame,
        "pre_existing": frame[frame["pre_existing"]],
        "study_written": frame[~frame["pre_existing"]],
    }

    report: dict = {
        "source": str(RUNS.relative_to(ROOT)),
        "resamples": A.BOOTSTRAP_RESAMPLES,
        "seed": A.BOOTSTRAP_SEED,
        "task_counts": {k: int(v["task_id"].nunique()) for k, v in subsets.items()},
        "category_mix": category_mix(frame),
        "codings": {},
    }

    for coding in (A.PRIMARY_CODING, A.ROBUSTNESS_CODING):
        report["codings"][coding] = {
            name: contrast(sub, coding) for name, sub in subsets.items()
        }
        report["codings"][coding]["halves_differ"] = halves_differ(frame, coding)
        for name, res in report["codings"][coding].items():
            if name == "halves_differ":
                print(f"{coding:16s} {'halves differ':14s} "
                      f"{res['difference']:+.4f} "
                      f"CI [{res['ci_low']:+.4f}, {res['ci_high']:+.4f}]  "
                      f"({res['direction']})")
                continue
            print(f"{coding:16s} {name:14s} tasks={res['n_tasks_resampled']:2d} "
                  f"runs={res['n_runs']:3d} comp={res['point']:+.4f} "
                  f"CI [{res['ci_low']:+.4f}, {res['ci_high']:+.4f}] "
                  f"ok={res['resamples']}/{res['resamples_requested']}")

    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("\nwrote", args.out)


if __name__ == "__main__":
    main()
