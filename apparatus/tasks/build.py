"""
build — assemble the six category files into tasks.json, with the ideal
derived rather than authored.

Run it to rebuild; run it with --check to verify the committed tasks.json
matches its sources without writing anything (what CI would do).

The build does three things worth naming:

1. It derives `ideal_decision` for every task from that task's properties,
   so the shipped file cannot contain an ideal nobody can trace to a rule.
2. It verifies the derived ideal against the hand-written ideal inherited
   from `frozen_v1`, for the tasks that have one. A disagreement stops the
   build unless it is listed in IDEAL_CORRECTIONS with a reason and a date.
   An allowlist is the point: agreement proves nothing if disagreement is
   also silent. This check has already caught one error in the
   pre-registration (see triv-02).
3. It checks the counts against the pre-registration: 48 tasks, eight per
   category (protocol §13), that every fixture a task asks for exists in the
   sandbox registry, and that every tool a task names is one the apparatus
   actually has. The tool check was added 2026-08-19 after it turned out 18
   records named tools that did not exist (see ANSWER_DIRECTLY in
   `derive_ideal.py`); the fixture check was already catching the same class
   of error one field over.

It also emits a sha256 of the built file. CHARTER §8 freezes the task set by
hash, so the hash is part of the build output rather than something computed
later and hoped to match.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys

from derive_ideal import ANSWER_DIRECTLY, derive_ideal, validate

# Fixture names are checked against the sandbox's own registry rather than a
# list kept here. A task asking for a fixture that does not exist would
# otherwise run against an empty world and fail for a reason that looks like
# the assistant's fault.
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ""))
from core.sandbox import FIXTURES
from core.skills import ACTION_SET

HERE = os.path.dirname(os.path.abspath(__file__))
PAPER_ROOT = os.path.dirname(os.path.dirname(HERE))
FROZEN_TASKS = os.path.join(PAPER_ROOT, "frozen_v1", "research", "tasks.json")
OUT = os.path.join(HERE, "tasks.json")

CATEGORIES = ("trivial", "reasoning", "action",
              "clarification", "grounding", "robustness")
PER_CATEGORY = 8

# Inherited ideals the build knowingly overrides. Each entry is a correction
# to a pre-registered value, so each needs a reason and a date, and the build
# fails on any drift NOT listed here. An allowlist is the point: silent
# agreement proves nothing if disagreement is also silent.
IDEAL_CORRECTIONS = {
    "triv-02": (
        "2026-08-19 (pre-data). The inherited ideal names `time` as the "
        "correct tool for \"what's today's date\". system_commands_skill "
        "exposes `time` and `date` as separate intents, so the inherited "
        "ideal marks the correct answer wrong. Corrected to `date`. Found by "
        "this build check, not by inspection."
    ),
    # The two inherited clarification tasks re-screened at the validity gate.
    # Both were tagged `missing_required_argument` against the full product's
    # action surface. After the reduction (protocol §12a item 4) no retained
    # action can fulfil either request at all, so the ideal moved from "ask"
    # to "decline" -- and `derive_ideal` now encodes that declining supersedes
    # asking. The pilot showed the cost of leaving them: the cloud model
    # declined correctly on capability grounds and was scored a fail by a
    # criterion that only admitted asking.
    "clar-04": (
        "2026-08-19 (pre-data, at the validity gate). 'play that one again' "
        "needs media playback; no retained action can play anything. "
        "Re-screened to `beyond_capability` by the same rule."
    ),
}

# Inherited task ids whose task is gone. Their replacements are different
# tasks and take new ids -- an id is a join key and reusing one would silently
# merge two different tasks in any downstream file.
RETIRED = {
    "clar-02": "named deep_action (GUI automation); replaced in role by clar-09",
    "act-02":  "named read_screen; replaced in role by act-09",
    "act-03":  "named operate_app / deep_action; replaced in role by act-10",
    "act-04":  "named deep_action; backgrounding showcase role passes to act-15",
    "act-05":  "named web_search / research; long-running role passes to act-12",
}


def _inherited_ideals():
    """The hand-written ideals from the snapshot, by task id."""
    try:
        with open(FROZEN_TASKS, encoding="utf-8") as fh:
            return {t["id"]: t.get("ideal_decision", {})
                    for t in json.load(fh)}
    except OSError:
        return {}


# Names the snapshot used for the same claim the apparatus now spells
# differently. Applied to the *inherited* side before comparing, so the
# reproduction check still fails on real drift while a pure rename does not
# masquerade as one. Added 2026-08-19 (pre-data): `general_conversation` and
# `recall_conversation` were routing-NLU intents, not tools, and both meant
# "no action needed" -- see ANSWER_DIRECTLY in derive_ideal.py. Listing them
# here rather than in IDEAL_CORRECTIONS is the point: nothing about what
# counts as the right answer moved, so calling it a correction would overstate
# the change and hide that the ideal is unchanged.
_RENAMED = {
    "general_conversation": ANSWER_DIRECTLY,
    "recall_conversation":  ANSWER_DIRECTLY,
    "cancel_all_timers":    "cancel_timer",
}


def _reproduces(derived, inherited, task):
    """Does the derived ideal agree with the inherited hand-written one?

    Only the fields the old format actually carried are compared. The old
    records used `tool` (single) or `tool_any` (list) and omitted fields
    they had no opinion about, so absence means 'unstated', not False.
    """
    problems = []
    for field in ("asked", "backgrounded", "decomposed"):
        if field in inherited and bool(inherited[field]) != bool(derived[field]):
            problems.append(
                f"{field}: inherited {inherited[field]}, derived {derived[field]}")

    old_tools = set()
    if "tool" in inherited:
        old_tools = {inherited["tool"]}
    elif "tool_any" in inherited:
        old_tools = set(inherited["tool_any"])
    old_tools = {_RENAMED.get(t, t) for t in old_tools}
    if old_tools and set(derived["tools"]) and not (old_tools & set(derived["tools"])):
        problems.append(
            f"tools: inherited {sorted(old_tools)}, derived {derived['tools']}")
    return problems


def main() -> int:
    check_only = "--check" in sys.argv
    if ANSWER_DIRECTLY in ACTION_SET:
        print(f"{ANSWER_DIRECTLY!r} is both a reserved name and a real "
              f"action; one of them has to be renamed", file=sys.stderr)
        return 1
    inherited = _inherited_ideals()

    tasks, problems, drift, corrected = [], [], [], []
    for cat in CATEGORIES:
        path = os.path.join(HERE, f"{cat}.json")
        if not os.path.exists(path):
            problems.append(f"{cat}.json missing")
            continue
        with open(path, encoding="utf-8") as fh:
            rows = json.load(fh)
        if len(rows) != PER_CATEGORY:
            problems.append(
                f"{cat}: {len(rows)} tasks, pre-registration says {PER_CATEGORY}")
        for t in rows:
            if t.get("category") != cat:
                problems.append(f"{t.get('id')}: category != {cat}")
            bad = validate(t)
            unknown = [f for f in (t.get("fixtures") or []) if f not in FIXTURES]
            if unknown:
                bad = bad + [f"unknown fixtures {unknown}; "
                             f"known: {sorted(FIXTURES)}"]
            # An ideal may only name a tool that exists. Without this, a task
            # can be scored against a tool no arm can call, which reads as
            # the assistant failing rather than the task set being wrong.
            no_such = [n for n in (t.get("tool_any") or [])
                       if n != ANSWER_DIRECTLY and n not in ACTION_SET]
            if no_such:
                bad = bad + [f"tool_any names no such action {no_such}; "
                             f"known: {sorted(ACTION_SET)} + {ANSWER_DIRECTLY!r}"]
            if bad:
                problems.append(f"{t.get('id')}: {'; '.join(bad)}")
                continue
            ideal = derive_ideal(t)
            if t["id"] in inherited:
                mismatch = _reproduces(ideal, inherited[t["id"]], t)
                if mismatch and t["id"] not in IDEAL_CORRECTIONS:
                    drift.append(f"{t['id']}: {'; '.join(mismatch)}")
                elif mismatch:
                    corrected.append(f"{t['id']}: {'; '.join(mismatch)}")
            tasks.append({**t, "ideal_decision": ideal})

    ids = [t["id"] for t in tasks]
    if len(set(ids)) != len(ids):
        problems.append("duplicate task ids")
    if len(tasks) != len(CATEGORIES) * PER_CATEGORY:
        problems.append(f"{len(tasks)} tasks total, expected "
                        f"{len(CATEGORIES) * PER_CATEGORY}")

    for line in problems:
        print(f"INVALID  {line}", file=sys.stderr)
    for line in drift:
        print(f"IDEAL DRIFT  {line}", file=sys.stderr)
    for line in corrected:
        print(f"corrected inherited ideal  {line}")
    if problems or drift:
        print("\nbuild failed — nothing written", file=sys.stderr)
        return 1

    # Hash the exact bytes that land on disk, and write those bytes.
    #
    # Fixed 2026-08-19 (pre-data), found when the first real run row carried a
    # different sha256 than this build printed. The blob was hashed in memory
    # with "\n" and then written through Windows text mode, which turns every
    # newline into "\r\n" — so the file's hash was never the hash anyone had
    # been told. CHARTER §8 freezes the task set *by hash*, and two hashes for
    # one artifact makes the freeze meaningless; it would have surfaced only
    # when a reviewer tried to verify it. Binary mode takes the platform out
    # of the answer.
    blob = (json.dumps(tasks, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    digest = hashlib.sha256(blob).hexdigest()

    if check_only:
        current = open(OUT, "rb").read() if os.path.exists(OUT) else b""
        if current != blob:
            print("tasks.json is stale — re-run build.py", file=sys.stderr)
            return 1
        print(f"ok  {len(tasks)} tasks  sha256 {digest[:16]}")
        return 0

    with open(OUT, "wb") as fh:
        fh.write(blob)

    n_inherited = sum(1 for t in tasks if t["id"] in inherited)
    print(f"built {len(tasks)} tasks -> {OUT}")
    n_corr = len(corrected)
    print(f"  {n_inherited} inherited "
          f"({n_inherited - n_corr} ideals reproduced, {n_corr} corrected), "
          f"{len(tasks) - n_inherited} authored")
    for cat in CATEGORIES:
        n = sum(1 for t in tasks if t["category"] == cat)
        print(f"  {cat:14s} {n}")
    still_used = set(RETIRED) & set(ids)
    if still_used:
        print(f"retired ids reused: {sorted(still_used)}", file=sys.stderr)
        return 1
    print(f"  {len(RETIRED)} retired ids, not reused: "
          f"{', '.join(sorted(RETIRED))}")
    print(f"  sha256 {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
