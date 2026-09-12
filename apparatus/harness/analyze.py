"""
`scored.jsonl` -> the numbers the paper reports.

Implements protocol §9 **as amended 2026-08-19 (pre-data)**. The superseded
plan — a two-way ANOVA and a run-level bootstrap — is not implemented here at
all, deliberately: leaving it available would make "which analysis did you
run" a choice made after seeing results.

**The primary estimand.** One contrast, fixed in advance:

    compensation = (C3 - C4) - (C1 - C2)

on task success, where C1/C2 are deciding cloud/local and C3/C4 are routing
cloud/local. It is the routing design's cloud-to-local drop minus the
deciding design's. **Its sign is not predicted anywhere** — the prior work is
genuinely split (`docs/related_work.md`), and this file computes a signed
number without asserting which way it should point.

**Estimated two ways that must agree.**

1. *Mixed-effects logistic regression*, `success ~ architecture * deployment
   + (1 | task)`, with the interaction tested by likelihood-ratio test.
   Logistic because the outcome is binary; a random intercept per task
   because the R repetitions of one task are not independent draws, and
   treating 240 runs per cell as 240 independent observations would overstate
   precision by a wide margin.
2. *Clustered bootstrap*, 5,000 resamples, **resampling tasks with their
   repetitions attached** — never individual runs. Resampling runs would
   reintroduce exactly the independence assumption the random effect exists
   to avoid. The task count is therefore the cluster count, which is why
   §13 raised the set from 27 to 48.

If the two disagree materially, the disagreement is reported, not resolved by
picking one.

**Everything here is descriptive of the data it is given.** It does not know
whether it is looking at a pilot or the full run, and it prints n everywhere
because a figure without its sample size is a claim.
"""

from __future__ import annotations

import json
import math
import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .capture import read_rows
from .run_cell import CELLS

BOOTSTRAP_RESAMPLES = 5000
BOOTSTRAP_SEED = 20260819

# Fixed before any data (protocol §9): `partial` is a fail for the primary
# analysis. The lenient coding is reported alongside as a robustness check,
# never instead.
PRIMARY_CODING = "success_strict"
ROBUSTNESS_CODING = "success_lenient"


def load_scored(path: str) -> pd.DataFrame:
    rows = read_rows(path)
    if not rows:
        raise ValueError(f"{path} has no rows")
    frame = pd.DataFrame(rows)
    frame["architecture"] = frame["cell"].map(lambda c: CELLS[c][0])
    frame["deployment"] = frame["cell"].map(
        lambda c: "local" if CELLS[c][1] == "ollama" else "cloud")
    # Explicit numeric contrasts so the interaction term's sign is a property
    # of this file rather than of whatever order a library sorted strings in.
    #
    # **`routing` is the 1, not `deciding`, and that is load-bearing.** The
    # pre-registered contrast is `(C3-C4) - (C1-C2)` — routing's cloud-to-local
    # gap minus deciding's — so the model's interaction term has to be
    # oriented the same way or the two estimates protocol §9 requires to
    # *agree* come out with opposite signs. The first run of this file did
    # exactly that: the bootstrap read -0.50 and the model +2.46 on identical
    # data, which reads as a contradiction and is a coding convention.
    # Coding `deciding = 1` silently inverts the estimand.
    frame["arch_num"] = (frame["architecture"] == "routing").astype(int)
    frame["depl_num"] = (frame["deployment"] == "cloud").astype(int)
    return frame


# ── the contrast ─────────────────────────────────────────────────────────

def cell_means(frame: pd.DataFrame, coding: str = PRIMARY_CODING
               ) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}
    for cell in sorted(CELLS):
        sub = frame[frame["cell"] == cell]
        values = pd.to_numeric(sub[coding], errors="coerce").dropna()
        out[cell] = {
            "n": int(len(values)),
            "n_tasks": int(sub["task_id"].nunique()),
            "mean": float(values.mean()) if len(values) else float("nan"),
        }
    return out


def compensation(frame: pd.DataFrame, coding: str = PRIMARY_CODING) -> float:
    """(C3 - C4) - (C1 - C2). Signed; no direction is assumed."""
    m = cell_means(frame, coding)
    return ((m["C3"]["mean"] - m["C4"]["mean"])
            - (m["C1"]["mean"] - m["C2"]["mean"]))


# ── estimate 1: mixed-effects logistic ───────────────────────────────────

def mixed_effects(frame: pd.DataFrame, coding: str = PRIMARY_CODING
                  ) -> Dict[str, Any]:
    """`success ~ architecture * deployment + (1 | task)`, LRT on the
    interaction.

    `statsmodels` has no exact mixed-effects *logistic* fit, so this uses
    Binomial GEE with an exchangeable working correlation clustered on task
    — the same correction for within-task dependence, with robust standard
    errors — and reports which estimator actually ran. Saying "mixed-effects
    logistic" while running something else would be the kind of quiet
    substitution this study is built against.
    """
    import statsmodels.api as sm
    import statsmodels.formula.api as smf

    data = frame.copy()
    data["y"] = pd.to_numeric(data[coding], errors="coerce")
    data = data.dropna(subset=["y"])
    if data["y"].nunique() < 2:
        return {"estimator": "none",
                "note": f"outcome is constant ({data['y'].iloc[0]}); "
                        f"no model is identifiable",
                "n": int(len(data))}

    common = dict(groups=data["task_id"],
                  family=sm.families.Binomial(),
                  cov_struct=sm.cov_struct.Exchangeable(),
                  data=data)
    try:
        full = smf.gee("y ~ arch_num * depl_num", **common).fit()
        reduced = smf.gee("y ~ arch_num + depl_num", **common).fit()
    except Exception as exc:                     # pragma: no cover
        return {"estimator": "gee_failed", "note": f"{type(exc).__name__}: {exc}",
                "n": int(len(data))}

    term = "arch_num:depl_num"
    # Score test on the interaction. A likelihood-ratio test is not defined
    # for GEE (it is quasi-likelihood, not a likelihood), so the honest
    # substitute is reported under its own name rather than mislabelled.
    try:
        score = full.model.compare_score_test(reduced)
        p_interaction = float(score["p-value"])
        test_name = "generalised score test (GEE)"
    except Exception:                            # pragma: no cover
        p_interaction = float(full.pvalues.get(term, float("nan")))
        test_name = "Wald z on the interaction term"

    return {
        "estimator": "GEE binomial, exchangeable, clustered on task",
        "n": int(len(data)),
        "n_tasks": int(data["task_id"].nunique()),
        # Same orientation as `compensation()`: positive means routing's
        # cloud-to-local gap exceeds deciding's, i.e. the deciding design
        # compensated. See the coding note in `load_scored`.
        "orientation": "(routing cloud-local) - (deciding cloud-local), "
                       "matching the pre-registered contrast",
        "interaction_logodds": float(full.params.get(term, float("nan"))),
        "interaction_se": float(full.bse.get(term, float("nan"))),
        "interaction_p": p_interaction,
        "interaction_test": test_name,
        "arch_logodds": float(full.params.get("arch_num", float("nan"))),
        "depl_logodds": float(full.params.get("depl_num", float("nan"))),
    }


# ── estimate 2: task-clustered bootstrap ─────────────────────────────────

def bootstrap_contrast(frame: pd.DataFrame, coding: str = PRIMARY_CODING,
                       resamples: int = BOOTSTRAP_RESAMPLES,
                       seed: int = BOOTSTRAP_SEED) -> Dict[str, Any]:
    """95% CI on the compensation contrast, resampling **tasks**.

    A task is drawn with all of its runs in all four cells attached. That is
    what makes the interval honest about the real unit of replication: the
    study has 48 independent tasks, not 960 independent runs.
    """
    data = frame.copy()
    data["y"] = pd.to_numeric(data[coding], errors="coerce")
    data = data.dropna(subset=["y"])

    tasks = data["task_id"].unique()
    by_task = {t: data[data["task_id"] == t] for t in tasks}
    rng = np.random.default_rng(seed)

    estimates: List[float] = []
    for _ in range(resamples):
        picked = rng.choice(tasks, size=len(tasks), replace=True)
        sample = pd.concat([by_task[t] for t in picked], ignore_index=True)
        means = sample.groupby("cell")["y"].mean()
        if not all(c in means for c in CELLS):
            # A resample that happens to miss a cell cannot produce the
            # contrast. Dropped rather than filled in, and counted below so
            # the loss is visible instead of silent.
            continue
        estimates.append(float((means["C3"] - means["C4"])
                               - (means["C1"] - means["C2"])))

    arr = np.array(estimates)
    if arr.size == 0:
        return {"resamples": 0, "note": "no resample produced all four cells"}
    return {
        "point": float(compensation(frame, coding)),
        "ci_low": float(np.percentile(arr, 2.5)),
        "ci_high": float(np.percentile(arr, 97.5)),
        "resamples": int(arr.size),
        "resamples_requested": resamples,
        "n_tasks_resampled": int(len(tasks)),
        "unit": "task (with all repetitions attached)",
    }


# ── the supporting breakdowns ────────────────────────────────────────────

def by_category(frame: pd.DataFrame, coding: str = PRIMARY_CODING
                ) -> pd.DataFrame:
    """The cloud->local gap per category, per architecture (protocol §9).

    Reported so the result says *where* the local deployment is weaker rather
    than asserting one undifferentiated "weaker".
    """
    data = frame.copy()
    data["y"] = pd.to_numeric(data[coding], errors="coerce")
    table = (data.groupby(["category", "architecture", "deployment"])
             .agg(mean=("y", "mean"), n=("y", "size"))
             .reset_index())
    return table


# Categories the per-category band does not apply to, and why.
#
# **`trivial` is exempt.** Added 2026-08-19 after the first pilot, as a stated
# reading of a genuine conflict between two pre-registered sentences rather
# than a loosening of either. §8 requires the local model to show intermediate
# variance "across categories and difficulty"; §7 and §10 give the trivial
# category the opposite job — it is the control, included "where Brain
# shouldn't help", the category both models are *supposed* to pass, and it is
# what makes H1's complexity claim falsifiable: if the design gap does not
# vanish on trivial tasks, the gap is not about complexity.
#
# A band that forces trivial below 0.85 would require making the control hard,
# which destroys the control. The pilot made the conflict concrete: trivial
# came out at 0.875 in **all four cells identically** — the control behaving
# exactly as designed, flagged as a failure.
#
# The exemption is narrow and it is not a free pass: trivial still counts in
# the overall local rate, so a study whose local model passed everything would
# still fail the gate. Only the per-category check skips it.
EXEMPT_FROM_BAND = ("trivial",)

# Categories that fail the band and that the study nonetheless proceeds on,
# each with a dated reason and a statement of what it forfeits.
#
# **This is not a second exemption, and the difference matters.** `trivial` is
# exempt because its pre-registered *role* conflicts with the band — a fact
# that was true before any data existed. Everything here failed the criterion
# on the data, so the criterion is recorded as **failed** and the decision to
# continue is recorded separately, with its cost. `validity_gate` reports
# `criterion_met` and `proceed` as two different booleans, and an exception
# can never turn the first one True. A gate whose failures can be written away
# is not a gate.
GATE_EXCEPTIONS = {
    "clarification": (
        "2026-08-19, after pilot M4 (192 runs, R=1). Local success 0.062 "
        "(1/16), below the 0.15 floor, and unchanged by re-screening four "
        "records against the retained action surface. The floor is not a task "
        "artifact: the local model asks correctly elsewhere in the same pilot "
        "(10 questions across robustness, grounding and trivial), and its "
        "failure mode here is specific and reproducible — it confabulates, "
        "claiming completed actions it has no tool for (\"You are now in your "
        "email client\", \"The music player is now open\") and emitting raw "
        "tool-call JSON as prose. Rewording tasks would not move a "
        "confabulation floor, and iterating until the gate passed would be "
        "the tuning the gate exists to prevent. "
        "WHAT THIS FORFEITS: no claim is made about architecture within the "
        "clarification category at local deployment, because both arms sit at "
        "the floor there and no gradient exists for architecture to interact "
        "with. The category is reported descriptively, with its n. It still "
        "contributes to the overall contrast — 6 of its 8 tasks discriminate "
        "between cells — but that discrimination is deployment, not "
        "architecture."
    ),
}


def validity_gate(frame: pd.DataFrame, coding: str = PRIMARY_CODING,
                  floor: float = 0.15, ceiling: float = 0.85) -> Dict[str, Any]:
    """Protocol §8's gate: does the **local** model show intermediate variance?

    The make-or-break threat in §10. If the local model fails nearly
    everything or passes nearly everything, there is no gradient for
    architecture to interact with and the study collapses to a main effect.

    The 0.15/0.85 band is written here **before any full run**, so the gate is
    a criterion rather than a rationalisation of whatever came out. It is
    checked overall and per category, because an overall rate in band can hide
    a category at the floor and another at the ceiling — except for the
    categories in `EXEMPT_FROM_BAND`, which have a documented reason above.
    """
    data = frame.copy()
    data["y"] = pd.to_numeric(data[coding], errors="coerce")
    local = data[data["deployment"] == "local"].dropna(subset=["y"])
    overall = float(local["y"].mean()) if len(local) else float("nan")

    per_cat = {}
    for cat, sub in local.groupby("category"):
        rate = float(sub["y"].mean())
        exempt = cat in EXEMPT_FROM_BAND
        per_cat[cat] = {"rate": rate, "n": int(len(sub)),
                        "exempt": exempt,
                        "in_band": True if exempt
                                   else bool(floor <= rate <= ceiling)}

    out_of_band = sorted(c for c, v in per_cat.items() if not v["in_band"])
    overall_ok = (bool(floor <= overall <= ceiling)
                  if not math.isnan(overall) else False)
    undocumented = [c for c in out_of_band if c not in GATE_EXCEPTIONS]

    return {
        "band": [floor, ceiling],
        "local_overall": overall,
        "local_overall_in_band": overall_ok,
        "per_category": per_cat,
        "categories_out_of_band": out_of_band,
        "categories_exempt": list(EXEMPT_FROM_BAND),
        # Two booleans, never one. `criterion_met` is what the pre-registered
        # gate actually asked; `proceed` is the decision taken, which an
        # exception may justify but never disguise.
        "criterion_met": overall_ok and not out_of_band,
        "proceed": overall_ok and not undocumented,
        "exceptions_invoked": {c: GATE_EXCEPTIONS[c] for c in out_of_band
                               if c in GATE_EXCEPTIONS},
        "undocumented_failures": undocumented,
        "n_local_runs": int(len(local)),
        "n_local_tasks": int(local["task_id"].nunique()),
    }


# ── the report ───────────────────────────────────────────────────────────

def analyze(scored_path: str, out_path: str = "", *,
            resamples: int = BOOTSTRAP_RESAMPLES) -> Dict[str, Any]:
    frame = load_scored(scored_path)
    cells_present = sorted(frame["cell"].unique())

    report: Dict[str, Any] = {
        "source": scored_path,
        "n_runs": int(len(frame)),
        "n_tasks": int(frame["task_id"].nunique()),
        "cells_present": cells_present,
        "complete_2x2": cells_present == sorted(CELLS),
        "primary_coding": PRIMARY_CODING,
        "cell_means": cell_means(frame),
        "unjudged_rows": int((frame["success"] == "unjudged").sum()),
        "judge_error_rows": int((frame["success"] == "judge_error").sum()),
        "degraded_rows": int(frame["degradation"].map(bool).sum()),
        "decision_accuracy": {
            c: float(frame[frame["cell"] == c]["decision_correct"].mean())
            for c in cells_present},
        "ask_origin": (frame.groupby(["cell", "ask_origin"]).size()
                       .unstack(fill_value=0).to_dict("index")),
        "validity_gate": validity_gate(frame),
    }

    if report["complete_2x2"]:
        report["compensation_point"] = compensation(frame)
        report["compensation_lenient"] = compensation(frame, ROBUSTNESS_CODING)
        report["bootstrap"] = bootstrap_contrast(frame, resamples=resamples)
        report["mixed_effects"] = mixed_effects(frame)
    else:
        # The contrast is not defined without all four cells, and a partial
        # answer here would be worse than none.
        report["compensation_point"] = None
        report["note"] = (f"cells present: {cells_present}. The interaction "
                          f"contrast needs all four; nothing is estimated.")

    report["by_category"] = json.loads(by_category(frame).to_json(orient="records"))

    if out_path:
        os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".",
                    exist_ok=True)
        with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(report, fh, indent=2, ensure_ascii=False)
    return report


def print_report(report: Dict[str, Any]) -> None:
    print(f"\n{report['n_runs']} runs over {report['n_tasks']} tasks, "
          f"cells {report['cells_present']}")
    if report["unjudged_rows"] or report["judge_error_rows"]:
        print(f"  UNSCORED: {report['unjudged_rows']} unjudged, "
              f"{report['judge_error_rows']} judge errors")
    print(f"  degraded rows: {report['degraded_rows']}")

    print("\n  cell   success   decision   n    tasks")
    for cell, m in report["cell_means"].items():
        acc = report["decision_accuracy"].get(cell)
        acc_s = f"{acc:.3f}" if acc is not None else "  -  "
        print(f"  {cell}    {m['mean']:.3f}     {acc_s}    "
              f"{m['n']:<4d} {m['n_tasks']}")

    gate = report["validity_gate"]
    verdict = "criterion MET" if gate["criterion_met"] else "criterion NOT MET"
    if not gate["criterion_met"]:
        n = len(gate["exceptions_invoked"])
        verdict += (f", proceeding on {n} documented exception"
                    f"{'' if n == 1 else 's'}" if gate["proceed"]
                    else ", DO NOT PROCEED")
    print(f"\n  validity gate ({gate['band'][0]}-{gate['band'][1]}): {verdict}")
    print(f"    local overall {gate['local_overall']:.3f} "
          f"over {gate['n_local_runs']} runs / {gate['n_local_tasks']} tasks")
    for cat, v in sorted(gate["per_category"].items()):
        mark = " " if v["in_band"] else "!"
        note = "  (exempt: the control)" if v.get("exempt") else ""
        print(f"    {mark} {cat:14s} {v['rate']:.3f}  (n={v['n']}){note}")

    if report.get("compensation_point") is None:
        print(f"\n  {report.get('note', '')}")
        return

    b = report["bootstrap"]
    print(f"\n  compensation (C3-C4)-(C1-C2) = {report['compensation_point']:+.4f}")
    print(f"    95% CI [{b['ci_low']:+.4f}, {b['ci_high']:+.4f}]  "
          f"({b['resamples']} resamples, unit = {b['unit']})")
    print(f"    lenient coding: {report['compensation_lenient']:+.4f}")
    me = report["mixed_effects"]
    if "interaction_logodds" in me:
        print(f"    {me['estimator']}")
        print(f"    interaction {me['interaction_logodds']:+.4f} "
              f"(se {me['interaction_se']:.4f}), p={me['interaction_p']:.4f} "
              f"[{me['interaction_test']}]")
    else:
        print(f"    model: {me.get('note', me.get('estimator'))}")


__all__ = ["analyze", "print_report", "load_scored", "compensation",
           "bootstrap_contrast", "mixed_effects", "validity_gate",
           "by_category", "cell_means"]
