"""
The sandbox — a disposable world one task acts on, and a log of what it did.

Two jobs, and they are separate on purpose.

**Isolation.** CHARTER §7 requires state to be isolated at the task boundary,
because the pilot showed a fact learned in one task leaking into the prompt of
unrelated later ones, and because task order is shuffled per repetition —
which makes contamination order-dependent and the runs non-independent. Every
task gets a fresh `World` rooted in its own temporary directory, and the root
is passed in from the harness so nothing is ever written inside the instrument
tree.

**Verification.** Scoring an action by reading the assistant's prose asks a
grader whether it *sounds* like the file was deleted. The sandbox instead
records every effect as it happens, so the scorer asks the world what changed.
`world.did("file.delete", "draft-old.txt")` is a fact; "it said it deleted the
file" is a claim.

Recording effects also makes **absence** checkable, which several tasks need.
clar-07 asks the assistant to "clear out the old downloads" without saying
which — the ideal is to ask, and part of succeeding is that *nothing was
deleted*. Only an effect log can score that.

Nothing here touches the real machine. `open_app` and volume changes are
recorded, never executed: the measured quantity is the decision to launch the
calculator, not whether Windows opened a window 960 times.
"""

from __future__ import annotations

import json
import os
import shutil
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


class SandboxError(RuntimeError):
    """An operation the sandbox refuses — most often an escape attempt."""


@dataclass(frozen=True)
class Effect:
    """One thing that happened to the world.

    `kind` is a dotted verb (`file.delete`, `note.add`, `app.launch`) and
    `target` is what it happened to. Both are matched exactly by the scorer,
    so the vocabulary is small and closed by convention rather than by
    cleverness.
    """
    kind: str
    target: str
    detail: Dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=lambda: round(time.time(), 4))


class _Store:
    """Common plumbing: every store appends to the world's one effect log."""

    def __init__(self, world: "World") -> None:
        self._world = world

    def _record(self, kind: str, target: str, **detail: Any) -> None:
        self._world.effects.append(Effect(kind=kind, target=target,
                                          detail=detail))


class FileStore(_Store):
    """A rooted filesystem. Every path resolves inside `root` or raises.

    The traversal guard is not decoration. The apparatus hands a file tool to
    a language model and asks it to act on paths the model chose; a study that
    let `../../` out of the sandbox would be a study that occasionally deleted
    something of the author's.
    """

    def __init__(self, world: "World", root: Path) -> None:
        super().__init__(world)
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, relpath: str) -> Path:
        """Relative paths inside the root, and nothing else.

        An absolute path is rejected rather than quietly rebased onto the
        root. Rebasing would contain it, but it would also turn "delete
        /etc/passwd" into a successful-looking delete of a sandbox file, and
        the fact that the model reached outside is exactly the kind of thing
        the effect log exists to surface.
        """
        raw = str(relpath)
        candidate = Path(raw)
        if candidate.is_absolute() or candidate.drive or raw.startswith(("/", "\\")):
            raise SandboxError(f"absolute path refused: {relpath!r}")
        root = self.root.resolve()
        p = (root / raw).resolve()
        if p != root and root not in p.parents:
            raise SandboxError(f"path escapes the sandbox: {relpath!r}")
        return p

    def list(self, subdir: str = "") -> List[str]:
        base = self._resolve(subdir) if subdir else self.root
        out = [str(p.relative_to(self.root)).replace(os.sep, "/")
               for p in sorted(base.rglob("*")) if p.is_file()]
        self._record("file.list", subdir or ".", count=len(out))
        return out

    def search(self, query: str, *, in_content: bool = True) -> List[str]:
        """Filename match, plus content match for text-like files."""
        q = query.lower()
        hits: List[str] = []
        for p in sorted(self.root.rglob("*")):
            if not p.is_file():
                continue
            rel = str(p.relative_to(self.root)).replace(os.sep, "/")
            if q in rel.lower():
                hits.append(rel)
                continue
            if in_content and p.suffix.lower() in (".txt", ".md", ".csv", ".json"):
                try:
                    if q in p.read_text(encoding="utf-8", errors="replace").lower():
                        hits.append(rel)
                except OSError:
                    pass
        self._record("file.search", query, hits=len(hits))
        return hits

    def read(self, relpath: str) -> str:
        p = self._resolve(relpath)
        if not p.is_file():
            raise SandboxError(f"no such file: {relpath}")
        self._record("file.read", relpath)
        return p.read_text(encoding="utf-8", errors="replace")

    def write(self, relpath: str, content: str) -> None:
        p = self._resolve(relpath)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        self._record("file.write", relpath, bytes=len(content))

    def delete(self, relpath: str) -> None:
        p = self._resolve(relpath)
        if not p.is_file():
            raise SandboxError(f"no such file: {relpath}")
        p.unlink()
        self._record("file.delete", relpath)

    def stat(self, relpath: str) -> Dict[str, Any]:
        p = self._resolve(relpath)
        if not p.is_file():
            raise SandboxError(f"no such file: {relpath}")
        st = p.stat()
        self._record("file.stat", relpath)
        return {"path": relpath, "bytes": st.st_size,
                "modified": time.strftime("%Y-%m-%d %H:%M",
                                          time.localtime(st.st_mtime))}

    def exists(self, relpath: str) -> bool:
        """Not recorded — used by the scorer, not by the assistant."""
        try:
            return self._resolve(relpath).is_file()
        except SandboxError:
            return False


class NoteStore(_Store):
    def __init__(self, world: "World") -> None:
        super().__init__(world)
        self.notes: List[Dict[str, Any]] = []

    def add(self, text: str, title: str = "") -> str:
        nid = f"note-{len(self.notes) + 1}"
        self.notes.append({"id": nid, "title": title, "text": text})
        self._record("note.add", nid, title=title, text=text)
        return nid

    def all(self) -> List[Dict[str, Any]]:
        self._record("note.list", "*", count=len(self.notes))
        return list(self.notes)

    def remove(self, nid: str) -> None:
        before = len(self.notes)
        self.notes = [n for n in self.notes if n["id"] != nid]
        if len(self.notes) == before:
            raise SandboxError(f"no such note: {nid}")
        self._record("note.remove", nid)


class FactStore(_Store):
    def __init__(self, world: "World") -> None:
        super().__init__(world)
        self.facts: Dict[str, str] = {}

    def remember(self, key: str, value: str) -> None:
        self.facts[key] = value
        self._record("fact.remember", key, value=value)

    def recall(self, key: str) -> Optional[str]:
        self._record("fact.recall", key, found=key in self.facts)
        return self.facts.get(key)

    def all(self) -> Dict[str, str]:
        return dict(self.facts)


class TimerStore(_Store):
    """Timers are recorded, never slept.

    A 45-minute timer must not cost the run 45 minutes, and the measured
    quantity is the decision to set one.
    """

    def __init__(self, world: "World") -> None:
        super().__init__(world)
        self.timers: List[Dict[str, Any]] = []

    def set(self, seconds: float, label: str = "") -> str:
        tid = f"timer-{len(self.timers) + 1}"
        self.timers.append({"id": tid, "seconds": float(seconds), "label": label})
        self._record("timer.set", tid, seconds=float(seconds), label=label)
        return tid

    def cancel(self, tid: str = "") -> int:
        n = len(self.timers)
        self.timers = [] if not tid else [t for t in self.timers if t["id"] != tid]
        removed = n - len(self.timers)
        self._record("timer.cancel", tid or "*", removed=removed)
        return removed

    def all(self) -> List[Dict[str, Any]]:
        return list(self.timers)


class SystemStore(_Store):
    """App launches and volume changes: recorded, never performed."""

    def __init__(self, world: "World") -> None:
        super().__init__(world)
        self.volume = 50
        self.launched: List[str] = []

    def open_app(self, name: str) -> None:
        self.launched.append(name)
        self._record("app.launch", name.lower())

    def close_app(self, name: str) -> None:
        self.launched = [a for a in self.launched if a.lower() != name.lower()]
        self._record("app.close", name.lower())

    def set_volume(self, delta: int) -> int:
        self.volume = max(0, min(100, self.volume + delta))
        self._record("volume.change", "system", delta=delta, now=self.volume)
        return self.volume

    def now(self) -> Dict[str, str]:
        t = time.localtime()
        self._record("clock.read", "now")
        return {"time": time.strftime("%H:%M", t),
                "date": time.strftime("%Y-%m-%d", t)}


class World:
    """One task's world. Created before the task, destroyed after it."""

    def __init__(self, root: Path, task_id: str = "") -> None:
        self.root = Path(root)
        self.task_id = task_id
        self.root.mkdir(parents=True, exist_ok=True)
        self.effects: List[Effect] = []
        self.files = FileStore(self, self.root / "home")
        self.notes = NoteStore(self)
        self.facts = FactStore(self)
        self.timers = TimerStore(self)
        self.system = SystemStore(self)

    # ---- what the scorer asks -------------------------------------------

    def did(self, kind: str, target: Optional[str] = None) -> bool:
        """Did this happen? The positive check."""
        return any(e.kind == kind and (target is None or e.target == target)
                   for e in self.effects)

    def did_not(self, kind: str, target: Optional[str] = None) -> bool:
        """Did this *not* happen? Needed by every task whose ideal is to ask
        before acting — clar-07 succeeds partly by deleting nothing."""
        return not self.did(kind, target)

    def effects_of(self, kind: str) -> List[Effect]:
        return [e for e in self.effects if e.kind == kind]

    def mutations(self) -> List[Effect]:
        """Effects that changed the world, as opposed to reading it. The
        distinction matters: a task whose ideal is to ask may legitimately
        look around first."""
        reads = {"file.list", "file.search", "file.read", "file.stat",
                 "note.list", "fact.recall", "clock.read"}
        return [e for e in self.effects if e.kind not in reads]

    def log(self) -> List[Dict[str, Any]]:
        return [asdict(e) for e in self.effects]

    def state(self) -> Dict[str, Any]:
        """A comparable summary, for before/after diffing."""
        return {
            "files": sorted(str(p.relative_to(self.files.root)).replace(os.sep, "/")
                            for p in self.files.root.rglob("*") if p.is_file()),
            "notes": [dict(n) for n in self.notes.notes],
            "facts": dict(self.facts.facts),
            "timers": [dict(t) for t in self.timers.timers],
            "volume": self.system.volume,
            "launched": list(self.system.launched),
        }

    # ---- lifecycle -------------------------------------------------------

    def close(self, keep: bool = False) -> None:
        if not keep:
            shutil.rmtree(self.root, ignore_errors=True)

    def __enter__(self) -> "World":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


def dump_effects(world: World, path: Path) -> None:
    """Persist the effect log beside the run row. Raw data is immutable
    (CHARTER §7), so this is written once and never edited."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"task_id": world.task_id, "effects": world.log(),
                   "final_state": world.state()}, fh, indent=2)
