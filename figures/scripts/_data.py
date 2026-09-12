"""Shared loading and resampling for the result figures.

Every result figure reads the frozen record directly, so no number is ever
transcribed by hand between the run and the page. The resampling here is the
same procedure the analysis used: draw 48 tasks with replacement, carry each
drawn task's five repetitions with it, and recompute. Repetitions of one task
are not independent observations, so the task is the unit.

The generator, the seed and the percentile rule are the same ones
`apparatus/harness/analyze.py` used, so a figure's interval is the interval in
the frozen record rather than a near-miss of it.
"""

import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

import numpy as np

RUN = Path(__file__).resolve().parents[3] / "runs" / "full-2026-08-20"

CELLS = ["C1", "C2", "C3", "C4"]
DESIGN = {"C1": "deciding", "C2": "deciding", "C3": "routing", "C4": "routing"}
DEPLOY = {"C1": "cloud", "C2": "on-device", "C3": "cloud", "C4": "on-device"}
CATS = ["trivial", "action", "clarification", "grounding",
        "reasoning", "robustness"]

RESAMPLES = 5000
SEED = 20260819

# The house palette, from docs/figures/README.md.
INK = "#1B1B1B"
MUTED = "#6B6B6B"
RULE = "#C9C6C0"
SURFACE = "#F5F4F1"
ACCENT = "#33506A"


def load():
    with open(RUN / "scored.jsonl", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def by_task(rows, field="success_strict"):
    """{task_id: {cell: [value per repetition]}} -- the resampling unit."""
    out = defaultdict(lambda: defaultdict(list))
    for r in rows:
        out[r["task_id"]][r["cell"]].append(r[field])
    return {t: dict(c) for t, c in out.items()}


def cell_means(per_task, tasks=None):
    tasks = list(per_task) if tasks is None else tasks
    return {c: mean(v for t in tasks for v in per_task[t][c]) for c in CELLS}


def bootstrap(per_task, statistic, resamples=RESAMPLES, seed=SEED):
    """Percentile interval for any statistic of the cell means.

    `statistic` takes the dict of cell means and returns one number.
    """
    tasks = list(per_task)
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(resamples):
        drawn = list(rng.choice(tasks, size=len(tasks), replace=True))
        draws.append(statistic(cell_means(per_task, drawn)))
    return (statistic(cell_means(per_task)),
            float(np.percentile(draws, 2.5)),
            float(np.percentile(draws, 97.5)))


def save(fig, stem):
    out = Path(__file__).resolve().parents[1]
    for ext, kw in (("png", {"dpi": 300}), ("pdf", {})):
        fig.savefig(out / f"{stem}.{ext}", facecolor="white",
                    bbox_inches="tight", **kw)
    print(f"wrote {stem}.png / .pdf to {out}")
