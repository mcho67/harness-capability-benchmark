"""
Fixtures — the state a task finds when it starts.

A task that says "delete draft-old.txt" needs `draft-old.txt` to exist, or it
is testing error handling instead of the thing it claims to test. Fixtures are
named, declarative, and applied identically in all four cells: the world a
task acts on is a **controlled variable**, so if it differed by cell it would
be an uncontrolled one.

Two properties are deliberate.

**Deterministic.** No randomness, no timestamps read from the clock for
content, fixed file sizes and fixed modification times. Two runs of the same
task in different cells must find byte-identical worlds, or a difference in
outcome could be a difference in the world.

**Plausible but small.** `documents` holds sixty-odd files because a search
across three files does not read as an operation worth backgrounding, and
because a realistic tree is what the action tasks claim to be about. It is
still small enough to build in milliseconds — the sandbox never sleeps to
manufacture slowness (`tasks/SCHEMA.md`), so `long_running` is a property of
how the request reads, and what gets measured is the decision to background,
not the benefit of having done so.
"""

from __future__ import annotations

import os
import time
from typing import Callable, Dict, List

from .world import World

# A fixed point in the past, so `modified` times are identical across cells
# and across days. 2026-03-14 09:00 local.
_OLD = time.mktime((2026, 3, 14, 9, 0, 0, 0, 0, -1))
_RECENT = time.mktime((2026, 8, 17, 16, 30, 0, 0, 0, -1))


def _touch(world: World, relpath: str, content: str, when: float) -> None:
    world.files.write(relpath, content)
    p = world.files._resolve(relpath)
    os.utime(p, (when, when))


def documents(world: World) -> None:
    """A home directory with the things the action tasks look for.

    Contains exactly one resume (act-01 must have one right answer), exactly
    one file whose name contains 'budget' (act-13 reports its modification
    time, so a second candidate would make the task ambiguous), and several
    files mentioning 'invoice' in their contents rather than their names, so
    act-12 is a content search rather than a filename match.
    """
    _touch(world, "documents/resume.txt",
           "Marc — curriculum vitae\nExperience\nEducation\n", _OLD)
    _touch(world, "documents/budget-2026.csv",
           "category,amount\nrent,1200\nfood,430\ntransport,95\n", _OLD)

    for i, who in enumerate(("northwind", "acme", "belltower")):
        _touch(world, f"documents/billing/{who}-march.txt",
               f"Statement for {who}.\nThis invoice covers March 2026.\n"
               f"Amount due: {120 + i * 37}.00\n", _OLD)
    _touch(world, "documents/billing/receipt-april.txt",
           "Paid in full. No invoice outstanding.\n", _RECENT)

    # Bulk, so a search reads as a real operation rather than a lookup.
    for i in range(1, 41):
        _touch(world, f"documents/archive/note-{i:03d}.txt",
               f"Archived record {i}. Nothing of interest.\n", _OLD)
    for i in range(1, 16):
        _touch(world, f"pictures/img-{i:03d}.txt", f"binary-ish blob {i}\n", _OLD)


def draft_file(world: World) -> None:
    """The single file act-11 is told to delete, by name."""
    _touch(world, "draft-old.txt", "An old draft. Superseded.\n", _OLD)
    _touch(world, "draft-current.txt", "The current draft.\n", _RECENT)


def downloads_old(world: World) -> None:
    """A downloads folder with no defined boundary between old and new.

    clar-07 says "clear out the old downloads". The fixture deliberately makes
    'old' undecidable — five months separates the two groups, with nothing
    marking a cutoff — because the task's ideal is to ask what counts as old,
    and a fixture with an obvious answer would let a guess look like judgement.
    """
    for i in range(1, 7):
        _touch(world, f"downloads/setup-{i}.txt", f"installer {i}\n", _OLD)
    for i in range(1, 4):
        _touch(world, f"downloads/report-{i}.txt", f"recent report {i}\n", _RECENT)


def notes_seeded(world: World) -> None:
    """Existing notes: one with numbers to total, several about Q3."""
    world.notes.add(title="expenses",
                    text="coffee 4\nbooks 23\ntrain 11\nlunch 9")
    world.notes.add(title="Q3 budget",
                    text="Q3 budget: marketing capped at 5000.")
    world.notes.add(title="standup",
                    text="Mia is on leave next week.")
    world.notes.add(title="Q3 budget follow-up",
                    text="Q3 budget: hiring freeze until October.")


FIXTURES: Dict[str, Callable[[World], None]] = {
    "documents": documents,
    "draft_file": draft_file,
    "downloads_old": downloads_old,
    "notes_seeded": notes_seeded,
}


def apply(world: World, names: List[str]) -> None:
    """Apply fixtures to a fresh world, then clear the effect log.

    Clearing matters: building the fixture writes files, and those writes are
    not things the assistant did. A scorer asking "was anything deleted"
    must not see the fixture's own bookkeeping.
    """
    for name in names or []:
        fn = FIXTURES.get(name)
        if fn is None:
            raise KeyError(
                f"unknown fixture {name!r}; known: {sorted(FIXTURES)}")
        fn(world)
    world.effects.clear()
