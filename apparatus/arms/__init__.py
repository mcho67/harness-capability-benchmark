"""
The two assistant designs. One factor of the 2x2; `core.llm` carries the
other. `build_arm` is the only construction path, so a cell cannot acquire an
arm the harness did not name.
"""

from __future__ import annotations

from typing import Any

from .base import (MAX_ITERATIONS, SYSTEM_PROMPT, Arm, DecisionTrace,
                   TurnResult)
from .deciding import DecidingArm
from .routing import RoutingArm

ARMS = {"routing": RoutingArm, "deciding": DecidingArm}


def build_arm(architecture: str, provider: Any, world: Any) -> Arm:
    if architecture not in ARMS:
        raise ValueError(
            f"unknown architecture {architecture!r}; "
            f"the 2x2 has exactly {sorted(ARMS)}")
    return ARMS[architecture](provider, world)


__all__ = ["ARMS", "build_arm", "Arm", "RoutingArm", "DecidingArm",
           "DecisionTrace", "TurnResult", "SYSTEM_PROMPT",
           "MAX_ITERATIONS"]
