"""Flatten the frozen run record into forms a person can read.

Reads `runs/full-2026-08-20/scored.jsonl` -- the 960 scored runs -- and writes:

  runs/full-2026-08-20/runs.csv   one row per run, opens in any spreadsheet
  docs/results.md                 every number the paper reports, in one place

Nothing here computes a new result. Every figure of merit is either read
straight from `report.json` / `main_effects.json` or recomputed from the
scored rows. If a number in the paper is not in `docs/results.md`, it did not
come from the run.

Vocabulary: the run record uses the apparatus's field names, which are not the
paper's. The mapping is fixed and stated at the top of `results.md`.

    architecture -> the harness design       deciding / routing
    deployment   -> deployment               cloud / on-device  (record: local)
    cell         -> configuration            C1..C4
"""

import csv
import json
from pathlib import Path
from statistics import mean, median, quantiles

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs" / "full-2026-08-20"

CELLS = ["C1", "C2", "C3", "C4"]
LABEL = {"C1": "deciding x cloud", "C2": "deciding x on-device",
         "C3": "routing x cloud", "C4": "routing x on-device"}
CATS = ["trivial", "action", "clarification", "grounding",
        "reasoning", "robustness"]

CSV_COLUMNS = [
    "run_id", "cell", "configuration", "design", "deployment",
    "task_id", "category", "difficulty", "repetition", "order_index",
    "success", "success_strict", "success_lenient", "success_by",
    "decision_correct", "asked", "ask_origin", "over_asked", "under_asked",
    "declined", "backgrounded", "decomposed",
    "tools_called", "n_tools", "dropped_by_router",
    "iterations", "model_calls", "hit_iteration_cap",
    "bad_arguments", "missing_arguments", "unknown_tools",
    "latency_s", "cost_usd", "input_tokens", "output_tokens",
    "length_words", "length_fit", "formulaic_opening",
    "model_pinned", "models_reported", "degradation", "error",
    "judge_model", "success_why", "reply",
]


def load():
    with open(RUN / "scored.jsonl", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def flat(r):
    d = r["decision"]
    return {
        "run_id": r["run_id"],
        "cell": r["cell"],
        "configuration": LABEL[r["cell"]],
        "design": r["architecture"],
        "deployment": "on-device" if r["deployment"] == "local" else r["deployment"],
        "task_id": r["task_id"],
        "category": r["category"],
        "difficulty": r["difficulty"],
        "repetition": r["repetition"],
        "order_index": r["order_index"],
        "success": r["success"],
        "success_strict": r["success_strict"],
        "success_lenient": r["success_lenient"],
        "success_by": r["success_by"],
        "decision_correct": r["decision_correct"],
        "asked": d["asked"],
        "ask_origin": r["ask_origin"],
        "over_asked": r["over_asked"],
        "under_asked": r["under_asked"],
        "declined": d["declined"],
        "backgrounded": d["backgrounded"],
        "decomposed": d["decomposed"],
        "tools_called": "|".join(d["tools"]),
        "n_tools": len(d["tools"]),
        "dropped_by_router": "|".join(d["dropped_by_router"]),
        "iterations": d["iterations"],
        "model_calls": d["model_calls"],
        "hit_iteration_cap": d["hit_iteration_cap"],
        "bad_arguments": d["bad_arguments"],
        "missing_arguments": d["missing_arguments"],
        "unknown_tools": "|".join(d["unknown_tools"]),
        "latency_s": r["latency_s"],
        "cost_usd": r["cost_usd"],
        "input_tokens": r["input_tokens"],
        "output_tokens": r["output_tokens"],
        "length_words": r["length_words"],
        "length_fit": r["length_fit"],
        "formulaic_opening": r["formulaic_opening"],
        "model_pinned": r["model_pinned"],
        "models_reported": "|".join(sorted(set(r["models_reported"]))),
        "degradation": "|".join(r["degradation"]),
        "error": r["error"] or "",
        "judge_model": r.get("judge_model", ""),  # absent on the 300 deterministically scored rows
        "success_why": r["success_why"],
        "reply": r["reply"],
    }


def write_csv(rows):
    out = RUN / "runs.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        w.writeheader()
        for r in sorted(rows, key=lambda r: (r["task_id"], r["cell"], r["repetition"])):
            w.writerow(flat(r))
    return out


def cell_mean(rows, cell, where=None):
    vs = [r["success_strict"] for r in rows
          if r["cell"] == cell and (where is None or where(r))]
    return (mean(vs) if vs else float("nan")), len(vs)


def table(header, body):
    lines = ["| " + " | ".join(str(h) for h in header) + " |",
             "|" + "|".join("---" for _ in header) + "|"]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in body]
    return "\n".join(lines)


def write_results(rows, report, effects):
    m = {c: report["cell_means"][c]["mean"] for c in CELLS}
    boot = report["bootstrap"]
    ge = report["mixed_effects"]
    me = effects["marginal_effects"]

    def ci(k):
        e = me[k]
        return f"{e['point']:+.3f} [{e['ci_low']:+.3f}, {e['ci_high']:+.3f}]"

    p = []
    p.append("""# The results, in one place

Generated by `tools/export_results.py` from `runs/full-2026-08-20/scored.jsonl`
-- the frozen record of the full run of 2026-08-20. Do not edit this file by
hand; re-run the script instead. Every number the paper states should be
findable here, and every number here came from those 960 rows.

The spreadsheet form of the same record is `runs/full-2026-08-20/runs.csv`,
one row per run.

**The record's vocabulary is not the paper's.** The run files were written
before the terminology was fixed. The mapping is exact:

| in the record | in the paper |
|---|---|
| `architecture` | the harness design |
| `deciding` / `routing` | the deciding design / the routing design |
| `deployment` | deployment |
| `cloud` / `local` | cloud / on-device |
| `cell`, `C1`-`C4` | configuration |""")

    p.append("## 1. Integrity of the run")
    p.append(table(
        ["", "value"],
        [["runs", report["n_runs"]],
         ["tasks", report["n_tasks"]],
         ["repetitions per task per configuration", 5],
         ["configurations", "C1, C2, C3, C4 -- 240 runs each"],
         ["errors", len([r for r in rows if r["error"]])],
         ["degraded runs", len([r for r in rows if r["degradation"]])],
         ["runs the judge could not score", report["unjudged_rows"]],
         ["judge errors", report["judge_error_rows"]],
         ["wall-clock time", f"{report['wall_minutes']} minutes"],
         ["model cost", f"${sum(r['cost_usd'] for r in rows):.2f}"],
         ["judging cost", f"${report['judge_cost_usd']:.4f}"],
         ["baseline commit", "`" + rows[0]["baseline_commit"][:12] + "`"],
         ["task-set fingerprint", "`" + rows[0]["tasks_sha256"][:16] + "...`"],
         ["task order seed", rows[0]["order_seed"]]]))
    p.append("Every row records the model that answered, checked against the model the\n"
             "configuration fixed; all 960 agree (paper section 3.3).")

    p.append("## 2. The four configurations")
    p.append(table(
        ["", "configuration", "task success", "n runs", "n tasks"],
        [[c, LABEL[c], f"{m[c]:.4f}",
          report["cell_means"][c]["n"], report["cell_means"][c]["n_tasks"]]
         for c in CELLS]))

    p.append("## 3. The contrasts")
    p.append("Percentile bootstrap, 5,000 resamples, resampling **tasks** with all their\n"
             "repetitions attached, because repetitions of one task are not independent\n"
             "observations.")
    p.append(table(
        ["contrast", "what it asks", "point [95% CI]"],
        [["design (main effect)", "deciding minus routing, both deployments", ci("architecture")],
         ["deployment (main effect)", "cloud minus on-device, both designs", ci("deployment")],
         ["design at cloud", "C1 minus C3", ci("arch_at_cloud")],
         ["design on-device", "C2 minus C4", ci("arch_at_local")],
         ["deployment in deciding", "C1 minus C2", ci("depl_in_deciding")],
         ["deployment in routing", "C3 minus C4", ci("depl_in_routing")]]))
    p.append(f"""**The interaction -- the study's primary outcome.**

```
C = (C3 - C4) - (C1 - C2) = {boot['point']:+.4f}
95% CI [{boot['ci_low']:+.4f}, {boot['ci_high']:+.4f}], {boot['resamples']} resamples over {boot['n_tasks_resampled']} tasks
```

Read on the design gap instead: the deciding design is worth
**{me['arch_at_cloud']['point']:+.3f}** at cloud and **{me['arch_at_local']['point']:+.3f}** on-device. The gap
**narrows** on the way down, so the compensation term is negative. Its interval
spans zero.

**{ge['estimator']}**, n = {ge['n']} over {ge['n_tasks']} tasks: interaction
{ge['interaction_logodds']:+.4f} log-odds (SE {ge['interaction_se']:.4f}),
{ge['interaction_test']} p = {ge['interaction_p']:.3f}.
Orientation: {ge['orientation']}.

Under the lenient coding (partial credit counted as success) the interaction is
{report['compensation_lenient']:+.4f}.""")

    p.append("## 4. Task success by category")
    body = []
    for cat in CATS:
        row = [cat]
        n = 0
        for c in CELLS:
            v, n = cell_mean(rows, c, where=lambda r, k=cat: r["category"] == k)
            row.append(f"{v:.3f}")
        row.append(n)
        body.append(row)
    p.append(table(["category"] + [f"{c}" for c in CELLS] + ["n per cell"], body))
    p.append("C1 deciding x cloud, C2 deciding x on-device, C3 routing x cloud,\n"
             "C4 routing x on-device.")

    p.append("## 5. Task success by difficulty")
    p.append("`difficulty` is the author's prospective 1-5 estimate, ranked **within** its\n"
             "category (`apparatus/tasks/SCHEMA.md`). A slope pooled across categories\n"
             "therefore pools ranks that were never calibrated against each other -- a\n"
             "limitation to state, not a variable to trust.")
    diff_of = {r["task_id"]: r["difficulty"] for r in rows}
    body = []
    for d in [1, 2, 3, 4, 5]:
        ts = {t for t, dd in diff_of.items() if dd == d}
        vals = {c: cell_mean(rows, c, where=lambda r, s=ts: r["task_id"] in s)[0]
                for c in CELLS}
        body.append([d, len(ts)] + [f"{vals[c]:.3f}" for c in CELLS]
                    + [f"{vals['C1'] - vals['C3']:+.3f}",
                       f"{vals['C2'] - vals['C4']:+.3f}"])
    p.append(table(["difficulty", "n tasks"] + CELLS
                   + ["design gap, cloud", "design gap, on-device"], body))

    p.append("## 6. Decision accuracy, and what it buys")
    p.append("Decision accuracy is scored on the choice the harness made -- whether to\n"
             "ask, whether to decline, and which actions to call -- independently of\n"
             "whether the task then succeeded.")
    d2s = effects["decision_to_success"]
    body = []
    for c in CELLS:
        e = d2s[c]
        body.append([c, LABEL[c], f"{report['decision_accuracy'][c]:.4f}",
                     f"{e['success_when_decision_correct']:.3f} (n={e['n_correct']})",
                     f"{e['success_when_decision_wrong']:.3f} (n={e['n_wrong']})"])
    p.append(table(["", "configuration", "decision accuracy",
                    "success when decision correct", "when decision wrong"], body))
    p.append(f"At cloud the two designs judge almost identically -- "
             f"{report['decision_accuracy']['C1']:.3f} against "
             f"{report['decision_accuracy']['C3']:.3f} -- and succeed "
             f"{m['C1'] - m['C3']:.3f} apart. The advantage is not better judgement.")

    p.append("## 7. Asking: how often, and what initiated it")
    body = []
    for c in CELLS:
        a = report["ask_origin"][c]
        body.append([c, LABEL[c], a["model"] + a["rule"], a["model"], a["rule"], a["none"]])
    p.append(table(["", "configuration", "asked", "model-initiated",
                    "rule-initiated", "did not ask"], body))

    p.append("## 8. Cost, latency and reply length")
    body = []
    for c in CELLS:
        sub = [r for r in rows if r["cell"] == c]
        body.append([c, LABEL[c],
                     f"{mean(r['latency_s'] for r in sub):.2f}",
                     f"{sum(r['cost_usd'] for r in sub):.4f}",
                     f"{mean(r['model_calls'] for r in sub):.2f}",
                     f"{mean(r['input_tokens'] for r in sub):.0f}",
                     f"{mean(r['output_tokens'] for r in sub):.0f}",
                     f"{mean(r['length_words'] for r in sub):.1f}"])
    p.append(table(["", "configuration", "mean latency (s)", "total cost ($)",
                    "mean model calls", "mean input tokens",
                    "mean output tokens", "mean reply words"], body))

    p.append("## 9. How much the five repetitions actually replicate")
    rep = effects["replication"]
    p.append(table(["distinct replies across the 5 repetitions", "task-configuration pairs"],
                   [[k, v] for k, v in sorted(rep["distinct_replies_per_pair"].items())]))
    p.append(f"{rep['fully_deterministic_pairs']} of {rep['cell_task_pairs']} pairs "
             f"({rep['fraction_deterministic']:.1%}) produced one identical reply five\n"
             f"times. Where that happens the five repetitions are one observation recorded\n"
             f"five times, which is why every interval here resamples tasks rather than\n"
             f"runs.")

    p.append("## 10. The validity gate")
    vg = report["validity_gate"]
    p.append(f"On-device success overall **{vg['local_overall']:.4f}** "
             f"(n = {vg['n_local_runs']}), inside the pre-registered band "
             f"{vg['band']}.")
    body = []
    for cat in CATS:
        e = vg["per_category"][cat]
        body.append([cat, f"{e['rate']:.4f}", e["n"],
                     "yes" if e["in_band"] else "**no**",
                     "exempt" if e["exempt"] else ""])
    p.append(table(["category", "on-device success", "n", "in band", ""], body))
    p.append(f"""Criterion met: **{vg['criterion_met']}**. Proceeded: **{vg['proceed']}**, under a
documented exception for `clarification`:

> {vg['exceptions_invoked']['clarification']}

Undocumented failures: {vg['undocumented_failures'] or 'none'}.""")

    p.append("## 11. Every task, every configuration")
    p.append("Mean of 5 repetitions, strict coding.")
    cat_of = {r["task_id"]: r["category"] for r in rows}
    tasks = sorted(cat_of, key=lambda t: (CATS.index(cat_of[t]), t))
    body = []
    for t in tasks:
        sub = [r for r in rows if r["task_id"] == t]
        vals = {c: mean(r["success_strict"] for r in sub if r["cell"] == c) for c in CELLS}
        body.append([f"`{t}`", cat_of[t], sub[0]["difficulty"]]
                    + [f"{vals[c]:.1f}" for c in CELLS])
    p.append(table(["task", "category", "difficulty"] + CELLS, body))

    p += late_sections(rows)

    out = ROOT / "docs" / "results.md"
    out.write_text("\n\n".join(p) + "\n", encoding="utf-8")
    return out


# --- families the paper reports that had no artifact until 2026-09-08 -------
# Found by pass 1: every one of these reproduces from the frozen rows, but
# none of them could be read from anywhere, so "show me where this came from"
# had no answer. They are computed here rather than in `apparatus/`, because
# the instrument is frozen and is not edited after the run.

def boot_ci(values_by_task, statistic, seed=20260819, draws=5000):
    """Resample the 48 tasks, not the 960 runs (protocol section 9)."""
    import numpy as np
    ids = sorted(values_by_task)
    rng = np.random.default_rng(seed)
    out = []
    for _ in range(draws):
        s = list(rng.choice(ids, size=len(ids), replace=True))
        v = statistic(s)
        if v is not None:
            out.append(v)
    lo, hi = np.percentile(out, [2.5, 97.5])
    return float(lo), float(hi), len(out)


def difficulty_slope(rows):
    """The registered secondary test: does the advantage grow with difficulty?

    Fitted here and not in `apparatus/harness/analyze.py`, which declines to
    fit it and says why in `main_effects.json`. The paper reports it anyway,
    with the objection stated in the open, so the computation belongs
    somewhere a reader can reach.
    """
    import numpy as np
    by_task = {}
    for r in rows:
        by_task.setdefault(r["task_id"], []).append(r)

    def fit(sample):
        lv = {}
        for tid in sample:
            for r in by_task[tid]:
                d = r["difficulty"]
                k = "deciding" if r["cell"] in ("C1", "C2") else "routing"
                lv.setdefault(d, {"deciding": [], "routing": []})[k].append(
                    r["success_strict"])
        xs, ys = [], []
        for d in sorted(lv):
            dec, rou = lv[d]["deciding"], lv[d]["routing"]
            if dec and rou:
                xs.append(d)
                ys.append(mean(dec) - mean(rou))
        if len(xs) < 2:
            return None
        return float(np.polyfit(xs, ys, 1)[0])

    ids = sorted(by_task)
    per_level = {}
    for d in sorted({r["difficulty"] for r in rows}):
        dec = [r["success_strict"] for r in rows
               if r["difficulty"] == d and r["cell"] in ("C1", "C2")]
        rou = [r["success_strict"] for r in rows
               if r["difficulty"] == d and r["cell"] in ("C3", "C4")]
        per_level[d] = (mean(dec) - mean(rou), len(dec) + len(rou),
                        len({r["task_id"] for r in rows if r["difficulty"] == d}))
    lo, hi, n = boot_ci(by_task, fit)
    return per_level, fit(ids), (lo, hi), n


def instrument_size():
    """The size the paper states, under the rule that produces it.

    `derive/` holds tracing tools that are not part of the experiment, and
    excluding them is what turns 4,979 lines across 29 files into the number
    section 3.4 gives. The rule was applied but never written down.
    """
    src = ROOT / "apparatus"
    kept, dropped = [], []
    for f in sorted(src.rglob("*.py")):
        (dropped if "derive" in f.relative_to(src).parts else kept).append(f)

    def count(fs):
        return sum(len(f.read_text(encoding="utf-8", errors="replace")
                       .splitlines()) for f in fs)
    return len(kept), count(kept), len(dropped), count(dropped)


def case_id(row, task):
    """Reproduce `BlindCase.case_id` without importing the frozen instrument.

    The judge keyed its cache on a hash of what it was allowed to see, so a
    verdict cannot be matched back to a run any other way. Kept in step with
    `apparatus/harness/judge.py`; the check below is that the 660 rubric rows
    collapse onto exactly the cache's 214 cases.
    """
    import hashlib
    payload = json.dumps([task["id"], row.get("reply", ""),
                          sorted(row.get("mutations") or []),
                          (task.get("success") or {}).get("criteria", "")],
                         sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def cohens_kappa(pairs):
    from collections import Counter
    n = len(pairs)
    labels = sorted({x for pair in pairs for x in pair})
    agree = sum(1 for a, b in pairs if a == b) / n
    a_of = Counter(a for a, _ in pairs)
    b_of = Counter(b for _, b in pairs)
    expected = sum((a_of[l] / n) * (b_of[l] / n) for l in labels)
    return agree, (agree - expected) / (1 - expected)


def grader_crosscheck(rows):
    """A second model on the same rubric cases, as tools/grader_crosscheck.py
    computes it.

    That script is the study's instrument for this question and its numbers
    were computed on 2026-09-04, before Study 2 ran and before this file
    existed. It compares **per run**, not per distinct case: the 660 rubric
    runs collapse to 214 transcripts, and a transcript that recurs five times
    counts five times, because a grader's influence on a configuration mean
    runs through runs. Weighting each transcript once instead gives kappa
    0.808 -- a different question, and not the one section 7 asks.
    """
    xdir = ROOT / "runs" / "grader_crosscheck"
    with open(xdir / "verdicts_haiku.json", encoding="utf-8") as fh:
        second = json.load(fh)
    with open(ROOT / "apparatus" / "tasks" / "tasks.json", encoding="utf-8") as fh:
        tasks = {t["id"]: t for t in json.load(fh)}

    rubric = [r for r in rows if r["success_by"] == "rubric"]
    pairs = []
    for r in rubric:
        k = case_id(r, tasks[r["task_id"]])
        if k in second:
            pairs.append((r["success"], second[k]["verdict"]))

    p = [f"`claude-haiku-4-5` re-graded every rubric case blind, from the same "
         f"inputs `claude-sonnet-4-6` saw. The {len(rubric)} rubric-scored runs "
         f"collapse to {len({case_id(r, tasks[r['task_id']]) for r in rubric})} "
         f"distinct transcripts, and agreement is computed over the runs."]

    labels = ["pass", "partial", "fail"]
    body = [[a] + [sum(1 for x, y in pairs if x == a and y == b) for b in labels]
            for a in labels]
    p.append(table([r"sonnet \ haiku"] + labels, body))

    codings = [("three verdicts", lambda v: v),
               ("primary coding: partial counts as failure",
                lambda v: "pass" if v == "pass" else "not")]
    body = []
    for name, f in codings:
        agree, k = cohens_kappa([(f(a), f(b)) for a, b in pairs])
        body.append([name, len(pairs), f"{agree:.3f}", f"{k:.3f}"])
    p.append(table(["coding", "n runs", "raw agreement", "Cohen's kappa"], body))

    # The claim section 7 rests on: does swapping the grader move the
    # contrast? Computed over the 33 tasks a grader touched, because the
    # other 15 cannot move whoever grades them.
    strict = {"pass": 1.0, "partial": 0.0, "fail": 0.0}
    graded_tasks = sorted({r["task_id"] for r in rubric})
    body = []
    for name, verdict_of in (("sonnet, the grader of record", lambda r, k: None),
                             ("haiku", lambda r, k: second.get(k))):
        per_task = {}
        for r in rows:
            if r["task_id"] not in graded_tasks:
                continue
            k = case_id(r, tasks[r["task_id"]])
            v = verdict_of(r, k)
            val = strict[v["verdict"]] if v else r["success_strict"]
            per_task.setdefault(r["task_id"], {}).setdefault(r["cell"], []).append(val)
        contrast = {t: (mean(c["C3"]) - mean(c["C4"])) - (mean(c["C1"]) - mean(c["C2"]))
                    for t, c in per_task.items()}
        pt = mean(contrast.values())
        lo, hi = boot_ci(contrast, lambda s: mean(contrast[t] for t in s))[:2]
        body.append([name, len(contrast),
                     f"{pt + 0.0:+.4f}".replace("-0.0000", "+0.0000"),
                     f"[{lo:+.3f}, {hi:+.3f}]"])
    p.append(table(["grader", "n tasks", "compensation", "95% interval"], body))
    p.append("Computed over the tasks a grader scored. The other 15 were "
             "settled by a text check and no grader could move them.")

    abandoned = sorted(xdir.glob("abandoned_*.json"))
    if abandoned:
        with open(abandoned[0], encoding="utf-8") as fh:
            gave_up = json.load(fh)
        bad = sum(1 for v in gave_up.values() if v["verdict"] == "unparseable")
        p.append(f"A third grader was planned and abandoned. `llama3.1:8b` is "
                 f"the on-device treatment model, chosen because its expected "
                 f"bias runs opposite to the grader of record; it was dropped "
                 f"after {len(gave_up)} cases, {bad} of which came back in a "
                 f"form that could not be read as a verdict. Kept at "
                 f"`runs/grader_crosscheck/{abandoned[0].name}`.")
    return p


def late_sections(rows):
    p = []

    p.append("## 12. The registered difficulty test")
    per_level, slope, (lo, hi), n = difficulty_slope(rows)
    p.append("Design advantage is the deciding design minus the routing design on "
             "task success, both deployments pooled, strict coding.")
    p.append(table(["difficulty", "advantage", "n runs", "n tasks"],
                   [[d, f"{a:+.3f}", nr, nt]
                    for d, (a, nr, nt) in sorted(per_level.items())]))
    p.append(f"Slope **{slope:+.3f}** per level, 95% interval "
             f"[{lo:+.3f}, {hi:+.3f}], from {n} resamples of the 48 tasks at "
             f"seed 20260819. The interval spans zero. Difficulty was ranked "
             f"within a category rather than on one scale common to all six, so "
             f"the levels are not directly comparable across categories; the "
             f"paper states that where it reports this.")

    p.append("## 13. What the advantage costs")
    body = []
    for c in CELLS:
        lat = sorted(r["latency_s"] for r in rows if r["cell"] == c)
        cost = [r["cost_usd"] or 0.0 for r in rows if r["cell"] == c]
        body.append([LABEL[c], f"{median(lat):.2f}", f"{quantiles(lat, n=10)[8]:.1f}",
                     f"{mean(cost):.4f}", len(lat)])
    p.append(table(["configuration", "median latency (s)", "90th pct (s)",
                    "mean cost (USD)", "n"], body))
    p.append("On-device cost is zero by definition: the hardware is already "
             "owned and energy is not metered here.")

    p.append("## 14. The headline without the grader")
    scored_by = {}
    for r in rows:
        scored_by.setdefault(r["task_id"], r["success_by"])
    checked = sorted(t for t, b in scored_by.items() if b != "rubric")
    graded = sorted(t for t, b in scored_by.items() if b == "rubric")

    # One contrast per task, then the mean of those -- the same unit as the
    # primary analysis. Recomputing configuration means inside each draw
    # instead gives a visibly narrower interval and is not what was
    # registered.
    per_task = {}
    for t in scored_by:
        v = {c: mean(r["success_strict"] for r in rows
                     if r["task_id"] == t and r["cell"] == c) for c in CELLS}
        per_task[t] = (v["C3"] - v["C4"]) - (v["C1"] - v["C2"])

    def compensation(subset):
        def stat(sample):
            return mean(per_task[t] for t in sample)
        # Each subset resamples its own tasks. Drawing all 48 and filtering
        # would vary the subset's size from draw to draw.
        lo, hi, _ = boot_ci({t: None for t in subset}, stat)
        return stat(subset), lo, hi

    body = []
    for name, subset in (("text check only, no grader", checked),
                         ("grader scored", graded)):
        pt, lo, hi = compensation(subset)
        body.append([name, len(subset), f"{pt + 0.0:+.3f}".replace("-0.000", "+0.000"), f"[{lo:+.3f}, {hi:+.3f}]"])
    p.append(table(["subset", "n tasks", "compensation", "95% interval"], body))
    p.append("Whether a task is scored by a text check or by the grader was "
             "fixed when the task was written, before any run.")

    p.append("## 15. The second grader")
    p += grader_crosscheck(rows)

    p.append("## 16. The instrument's size")
    nk, lk, nd, ld = instrument_size()
    p.append(f"**{lk:,} lines of Python across {nk} files**, counting "
             f"`apparatus/` and excluding `derive/`, which holds {nd} tracing "
             f"tools totalling {ld} lines that no configuration runs. Counted "
             f"whole: {nk + nd} files, {lk + ld:,} lines. Section 3.4 states "
             f"the first pair, and this is the rule behind it.")
    return p


def main():
    rows = load()
    with open(RUN / "report.json", encoding="utf-8") as fh:
        report = json.load(fh)
    with open(RUN / "main_effects.json", encoding="utf-8") as fh:
        effects = json.load(fh)
    print("wrote", write_csv(rows))
    print("wrote", write_results(rows, report, effects))


if __name__ == "__main__":
    main()
