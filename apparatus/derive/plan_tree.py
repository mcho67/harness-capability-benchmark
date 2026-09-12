"""
plan_tree — turn the import log into a keep/cut list for the apparatus.

CHARTER.md §3 gives the *ceiling*: everything the running experiment
imported. This script applies the two narrowings the charter also specifies,
and prints the result with line counts so the reduction can be audited
rather than trusted.

Narrowing 1 — §5, skills. Autodiscovery imports every file in
skills/action/, so the trace lists skills no task ever invokes. Import is
not use. A skill is kept only if it maps to a pre-registered task category,
and the map below is that mapping, written out so it can be argued with.

Narrowing 2 — §4, reason classes. Some reached modules belong to subsystems
the charter removes wholesale (screen, personality, proactive, voice
timing). They appear in the trace because something imported them at boot,
not because the text path needs them.

Everything narrowed out is printed WITH its reason. Nothing is dropped
quietly, and both narrowings apply identically to both arms — a cut that
touched one arm only would rebuild the confound core/ exists to prevent.

    python plan_tree.py            # summary
    python plan_tree.py --full     # every module, with its verdict
"""

from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PAPER_ROOT = os.path.dirname(os.path.dirname(HERE))
FROZEN = os.path.join(PAPER_ROOT, "frozen_v1")

# --- Narrowing 1: skills mapped to pre-registered task categories --------
# protocol.md §7 categories: trivial, reasoning, action, clarification,
# grounding, robustness. CHARTER.md §5 is the authority; this is its
# machine-readable form.
SKILL_KEEP = {
    "skills/action/math_skill.py":            "reasoning — chained arithmetic",
    "skills/action/file_skill.py":            "action — file operations",
    "skills/action/timer_skill.py":           "action — backgrounding a long task",
    "skills/action/notes_skill.py":           "action — durable side effect to verify",
    "skills/action/memory_skill.py":          "grounding — explicit recall",
    "skills/action/system_commands_skill.py": "trivial — time/date, one-step factual",
    "skills/social/conversation_skill.py":    "trivial + grounding — plain answers",
}
SKILL_INFRA = (
    "skills/__init__.py", "skills/base_skill.py", "skills/skill_contract.py",
    "skills/skill_meta.py", "skills/autodiscovery.py",
    "skills/action/__init__.py", "skills/social/__init__.py",
)

# --- Narrowing 2: reached, but inside a removed subsystem ----------------
CUT_REASONS = {
    "skills/action/screen_agent.py":           "no surface — GUI automation, replaced by sandboxed side-effect checks (§6.3)",
    "skills/action/screen_skill.py":           "no surface",
    "skills/action/screen_utils.py":           "no surface",
    "skills/action/computer_control_skill.py": "no surface — drives a desktop",
    "skills/action/app_automation_skill.py":   "no surface",
    "skills/action/app_registry.py":           "no surface",
    "skills/action/window_skill.py":           "no surface",
    "skills/action/app_volume_skill.py":       "no surface",
    "skills/action/media_skill.py":            "no surface",
    "skills/action/navigator_skill.py":        "no surface — opens a browser",
    "skills/action/clipboard_skill.py":        "no surface",
    "skills/action/deep_action_skill.py":      "no surface — multi-step GUI automation",
    "skills/action/smart_home_skill.py":       "unreachable — no device in a cell",
    "skills/action/download_skill.py":         "network side effect, not a task category",
    "skills/action/email_skill.py":            "network side effect, not a task category",
    "skills/action/calendar_skill.py":         "network side effect, not a task category",
    "skills/action/weather_skill.py":          "network dependency — nondeterministic",
    "skills/action/web_search_skill.py":       "network dependency — nondeterministic",
    "skills/action/research_skill.py":         "network dependency — nondeterministic",
    "skills/action/document_skill.py":         "not a pre-registered category",
    "skills/action/system_monitor_skill.py":   "not a pre-registered category",
    "skills/action/dictation_skill.py":        "pre-transcription",
    "skills/social/social_reflex_skill.py":    "personality layer removed (§6.2)",
    "skills/adaptive.py":                      "personality layer removed (§6.2)",
    "formatting/action_personality.py":        "personality layer removed (§6.2)",
    "greetings.py":                            "personality layer removed (§6.2)",
    "config_voice_timing.py":                  "pre-transcription — voice turn timing",
    "stream_timing.py":                        "pre-transcription — speech pacing",
    "response_streaming.py":                   "pre-transcription — streams to TTS",
    "mood/__init__.py":                        "unreachable from a task-driven text path",
    "proactive/__init__.py":                   "unreachable — no unprompted turns in a cell",
    "proactive/engine.py":                     "unreachable — no unprompted turns in a cell",
    "proactive/monitors.py":                   "unreachable — no unprompted turns in a cell",
    "proactive/precompute.py":                 "suppressed in research mode — a cache hit is not measured work",
    "awareness.py":                            "unreachable — ambient context, no surface",
    "continuity.py":                           "unreachable — session resumption across app restarts",
    "startup_check.py":                        "not apparatus — boot-time environment check",
    "research/__init__.py":                    "replaced by apparatus/harness/",
    "research/run_cell.py":                    "replaced by apparatus/harness/",
    "research/capture.py":                     "replaced by apparatus/harness/",
    "research/schema.py":                      "replaced by apparatus/harness/",
}


def loc(relpath: str) -> int:
    try:
        with open(os.path.join(FROZEN, relpath), encoding="utf-8",
                  errors="replace") as fh:
            return sum(1 for _ in fh)
    except OSError:
        return 0


def verdict(relpath: str) -> "tuple[str, str]":
    """Return (KEEP|CUT, reason) for one reached module."""
    if relpath in CUT_REASONS:
        return "CUT", CUT_REASONS[relpath]
    if relpath.startswith("skills/"):
        if relpath in SKILL_INFRA:
            return "KEEP", "skill plumbing — the action surface itself"
        if relpath in SKILL_KEEP:
            return "KEEP", SKILL_KEEP[relpath]
        return "CUT", "imported by autodiscovery, never invoked; no task category (§5)"
    return "KEEP", "reached on the text path (§3)"


def main() -> int:
    full = "--full" in sys.argv
    with open(os.path.join(HERE, "import_log.json"), encoding="utf-8") as fh:
        log = json.load(fh)
    if not log.get("complete", False):
        print(f"NOTE: import log is incomplete "
              f"({log.get('incomplete_cells')}); this plan is provisional.\n")

    keep, cut = [], []
    for entry in log["modules"].values():
        p = entry["path"]
        v, why = verdict(p)
        (keep if v == "KEEP" else cut).append((p, why, loc(p), entry["cells"]))
    keep.sort()
    cut.sort()

    kl = sum(r[2] for r in keep)
    cl = sum(r[2] for r in cut)
    if full:
        for label, rows in (("KEEP", keep), ("CUT", cut)):
            print(f"\n===== {label} ({len(rows)} modules, "
                  f"{sum(r[2] for r in rows)} lines) =====")
            for p, why, n, cells in rows:
                mark = "" if len(cells) == 4 else f"   [only {'+'.join(cells)}]"
                print(f"  {n:5d}  {p:50s} {why}{mark}")

    print(f"\nreached : {len(keep) + len(cut):4d} modules  {kl + cl:6d} lines")
    print(f"keep    : {len(keep):4d} modules  {kl:6d} lines")
    print(f"cut     : {len(cut):4d} modules  {cl:6d} lines")
    print(f"\ncharter §4 target is 8-12k lines; this plan lands at {kl}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
