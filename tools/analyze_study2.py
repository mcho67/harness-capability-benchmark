"""Study 2 — the capability sweep and the ablation, analysed.

Every quantity here was fixed in `docs/protocol_ext.md` before the data
existed, under tag `study2-registered`. Nothing in this file decides what to
measure; it carries out a plan that is already on record.

**The estimator is Study 1's.** On a design with the same repetition count in
every configuration, the pre-registered contrast is the mean of one number
per task, and the interval is the percentile bootstrap of that mean over the
48-task unit. That identity is asserted against
`runs/full-2026-08-20/report.json` before anything else runs, so a drift in
the estimator stops this file rather than quietly changing its answers.

**Study 1's cloud runs are the cloud half of every pair.** Only the on-device
side of the sweep has been collected so far, so each new on-device model is
paired against C1 and C3 — the same cloud baseline, unchanged and not re-run.
Adding cloud models later adds pairs; it does not change the ones below.

**Repetition counts differ and that is fine.** Study 1 ran five repetitions
and Study 2 runs three. Both are balanced within a configuration, so a task
mean is a task mean either way, and the unit of replication is the task in
both.

Usage:  python tools/analyze_study2.py [--coding success_strict]
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

STUDY1 = ROOT / "runs" / "full-2026-08-20" / "scored.jsonl"
REPORT = ROOT / "runs" / "full-2026-08-20" / "report.json"
STUDY2 = ROOT / "runs" / "study2"
OUT = ROOT / "runs" / "study2_analysis.json"

RESAMPLES = A.BOOTSTRAP_RESAMPLES
SEED = A.BOOTSTRAP_SEED
MARGIN = 0.15                      # protocol_ext §2, fixed before the data

# Study 1's own configurations, in the paper's vocabulary.
CLOUD_DECIDING, CLOUD_ROUTING = "C1", "C3"
DEV_DECIDING, DEV_ROUTING = "C2", "C4"

# Two cloud baselines. Study 1 had one, which meant "cloud" and "that model"
# were the same column of the data and no analysis could separate them. Every
# on-device model is now paired against both, and a contrast that changes when
# the baseline changes is a fact about the baseline rather than about
# compensation.
CLOUD_BASELINES = {
    "sonnet": (CLOUD_DECIDING, CLOUD_ROUTING),
    "haiku": ("deciding@claude-haiku-4-5-20251001",
              "routing@claude-haiku-4-5-20251001"),
}

# The on-device ladder, weakest first. `llama3.1:8b` is Study 1's and its rows
# come from Study 1, not from `runs/study2/`.
LADDER = ["qwen2.5-1.5b", "qwen2.5-3b", "llama3.2-3b",
          "qwen2.5-7b", "mistral-7b"]

ABLATIONS = ["deciding-no-iteration", "deciding-no-multi-dispatch",
             "deciding-no-ask"]


def load(coding: str) -> pd.DataFrame:
    """Study 1 and Study 2 in one frame, keyed by configuration name.

    **Refuses to return a partially scored configuration.** When the grader
    cannot reach the provider it records `judge_error` on the row, and
    `STRICT` has no entry for that, so the row's coding is absent rather than
    wrong. Averaging over what remains silently reports the subset of tasks
    that never needed a grader — the deterministic ones, which are the easy
    ones. That produced a 7B on-device model at 1.000 task success once, and
    the number looked like a result rather than a bug. Nothing is computed
    from an incomplete configuration again.
    """
    frames = [A.load_scored(str(STUDY1))]
    incomplete = []
    for path in sorted(STUDY2.glob("*.scored.jsonl")):
        frame = pd.read_json(path, lines=True)
        frame["cell"] = path.name.replace(".scored.jsonl", "")
        missing = int(pd.to_numeric(frame[coding], errors="coerce").isna().sum())
        if missing:
            reasons = (frame.loc[pd.to_numeric(frame[coding], errors="coerce").isna(),
                                 "success"].astype(str).value_counts().to_dict())
            incomplete.append((frame["cell"].iloc[0], missing, len(frame), reasons))
        frames.append(frame)

    if incomplete:
        lines = ["configurations are not fully scored, so no contrast can be "
                 "computed from them:"]
        for cell, missing, total, reasons in incomplete:
            lines.append(f"  {cell}: {missing} of {total} rows have no "
                         f"{coding} — {reasons}")
        lines.append("\nRe-run `python tools/run_study2.py --score`. Verdicts "
                     "already obtained are cached and are not paid for twice.")
        raise SystemExit("\n".join(lines))

    return pd.concat(frames, ignore_index=True)


def task_means(frame: pd.DataFrame, cell: str, coding: str) -> pd.Series:
    sub = frame[frame["cell"] == cell]
    if sub.empty:
        raise SystemExit(f"no rows for configuration {cell!r}")
    values = pd.to_numeric(sub[coding], errors="coerce")
    return values.groupby(sub["task_id"]).mean()


def boot(values: np.ndarray, alpha: float = 0.05) -> tuple:
    rng = np.random.default_rng(SEED)
    draws = values[rng.integers(0, values.size, size=(RESAMPLES, values.size))].mean(axis=1)
    lo = 100.0 * alpha / 2.0
    return (float(values.mean()),
            float(np.percentile(draws, lo)),
            float(np.percentile(draws, 100.0 - lo)))


def verify(frame: pd.DataFrame, coding: str) -> None:
    """Reproduce Study 1's published contrast, or stop."""
    if coding != A.PRIMARY_CODING:
        return
    d = (task_means(frame, CLOUD_ROUTING, coding) - task_means(frame, DEV_ROUTING, coding)) \
        - (task_means(frame, CLOUD_DECIDING, coding) - task_means(frame, DEV_DECIDING, coding))
    recorded = json.loads(REPORT.read_text(encoding="utf-8"))["bootstrap"]["point"]
    if abs(float(d.mean()) - recorded) > 1e-9:
        raise SystemExit(f"task-level contrast {d.mean()!r} does not reproduce "
                         f"the recorded {recorded!r}; the estimator has drifted")
    print(f"estimator check: reproduces Study 1's {recorded:+.6f}\n")


def compensation(frame: pd.DataFrame, on_device: str, coding: str,
                 cloud: str = "sonnet") -> dict:
    """One pair: one cloud baseline against one on-device model."""
    cloud_deciding, cloud_routing = CLOUD_BASELINES[cloud]
    if on_device == "llama3.1-8b":
        # Study 1's own on-device model. Its rows are C2 and C4 and are not
        # re-run, so this pair is Study 1's headline recomputed here — which
        # is what makes it the check that the sweep sits on the same scale.
        deciding, routing = DEV_DECIDING, DEV_ROUTING
    else:
        deciding, routing = f"deciding@{on_device}", f"routing@{on_device}"

    cloud_gap = task_means(frame, cloud_routing, coding) - task_means(frame, routing, coding)
    dec_gap = task_means(frame, cloud_deciding, coding) - task_means(frame, deciding, coding)
    d = (cloud_gap - dec_gap).dropna().to_numpy()

    point, lo, hi = boot(d)
    _, lo90, hi90 = boot(d, alpha=0.10)
    routing_dev = float(task_means(frame, routing, coding).mean())
    return {
        "on_device_model": on_device,
        "cloud_baseline": cloud,
        "n_tasks": int(d.size),
        "compensation": point,
        "ci95": [lo, hi],
        "ci90": [lo90, hi90],
        "equivalent_at_margin": bool(lo90 > -MARGIN and hi90 < MARGIN),
        "capability_gap": float(task_means(frame, cloud_routing, coding).mean()) - routing_dev,
        # A second capability axis, unregistered, reported as a robustness
        # check on the first. `protocol_ext.md` §5 fixed the gap as routing
        # task success, on the reasoning that the routing design adds no
        # deliberation and so measures the model. That reasoning misses one
        # thing: under routing, what an action returns *is* the reply, so a
        # model that correctly reaches for the calculator answers with a bare
        # number and fails. Routing success therefore measures tool restraint
        # as well as capability. Decision accuracy scores which action the
        # model chose and never passes through the reply, so it is not subject
        # to that. If the slope is the same on both axes, the contamination
        # does not drive it.
        "capability_gap_decision":
            float(task_means(frame, cloud_routing, "decision_correct").mean())
            - float(task_means(frame, routing, "decision_correct").mean()),
        "routing_success": routing_dev,
        "deciding_success": float(task_means(frame, deciding, coding).mean()),
    }


def slope(frame: pd.DataFrame, pairs: list, coding: str,
          gap_field: str = "capability_gap", cloud: str = "sonnet") -> dict:
    """Compensation against the capability gap, across pairs.

    The gap is fixed by protocol_ext §5 as the cloud model's routing-design
    task success minus the on-device model's, so it is a property of the pair
    and was defined before any of these numbers existed.

    **The resampling unit is the task, not the pair.** §5 registers "a
    bootstrap interval on the same 48-task unit", which is the unit every
    other interval in both studies uses. An earlier implementation of this
    function resampled the six pairs by index instead. That is a different
    estimator and a badly behaved one at six points: a draw that collapses
    the spread of x fits a near-vertical line, and its draws ran past +11
    with 1.2% of them beyond |2|. It returned [+0.092, +0.595] where the
    registered unit returns an interval covering zero. Each resample below
    draws 48 tasks with replacement and recomputes every pair's contrast and
    every pair's gap on those tasks before the line is refitted, so the whole
    fit moves together.
    """
    if len(pairs) < 3:
        return {"note": "too few pairs to fit a slope", "n_pairs": len(pairs)}

    cloud_deciding, cloud_routing = CLOUD_BASELINES[cloud]
    gap_coding = "decision_correct" if gap_field.endswith("_decision") else coding

    tasks = sorted(task_means(frame, cloud_routing, coding).index)
    take = lambda cell, cod: task_means(frame, cell, cod).loc[tasks].to_numpy()
    CD, CR, CRG = (take(cloud_deciding, coding), take(cloud_routing, coding),
                   take(cloud_routing, gap_coding))

    models, dev = [p["on_device_model"] for p in pairs], {}
    for model in models:
        deciding, routing = ((DEV_DECIDING, DEV_ROUTING) if model == "llama3.1-8b"
                             else (f"deciding@{model}", f"routing@{model}"))
        dev[model] = (take(deciding, coding), take(routing, coding),
                      take(routing, gap_coding))

    def fit(idx):
        x = np.array([CRG[idx].mean() - dev[m][2][idx].mean() for m in models])
        y = np.array([((CR[idx] - dev[m][1][idx]) - (CD[idx] - dev[m][0][idx])).mean()
                      for m in models])
        return None if np.ptp(x) == 0 else float(np.polyfit(x, y, 1)[0])

    point = fit(np.arange(len(tasks)))
    rng = np.random.default_rng(SEED)
    draws = [v for v in (fit(rng.integers(0, len(tasks), len(tasks)))
                         for _ in range(RESAMPLES)) if v is not None]
    arr = np.array(draws)
    lo, hi = float(np.percentile(arr, 2.5)), float(np.percentile(arr, 97.5))
    return {"slope": point, "n_pairs": len(models), "gap_measured_by": gap_field,
            "resampling_unit": "task", "n_tasks": len(tasks),
            "ci95": [lo, hi], "excludes_zero": bool(lo > 0 or hi < 0),
            "note": "compensation regressed on the capability gap across pairs; "
                    "the 48-task unit is resampled and every pair recomputed"}


def ablations(frame: pd.DataFrame, coding: str) -> dict:
    """Each variant against the routing design, at both deployments.

    The reference is the deciding design's own advantage over routing in
    Study 1. A variant that removes the property carrying that advantage
    should collapse toward zero; one that removes a property costing the
    design should sit above it.

    Cloud is reported because the paper's §4.5 anchored its mechanism claim
    there — that is where the two designs decide almost identically and
    succeed very differently — so a mechanism test that ran only on-device
    would test the claim somewhere other than where it was made.
    """
    where = {"on-device": (DEV_ROUTING, DEV_DECIDING, "llama3.1-8b"),
             "cloud": (CLOUD_ROUTING, CLOUD_DECIDING, "claude-sonnet-4-6")}
    out: dict = {}
    for label, (routing_cell, deciding_cell, suffix) in where.items():
        routing = task_means(frame, routing_cell, coding)
        full = (task_means(frame, deciding_cell, coding) - routing).dropna().to_numpy()
        point, lo, hi = boot(full)
        block = {"deciding_advantage": {"estimate": point, "ci95": [lo, hi]},
                 "variants": {}}
        for name in ABLATIONS:
            cell = f"{name}@{suffix}"
            if not (STUDY2 / f"{cell}.scored.jsonl").exists():
                block["variants"][name] = {"note": "not scored"}
                continue
            d = (task_means(frame, cell, coding) - routing).dropna().to_numpy()
            pt, l, h = boot(d)
            block["variants"][name] = {
                "advantage_over_routing": pt, "ci95": [l, h],
                "share_of_full_advantage": (pt / point) if point else None,
            }
        out[label] = block
    return out


def routing_inversion(frame: pd.DataFrame, coding: str) -> dict:
    """Why the stronger cloud model scores lower under the routing design.

    Section 5.5 reports these counts and until 2026-09-08 nothing computed
    them. Under routing the reply the user reads is the action's return
    value, so a run that names an action is a run whose reply is machine
    output; the split is between runs that acted and runs that did not.
    """
    out = {}
    for label, cell in (("sonnet", CLOUD_ROUTING),
                        ("haiku", "routing@claude-haiku-4-5-20251001")):
        sub = frame[frame["cell"] == cell].copy()
        if sub.empty:
            continue
        acted = sub["decision"].apply(lambda d: bool((d or {}).get("tools")))
        v = pd.to_numeric(sub[coding], errors="coerce")
        block = {
            "acted": {"n": int(acted.sum()),
                      "task_success": float(v[acted].mean())},
            "did_not_act": {"n": int((~acted).sum()),
                            "task_success": float(v[~acted].mean())},
            "action_rate": float(acted.mean()),
        }
        rea = sub["category"] == "reasoning"
        if rea.any():
            block["reasoning_only"] = {
                "acted": {"n": int((rea & acted).sum()),
                          "task_success": float(v[rea & acted].mean())},
                "did_not_act": {"n": int((rea & ~acted).sum()),
                                "task_success": float(v[rea & ~acted].mean())},
            }
        out[label] = block
    return out


def property_costs(frame: pd.DataFrame, coding: str) -> dict:
    """What each removed property is worth, on-device minus cloud.

    Not registered, and section 5.5 says so. Each ablation is run at both
    deployments, so the property's contribution can be differenced across
    them; a difference near zero means the property is worth about the same
    whichever model is behind it.
    """
    out = {}
    for name in ABLATIONS:
        legs = {}
        for depl, model, base in (("cloud", "claude-sonnet-4-6", CLOUD_DECIDING),
                                  ("on-device", "llama3.1-8b", DEV_DECIDING)):
            cell = f"{name}@{model}"
            if cell not in set(frame["cell"]):
                continue
            full = task_means(frame, base, coding)
            cut = task_means(frame, cell, coding)
            shared = full.index.intersection(cut.index)
            legs[depl] = (full[shared] - cut[shared]).reindex(sorted(shared))
        if len(legs) != 2:
            continue
        shared = legs["cloud"].index.intersection(legs["on-device"].index)
        # On-device minus cloud, the direction section 5.5 states: a negative
        # number means the property buys less on the weaker model.
        diff = (legs["on-device"][shared] - legs["cloud"][shared]).to_numpy()
        point, lo, hi = boot(diff)
        out[name] = {"on_device_minus_cloud": point, "ci95": [lo, hi],
                     "n_tasks": int(diff.size),
                     "excludes_zero": bool(lo > 0 or hi < 0)}
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--coding", default=A.PRIMARY_CODING)
    args = ap.parse_args()

    frame = load(args.coding)
    verify(frame, args.coding)

    results = {}
    for cloud in CLOUD_BASELINES:
        pairs = []
        for model in ["llama3.1-8b"] + LADDER:
            try:
                pairs.append(compensation(frame, model, args.coding, cloud))
            except SystemExit as exc:
                print(f"skip {model} vs {cloud}: {exc}")
        results[cloud] = pairs

    clouds = [c for c in CLOUD_BASELINES if results[c]]
    order = [p["on_device_model"] for p in
             sorted(results[clouds[0]], key=lambda p: p["capability_gap"])]
    print(f"{'on-device model':16s}" +
          "".join(f"{'vs ' + c:>30s}" for c in clouds))
    for model in order:
        line = f"{model:16s}"
        for c in clouds:
            p_ = next(x for x in results[c] if x["on_device_model"] == model)
            star = "*" if (p_["ci95"][0] > 0 or p_["ci95"][1] < 0) else " "
            line += (f"{p_['compensation']:+9.3f} "
                     f"[{p_['ci95'][0]:+.3f},{p_['ci95'][1]:+.3f}]{star}")
        print(line)
    print("  * interval excludes zero")

    # Sorted for presentation only. The bootstrap resamples tasks rather than
    # positions in this list, so the interval no longer depends on the order.
    pairs = sorted(results[clouds[0]], key=lambda p: p["capability_gap"])
    s = slope(frame, pairs, args.coding)
    s_dec = slope(frame, pairs, args.coding, "capability_gap_decision")
    print(f"\nslope of compensation on capability gap: "
          f"{s.get('slope', float('nan')):+.4f}"
          + (f"  CI [{s['ci95'][0]:+.4f}, {s['ci95'][1]:+.4f}]" if "ci95" in s else "")
          + (f"   excludes zero: {s['excludes_zero']}" if "excludes_zero" in s else ""))
    print(f"  same, gap measured by decision accuracy:  "
          f"{s_dec.get('slope', float('nan')):+.4f}"
          + (f"  CI [{s_dec['ci95'][0]:+.4f}, {s_dec['ci95'][1]:+.4f}]" if "ci95" in s_dec else "")
          + (f"   excludes zero: {s_dec['excludes_zero']}" if "excludes_zero" in s_dec else ""))

    abl = ablations(frame, args.coding)
    for label, block in abl.items():
        full = block["deciding_advantage"]
        print()
        print(f"ablation, {label}. The deciding design's advantage over "
              f"routing is {full['estimate']:+.3f} "
              f"[{full['ci95'][0]:+.3f}, {full['ci95'][1]:+.3f}].")
        for name, v in block["variants"].items():
            if "note" in v:
                print(f"  {name:28s} {v['note']}")
                continue
            print(f"  {name:28s} {v['advantage_over_routing']:+.3f} "
                  f"[{v['ci95'][0]:+.3f}, {v['ci95'][1]:+.3f}]   "
                  f"{v['share_of_full_advantage']:.0%} of the full advantage")

    # `mistral:7b` never named an action, so its two configurations are the
    # same procedure twice and its point is not a test of the designs (§5.3).
    # Section 5.4 reports the line without it; the line was refitted by hand
    # until 2026-09-08.
    kept = [p for p in pairs if "mistral" not in p["on_device_model"]]
    s_no_mistral = slope(frame, kept, args.coding)
    print(f"\nslope with mistral-7b dropped: "
          f"{s_no_mistral.get('slope', float('nan')):+.4f}"
          + (f"  CI [{s_no_mistral['ci95'][0]:+.4f}, "
             f"{s_no_mistral['ci95'][1]:+.4f}]" if "ci95" in s_no_mistral else ""))

    inv = routing_inversion(frame, args.coding)
    for label, b in inv.items():
        print(f"\nrouting inversion, {label}: task success "
              f"{b['acted']['task_success']:.3f} on {b['acted']['n']} runs that "
              f"named an action, {b['did_not_act']['task_success']:.3f} on "
              f"{b['did_not_act']['n']} that did not; acts on "
              f"{b['action_rate']:.0%} of runs")
        if "reasoning_only" in b:
            r = b["reasoning_only"]
            print(f"  reasoning only: {r['acted']['task_success']:.3f} of "
                  f"{r['acted']['n']} against "
                  f"{r['did_not_act']['task_success']:.3f} of "
                  f"{r['did_not_act']['n']}")

    props = property_costs(frame, args.coding)
    print()
    for name, v in props.items():
        print(f"property cost, on-device minus cloud, {name:28s} "
              f"{v['on_device_minus_cloud']:+.4f} "
              f"[{v['ci95'][0]:+.4f}, {v['ci95'][1]:+.4f}]"
              + ("  excludes zero" if v["excludes_zero"] else ""))

    OUT.write_text(json.dumps({"coding": args.coding, "margin": MARGIN,
                               "pairs_by_cloud_baseline": results, "slope": s,
                               "slope_decision_axis": s_dec,
                               "slope_without_mistral": s_no_mistral,
                               "ablation": abl, "routing_inversion": inv,
                               "property_costs": props},
                              indent=2), encoding="utf-8")
    print(f"\nwrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
