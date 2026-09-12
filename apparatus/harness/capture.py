"""
One run, one row, written once.

CHARTER §7: raw data is immutable, and the pipeline is
`runs -> scored -> rated -> figures` with each step writing a new file and
re-runnable from the one before. This module owns the first arrow only. It
writes `runs.jsonl` and never reads a score, a rating or a figure.

**Why the row carries so much.** A row has to be enough on its own to answer
"what actually happened here" a year later, without the code that produced
it. In particular it carries what the trace found the snapshot getting wrong:

- `models_reported` — which model *answered*, read from each provider
  response, never copied from the cell label. The pilot found a tier selector
  sending a cell labelled Sonnet 4.6 to Haiku 4.5 while every row said
  Sonnet.
- `tasks_sha256` and `baseline_commit` — the row states which task set and
  which instrument produced it, so reproducibility is a property of the data
  rather than a claim in a document.
- `effects` and `final_state` — what the world says happened, not what the
  assistant said happened. Absence is checkable, which several clarification
  tasks require.
- `degradation` — every event that made a run less than clean. The pilot ran
  108 rows with a subsystem silently inert and reported zero degradation
  events; a row that looks complete while something was off is worse than no
  row.

**Append-only, flushed per row.** A long run that crashes at task 400 must
lose nothing and must be resumable from what it wrote (`docs/harness.md` §7).
`RunLog.done()` is what a cell consults to skip work already on disk.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

SCHEMA_VERSION = 1


def baseline_commit(repo_root: str) -> str:
    """The commit the instrument was at. Recorded per row.

    Dirty working trees are marked. A row produced from uncommitted code is
    not reproducible, and saying so in the data is better than discovering it
    at analysis time.
    """
    try:
        head = subprocess.run(["git", "-C", repo_root, "rev-parse", "HEAD"],
                              capture_output=True, text=True, timeout=10)
        if head.returncode != 0:
            return "unknown"
        sha = head.stdout.strip()
        dirty = subprocess.run(["git", "-C", repo_root, "status", "--porcelain"],
                               capture_output=True, text=True, timeout=10)
        return sha + ("-dirty" if dirty.stdout.strip() else "")
    except (OSError, subprocess.SubprocessError):
        return "unknown"


@dataclass
class TurnRow:
    """One turn inside one run. Multi-turn tasks have several."""
    index: int
    user: str
    reply: str
    decision: Dict[str, Any]
    latency_s: float
    cost_usd: float
    input_tokens: int
    output_tokens: int


@dataclass
class RunRow:
    """One task, run once, in one cell.

    `decision` is the **last** turn's trace. That is the scored turn: earlier
    turns of a grounding task exist to be carried, not to be graded. Every
    turn's trace is still kept in `turns`, so a per-turn analysis stays
    possible without re-running anything.
    """
    run_id: str
    cell: str
    architecture: str
    deployment: str
    provider: str
    model_pinned: str
    repetition: int
    order_index: int
    order_seed: int
    task_id: str
    category: str
    difficulty: int

    turns: List[Dict[str, Any]] = field(default_factory=list)
    reply: str = ""
    decision: Dict[str, Any] = field(default_factory=dict)

    models_reported: List[str] = field(default_factory=list)
    effects: List[Dict[str, Any]] = field(default_factory=list)
    final_state: Dict[str, Any] = field(default_factory=dict)
    mutations: List[str] = field(default_factory=list)

    latency_s: float = 0.0
    cost_usd: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    model_calls: int = 0

    degradation: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None

    started_at: str = ""
    wall_s: float = 0.0
    baseline_commit: str = ""
    tasks_sha256: str = ""
    schema_version: int = SCHEMA_VERSION

    @property
    def key(self) -> Tuple[str, str, int]:
        """What makes a run unique. Used for resume and duplicate detection."""
        return (self.cell, self.task_id, self.repetition)

    def note_degradation(self, kind: str, detail: str = "", **extra: Any) -> None:
        self.degradation.append({"kind": kind, "detail": detail, **extra})


class RunLog:
    """Append-only JSONL, flushed per row.

    Opened in append mode on purpose: reopening an existing log continues it
    rather than truncating it. There is no method to modify or delete a row,
    because there is no legitimate reason to have one.
    """

    def __init__(self, path: str) -> None:
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        self._fh = open(path, "a", encoding="utf-8")
        self._written: Set[Tuple[str, str, int]] = set()

    # -- resume ------------------------------------------------------------

    def done(self) -> Set[Tuple[str, str, int]]:
        """Keys already on disk, so a resumed cell can skip them.

        Reads the file rather than trusting this process's memory: the point
        of resume is that the previous process died.
        """
        keys: Set[Tuple[str, str, int]] = set()
        if not os.path.exists(self.path):
            return keys
        with open(self.path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except ValueError:
                    # A row half-written by a killed process. Skipping it
                    # means it is re-run, which is correct: a truncated row
                    # is not data.
                    continue
                keys.add((row.get("cell", ""), row.get("task_id", ""),
                          int(row.get("repetition", 0))))
        self._written |= keys
        return keys

    # -- write -------------------------------------------------------------

    def write(self, row: RunRow) -> None:
        if row.key in self._written:
            raise ValueError(
                f"refusing to write a duplicate row for {row.key}. A run is "
                f"identified by (cell, task, repetition); writing it twice "
                f"would double-count it in every downstream analysis.")
        self._fh.write(json.dumps(asdict(row), ensure_ascii=False) + "\n")
        self._fh.flush()
        os.fsync(self._fh.fileno())
        self._written.add(row.key)

    def close(self) -> None:
        self._fh.close()

    def __enter__(self) -> "RunLog":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


def read_rows(path: str) -> List[Dict[str, Any]]:
    """Every complete row in a log. The entry point for `score.py`."""
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    return out


__all__ = ["RunRow", "TurnRow", "RunLog", "read_rows", "baseline_commit",
           "SCHEMA_VERSION"]
