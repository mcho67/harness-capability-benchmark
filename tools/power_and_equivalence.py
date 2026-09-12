"""What this study could have detected, and what it can rule out.

A null result is only a finding if the study could have found the effect had
it been there. This computes two things the paper does not currently state.

**Power.** For a range of true compensation effects, how often would a study
of this size and shape return an interval that excludes zero? The minimum
detectable effect is the value where that reaches 80%.

**Equivalence.** The interval in §4.2 fails to exclude zero. That is not the
same as showing there is no effect. Two one-sided tests at alpha = 0.05
correspond to asking whether the 90% interval lies wholly inside a margin
fixed in advance. If it does, the finding is not "we did not detect
compensation" but "compensation larger than the margin is ruled out."

**The estimator is not re-implemented.** The pre-registered contrast
`(C3-C4) - (C1-C2)` on a balanced design with the same repetition count in
every cell is exactly the mean of one number per task,

    d_i = (C3_i - C4_i) - (C1_i - C2_i),

and the task bootstrap in `analyze.bootstrap_contrast` is the percentile
bootstrap of that mean. This file asserts that equality against the recorded
report before it computes anything, and stops if it does not hold.

**The simulation.** To model a world where the true effect is delta, the
observed per-task contrasts are shifted to have mean delta and otherwise left
alone, so the simulated tasks keep the real distribution's shape — including
that most tasks separate the designs identically and a few separate them
completely. Studies are then drawn from that population at the real task
count. This assumes the shape of task-to-task variation would not itself
change with the effect size, which is an assumption and is stated as one.

Usage:  python tools/power_and_equivalence.py

The defaults are the settings that produced the committed
`runs/power_and_equivalence.json`, and with seed 20260819 a bare run
reproduces that file byte for byte. They were 2000 and 2000 until
2026-09-08, which did not match the file: the power curve is simulated, and
re-running at the lower settings moved the power at delta = 0.15 from 0.512
to 0.523. The analytic quantities -- sd_task_contrasts, the standard error,
the 74 tasks, the equivalence intervals -- do not move at any setting.
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

SCORED = ROOT / "runs" / "full-2026-08-20" / "scored.jsonl"
REPORT = ROOT / "runs" / "full-2026-08-20" / "report.json"

# The pre-registered analysis fixed both of these. They are not tuned here.
RESAMPLES = A.BOOTSTRAP_RESAMPLES
SEED = A.BOOTSTRAP_SEED

DELTAS = [0.0, 0.05, 0.10, 0.125, 0.15, 0.175, 0.20, 0.25, 0.30, 0.35, 0.40]
MARGINS = [0.10, 0.125, 0.15, 0.20, 0.25]
TARGET_POWER = 0.80


def task_contrasts(frame: pd.DataFrame, coding: str) -> tuple:
    """One number per task: the compensation contrast computed within it.

    Returned in the order `analyze.bootstrap_contrast` sees the tasks, since
    that order is what its `rng.choice` draws over.
    """
    order = frame["task_id"].unique()
    wide = frame.pivot_table(index="task_id", columns="cell",
                             values=coding, aggfunc="mean").reindex(order)
    missing = [c for c in ("C1", "C2", "C3", "C4") if c not in wide.columns]
    if missing:
        raise SystemExit(f"cells absent from {coding}: {missing}")
    if wide.isna().any().any():
        raise SystemExit("a task is missing a cell; the design is unbalanced "
                         "and the task-level identity does not hold")
    d = (wide["C3"] - wide["C4"]) - (wide["C1"] - wide["C2"])
    return d.to_numpy(dtype=float), order


def observed_ci(values: np.ndarray, task_ids: np.ndarray, resamples: int,
                seed: int, alpha: float) -> tuple:
    """The interval on the real data, drawn exactly as `analyze` draws it.

    `bootstrap_contrast` calls `rng.choice` over the array of task ids, not
    `rng.integers` over positions. The two consume the generator differently
    and land a few thousandths apart at 5,000 resamples, so reproducing §4.2's
    published bounds means reproducing its draw, not merely its method. The
    90% interval the equivalence test needs is then the same draw read at
    different percentiles.
    """
    pos = {t: i for i, t in enumerate(task_ids)}
    rng = np.random.default_rng(seed)
    draws = np.empty(resamples)
    for i in range(resamples):
        picked = rng.choice(task_ids, size=task_ids.size, replace=True)
        draws[i] = values[np.fromiter((pos[p] for p in picked),
                                      dtype=int, count=picked.size)].mean()
    lo = 100.0 * (alpha / 2.0)
    return float(np.percentile(draws, lo)), float(np.percentile(draws, 100.0 - lo))


def power_at(d: np.ndarray, delta: float, sims: int, inner: int,
             rng: np.random.Generator) -> float:
    """Fraction of simulated studies whose 95% interval excludes zero."""
    shifted = d - d.mean() + delta
    n = shifted.size
    hits = 0
    chunk = 50
    for start in range(0, sims, chunk):
        k = min(chunk, sims - start)
        studies = shifted[rng.integers(0, n, size=(k, n))]          # k x n
        idx = rng.integers(0, n, size=(k, inner, n))
        draws = np.take_along_axis(
            studies[:, None, :], idx, axis=2).mean(axis=2)          # k x inner
        lo = np.percentile(draws, 2.5, axis=1)
        hi = np.percentile(draws, 97.5, axis=1)
        hits += int(np.sum((lo > 0) | (hi < 0)))
    return hits / sims


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sims", type=int, default=4000)
    ap.add_argument("--inner", type=int, default=3000)
    ap.add_argument("--out", default=str(ROOT / "runs" / "power_and_equivalence.json"))
    args = ap.parse_args()

    frame = A.load_scored(str(SCORED))
    recorded = json.loads(REPORT.read_text(encoding="utf-8"))["bootstrap"]

    report: dict = {
        "source": str(SCORED.relative_to(ROOT)),
        "resamples": RESAMPLES,
        "seed": SEED,
        "sims": args.sims,
        "inner_resamples": args.inner,
        "target_power": TARGET_POWER,
        "codings": {},
    }

    for coding in (A.PRIMARY_CODING, A.ROBUSTNESS_CODING):
        d, task_ids = task_contrasts(frame, coding)
        point = float(d.mean())

        if coding == A.PRIMARY_CODING:
            # The task-level identity must reproduce the recorded estimate
            # exactly, or the rest of this file is measuring something else.
            if abs(point - recorded["point"]) > 1e-9:
                raise SystemExit(
                    f"task-level contrast {point!r} does not reproduce the "
                    f"recorded estimate {recorded['point']!r}")

        ci95 = observed_ci(d, task_ids, RESAMPLES, SEED, 0.05)
        ci90 = observed_ci(d, task_ids, RESAMPLES, SEED, 0.10)
        if coding == A.PRIMARY_CODING:
            for got, want in ((ci95[0], recorded["ci_low"]),
                              (ci95[1], recorded["ci_high"])):
                if abs(got - want) > 1e-9:
                    raise SystemExit(
                        f"interval {ci95} does not reproduce the recorded "
                        f"{[recorded['ci_low'], recorded['ci_high']]}")

        rng = np.random.default_rng(SEED)
        curve = {f"{x:.3f}": power_at(d, x, args.sims, args.inner, rng)
                 for x in DELTAS}

        # Smallest delta on the grid reaching the target, with the bracketing
        # pair reported so the interpolation is visible rather than implied.
        mde = None
        keys = [float(k) for k in curve]
        for lo_d, hi_d in zip(keys, keys[1:]):
            if curve[f"{lo_d:.3f}"] < TARGET_POWER <= curve[f"{hi_d:.3f}"]:
                span = curve[f"{hi_d:.3f}"] - curve[f"{lo_d:.3f}"]
                frac = 0.0 if span == 0 else (TARGET_POWER - curve[f"{lo_d:.3f}"]) / span
                mde = {"estimate": round(lo_d + frac * (hi_d - lo_d), 4),
                       "bracket": [lo_d, hi_d],
                       "power_at_bracket": [curve[f"{lo_d:.3f}"], curve[f"{hi_d:.3f}"]]}
                break

        equivalence = {
            f"{m:.3f}": bool(ci90[0] > -m and ci90[1] < m) for m in MARGINS
        }

        # How many tasks a margin of 0.15 would have needed, on the normal
        # approximation. Indicative, not a substitute for the simulation.
        se = float(d.std(ddof=1) / np.sqrt(d.size))
        needed = {
            f"{m:.3f}": int(np.ceil((1.645 * d.std(ddof=1) / (m - abs(point))) ** 2))
            if m > abs(point) else None
            for m in MARGINS
        }

        report["codings"][coding] = {
            "n_tasks": int(d.size),
            "point": point,
            "sd_task_contrasts": float(d.std(ddof=1)),
            "se_of_mean": se,
            "ci95": list(ci95),
            "ci90": list(ci90),
            "power_curve": curve,
            "mde_80": mde,
            "equivalence_at_margin": equivalence,
            "tasks_needed_for_margin": needed,
        }

        print(f"\n=== {coding} (n = {d.size} tasks) ===")
        print(f"point {point:+.4f}   95% CI [{ci95[0]:+.4f}, {ci95[1]:+.4f}]"
              f"   90% CI [{ci90[0]:+.4f}, {ci90[1]:+.4f}]")
        print(f"sd of task contrasts {d.std(ddof=1):.4f}   se {se:.4f}")
        print("\n  power to detect a true compensation of:")
        for k, v in curve.items():
            print(f"    {float(k):+.3f}   {v:.3f}")
        if mde:
            print(f"\n  minimum detectable effect at {TARGET_POWER:.0%} power: "
                  f"~{mde['estimate']:+.3f}")
        else:
            print(f"\n  {TARGET_POWER:.0%} power not reached on the grid")
        print("\n  equivalence (90% CI inside the margin):")
        for m, ok in equivalence.items():
            print(f"    +/-{float(m):.3f}   {'YES' if ok else 'no':>3s}"
                  f"    tasks needed: {needed[m]}")

    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("\nwrote", args.out)


if __name__ == "__main__":
    main()
