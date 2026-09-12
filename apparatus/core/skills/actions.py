"""
The action set — every tool both arms can reach, and nothing else.

Each one names the pre-registered task category that justifies it. A tool
without a category cannot be constructed (`ToolSpec.__post_init__`), which is
how "added for realism" is kept out: the only way in is to name the category
that demanded it, and CHARTER §5 requires a dated entry for any addition.

All of them act on a `World` and nothing else. There is no path from here to
the real filesystem, the real clock's timers, or a real application.
"""

from __future__ import annotations

import ast
import operator
import re
from typing import Any, Dict, List

from ..sandbox import SandboxError, World
from .base import SkillResult, ToolSpec

# ── trivial: the clock ───────────────────────────────────────────────────


def _time(world: World) -> SkillResult:
    now = world.system.now()
    return SkillResult(f"It's {now['time']}.", data=now)


def _date(world: World) -> SkillResult:
    now = world.system.now()
    return SkillResult(f"Today is {now['date']}.", data=now)


# ── trivial: the machine (recorded, never performed) ─────────────────────


def _open_app(world: World, app: str = "") -> SkillResult:
    world.system.open_app(app)
    return SkillResult(f"Opening {app}.", data={"app": app})


def _close_app(world: World, app: str = "") -> SkillResult:
    world.system.close_app(app)
    return SkillResult(f"Closing {app}.", data={"app": app})


def _volume(world: World, delta: int) -> SkillResult:
    level = world.system.set_volume(delta)
    return SkillResult(f"Volume is now {level}.", data={"volume": level})


# ── reasoning: arithmetic ────────────────────────────────────────────────

_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv, ast.Pow: operator.pow,
        ast.Mod: operator.mod, ast.USub: operator.neg, ast.UAdd: operator.pos,
        ast.FloorDiv: operator.floordiv}


def _eval(node: ast.AST) -> float:
    """Arithmetic only. `eval` is not used: the expression comes from a
    language model, and the study does not need a code-execution surface to
    answer whether an assistant can add up."""
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    raise ValueError("unsupported expression")


def _quick_math(world: World, expression: str = "") -> SkillResult:
    try:
        value = _eval(ast.parse(expression.replace("x", "*").replace("×", "*"),
                                mode="eval"))
    except Exception:
        return SkillResult(f"I couldn't evaluate {expression!r}.", ok=False)
    shown = int(value) if float(value).is_integer() else round(value, 6)
    return SkillResult(str(shown), data={"expression": expression, "value": value})


# ── action: files ────────────────────────────────────────────────────────


def _search_files(world: World, query: str = "") -> SkillResult:
    hits = world.files.search(query)
    if not hits:
        return SkillResult(f"No files matching {query!r}.", data={"hits": []})
    head = hits[:20]
    more = "" if len(hits) == len(head) else f" (and {len(hits) - len(head)} more)"
    return SkillResult(f"Found {len(hits)}: " + ", ".join(head) + more,
                       data={"hits": hits})


def _list_files(world: World, folder: str = "") -> SkillResult:
    try:
        files = world.files.list(folder)
    except SandboxError as e:
        return SkillResult(str(e), ok=False)
    return SkillResult(f"{len(files)} files: " + ", ".join(files[:20]),
                       data={"files": files})


def _read_file(world: World, path: str = "") -> SkillResult:
    try:
        return SkillResult(world.files.read(path), data={"path": path})
    except SandboxError as e:
        return SkillResult(str(e), ok=False)


def _write_file(world: World, path: str = "", content: str = "") -> SkillResult:
    try:
        world.files.write(path, content)
    except SandboxError as e:
        return SkillResult(str(e), ok=False)
    return SkillResult(f"Wrote {path}.", data={"path": path})


def _delete_file(world: World, path: str = "") -> SkillResult:
    try:
        world.files.delete(path)
    except SandboxError as e:
        return SkillResult(str(e), ok=False)
    return SkillResult(f"Deleted {path}.", data={"path": path})


def _file_stat(world: World, path: str = "") -> SkillResult:
    try:
        st = world.files.stat(path)
    except SandboxError as e:
        return SkillResult(str(e), ok=False)
    return SkillResult(f"{st['path']}: {st['bytes']} bytes, last modified "
                       f"{st['modified']}.", data=st)


# ── action: notes ────────────────────────────────────────────────────────


def _add_note(world: World, text: str = "", title: str = "") -> SkillResult:
    nid = world.notes.add(text, title=title)
    return SkillResult("Noted.", data={"id": nid})


def _show_notes(world: World) -> SkillResult:
    notes = world.notes.all()
    if not notes:
        return SkillResult("You have no notes.", data={"notes": []})
    body = "; ".join(f"{n['title'] or n['id']}: {n['text']}" for n in notes)
    return SkillResult(f"{len(notes)} notes — {body}", data={"notes": notes})


def _remove_note(world: World, id: str = "") -> SkillResult:
    try:
        world.notes.remove(id)
    except SandboxError as e:
        return SkillResult(str(e), ok=False)
    return SkillResult(f"Removed {id}.", data={"id": id})


# ── grounding: durable facts ─────────────────────────────────────────────


def _remember(world: World, key: str = "", value: str = "") -> SkillResult:
    world.facts.remember(key, value)
    return SkillResult(f"I'll remember that {key} is {value}.",
                       data={"key": key})


def _recall(world: World, key: str = "") -> SkillResult:
    got = world.facts.recall(key)
    if got is None:
        return SkillResult(f"I have nothing recorded for {key!r}.",
                           data={"key": key, "found": False})
    return SkillResult(str(got), data={"key": key, "found": True})


# ── action: timers ───────────────────────────────────────────────────────

_UNITS = {"second": 1, "seconds": 1, "sec": 1, "s": 1,
          "minute": 60, "minutes": 60, "min": 60, "m": 60,
          "hour": 3600, "hours": 3600, "h": 3600}
_WORD_NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
             "seven": 7, "eight": 8, "nine": 9, "ten": 10, "fifteen": 15,
             "twenty": 20, "thirty": 30, "forty": 40, "forty-five": 45,
             "sixty": 60, "half": 0.5}


def parse_duration(text: str) -> float:
    """Words or digits to seconds, or 0.0 if nothing parses.

    Shared by both arms so duration parsing cannot differ between them. It is
    deliberately forgiving of typos in the *unit* (robust-06 says "10
    mnutes"), because that task's ideal is to act, not to ask.
    """
    t = str(text).lower().strip()
    m = re.search(r"(\d+(?:\.\d+)?)\s*([a-z]+)?", t)
    if m:
        n, unit = float(m.group(1)), (m.group(2) or "minute")
    else:
        words = re.findall(r"[a-z-]+", t)
        n = next((_WORD_NUM[w] for w in words if w in _WORD_NUM), 0.0)
        unit = next((w for w in words if w[:3] in ("sec", "min", "hou", "mnu")), "minute")
        if not n:
            return 0.0
    u = unit[:3]
    mult = 1 if u == "sec" else 3600 if u in ("hou", "hr") else 60
    return float(n) * mult


def _set_timer(world: World, duration: str = "", label: str = "") -> SkillResult:
    seconds = parse_duration(duration)
    if seconds <= 0:
        return SkillResult("", needs=("duration",))
    tid = world.timers.set(seconds, label=label)
    mins = seconds / 60
    pretty = f"{int(mins)} minutes" if mins >= 1 and float(mins).is_integer() \
        else f"{int(seconds)} seconds"
    return SkillResult(f"Timer set for {pretty}.",
                       data={"id": tid, "seconds": seconds})


def _cancel_timer(world: World, id: str = "") -> SkillResult:
    removed = world.timers.cancel(id)
    if not removed:
        return SkillResult("You have no timers running.", data={"removed": 0})
    return SkillResult(f"Cancelled {removed} timer(s).", data={"removed": removed})


def _show_timers(world: World) -> SkillResult:
    ts = world.timers.all()
    if not ts:
        return SkillResult("No timers running.", data={"timers": []})
    return SkillResult(f"{len(ts)} running.", data={"timers": ts})


# ── the set ──────────────────────────────────────────────────────────────

def _spec(name, desc, props, required, run, category, justification):
    return ToolSpec(name=name, description=desc, properties=props,
                    required=tuple(required), run=run, category=category,
                    justification=justification)


_STR = {"type": "string"}


def build_action_set() -> Dict[str, ToolSpec]:
    """The fixed action set. Built by a function so a test can construct a
    second, independent copy and confirm the arms are not sharing mutable
    state through it."""
    specs: List[ToolSpec] = [
        _spec("time", "Get the current time of day.", {}, (), _time,
              "trivial", "protocol §7 category 1 — one-step factual readout"),
        _spec("date", "Get today's calendar date.", {}, (), _date,
              "trivial", "protocol §7 category 1 — one-step factual readout"),
        _spec("open_app", "Open an application by name.",
              {"app": {**_STR, "description": "which application to open"}},
              ("app",), _open_app,
              "trivial", "protocol §7 category 1 — single-step command with a side effect"),
        _spec("close_app", "Close an application by name.",
              {"app": {**_STR, "description": "which application to close"}},
              ("app",), _close_app,
              "trivial", "protocol §7 category 1 — the counterpart to open_app"),
        _spec("volume_up", "Raise the system volume.", {}, (),
              lambda world: _volume(world, +10),
              "trivial", "protocol §7 category 1 — bare imperative, no argument"),
        _spec("volume_down", "Lower the system volume.", {}, (),
              lambda world: _volume(world, -10),
              "trivial", "protocol §7 category 1 — bare imperative, no argument"),

        _spec("quick_math", "Evaluate an arithmetic expression.",
              {"expression": {**_STR, "description": "the arithmetic to evaluate, e.g. '12*8'"}},
              ("expression",), _quick_math,
              "reasoning", "protocol §7 category 2 — chained inference needs arithmetic"),

        _spec("search_files", "Search files by name and by content.",
              {"query": {**_STR, "description": "what to search for"}},
              ("query",), _search_files,
              "action", "protocol §7 category 3 — the primary tool-choice action"),
        _spec("list_files", "List the files in a folder.",
              {"folder": {**_STR, "description": "which folder, or blank for everything"}},
              (), _list_files,
              "action", "protocol §7 category 3 — the second step of a two-step goal"),
        _spec("read_file", "Read a file's contents.",
              {"path": {**_STR, "description": "which file to read"}},
              ("path",), _read_file,
              "action", "protocol §7 category 3 — reading is the input to sequencing"),
        _spec("write_file", "Write content to a file.",
              {"path": {**_STR, "description": "what to name the file"},
               "content": {**_STR, "description": "what to put in it"}},
              ("path", "content"), _write_file,
              "action", "protocol §7 category 3 — a verifiable durable side effect"),
        _spec("delete_file", "Delete a file.",
              {"path": {**_STR, "description": "which file to delete"}},
              ("path",), _delete_file,
              "action", "protocol §7 category 3 — the destructive action clar-07 and act-11 pivot on"),
        _spec("file_stat", "Get a file's size and last-modified time.",
              {"path": {**_STR, "description": "which file to inspect"}},
              ("path",), _file_stat,
              "action", "protocol §7 category 3 — act-13's second step"),

        _spec("add_note", "Save a note.",
              {"text": {**_STR, "description": "what the note should say"},
               "title": {**_STR, "description": "an optional short title"}},
              ("text",), _add_note,
              "action", "protocol §7 category 3 — a verifiable durable side effect"),
        _spec("show_notes", "List saved notes.", {}, (), _show_notes,
              "action", "protocol §7 category 3 — the read half of the notes surface"),
        _spec("remove_note", "Delete a saved note.",
              {"id": {**_STR, "description": "which note, by id"}},
              ("id",), _remove_note,
              "action", "protocol §7 category 3 — completes the notes surface"),

        _spec("remember", "Store a fact for later recall.",
              {"key": {**_STR, "description": "what the fact is about"},
               "value": {**_STR, "description": "the fact itself"}},
              ("key", "value"), _remember,
              "grounding", "protocol §7 category 5 — explicit durable grounding"),
        _spec("recall", "Retrieve a previously stored fact.",
              {"key": {**_STR, "description": "what to look up"}},
              ("key",), _recall,
              "grounding", "protocol §7 category 5 — the read half of grounding"),

        _spec("set_timer", "Set a countdown timer.",
              {"duration": {**_STR, "description": "how long, e.g. '5 minutes'"},
               "label": {**_STR, "description": "an optional label"}},
              ("duration",), _set_timer,
              "action", "protocol §7 category 3 — the backgroundable action"),
        _spec("cancel_timer", "Cancel a running timer.",
              {"id": {**_STR, "description": "which timer, or blank for all"}},
              (), _cancel_timer,
              "action", "protocol §7 category 3 — completes the timer surface"),
        _spec("show_timers", "List running timers.", {}, (), _show_timers,
              "action", "protocol §7 category 3 — completes the timer surface"),
    ]
    return {s.name: s for s in specs}
