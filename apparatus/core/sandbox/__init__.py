"""
core.sandbox — the disposable world a task acts on, and the record of what
it did to that world.

    from core.sandbox import new_world
    with new_world("act-11", base_dir, fixtures=["draft_file"]) as w:
        ...                                   # the arm runs
        w.did("file.delete", "draft-old.txt") # the scorer asks
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import List, Optional

from .fixtures import FIXTURES, apply
from .world import Effect, SandboxError, World, dump_effects


def new_world(task_id: str, base_dir, *,
              fixtures: Optional[List[str]] = None) -> World:
    """A fresh world for one task.

    `base_dir` is passed in, never derived: CHARTER §7 forbids the apparatus
    writing inside its own tree, and the snapshot's habit of putting its
    database next to `config.py` is exactly the defect being avoided.

    The directory name carries a uuid so two cells running the same task
    concurrently cannot collide, and so a leftover directory from a crashed
    run is never silently reused.
    """
    root = Path(base_dir) / f"{task_id or 'task'}-{uuid.uuid4().hex[:8]}"
    world = World(root, task_id=task_id)
    apply(world, fixtures or [])
    return world


__all__ = ["new_world", "World", "Effect", "SandboxError",
           "dump_effects", "FIXTURES", "apply"]
