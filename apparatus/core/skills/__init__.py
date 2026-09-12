"""
core.skills — the fixed action set, and the one way to invoke it.

Both arms call `dispatch`. Neither arm reaches an action any other way, and
neither arm can see an action the other cannot: `tool_schemas()` returns the
same list to both, in the same order, built from the same specs.

    from core.skills import ACTION_SET, tool_schemas, dispatch
    result = dispatch(world, "set_timer", {"duration": "5 minutes"})

`dispatch` enforces the one rule that has to hold before any arm-specific
logic runs: **a required argument that is missing is a clarification, not a
guess.** The action does not run, and the result carries `needs`. Both arms
see that identically — it is the rule-driven ask the pilot found in the
routing arm, and it is why `ask_origin` distinguishes `rule` from `model`.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..sandbox import World
from .actions import build_action_set, parse_duration
from .base import (CATEGORIES, SkillResult, ToolSpec, missing_args,
                   phrase_needs)

ACTION_SET: Dict[str, ToolSpec] = build_action_set()


def tool_schemas(names: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """The tool definitions handed to the model.

    Order is the declaration order of the action set, not a set iteration or
    a per-arm choice — tool order can influence which tool a model reaches
    for, so a difference in order between arms would be a difference in the
    architecture variable.
    """
    wanted = names if names is not None else list(ACTION_SET)
    return [ACTION_SET[n].schema() for n in wanted if n in ACTION_SET]


def dispatch(world: World, name: str, args: Optional[Dict[str, Any]] = None
             ) -> SkillResult:
    """Run one action against one world.

    Unknown actions return a failed result rather than raising: a model
    inventing a tool name is behaviour to record, not a crash. A *missing
    world* would be a harness bug and does raise.
    """
    if world is None:
        raise ValueError("dispatch requires a world")
    args = dict(args or {})
    spec = ACTION_SET.get(name)
    if spec is None:
        return SkillResult(f"I don't have a way to do {name!r}.", ok=False,
                           data={"unknown_action": name})

    needs = missing_args(spec, args)
    if needs:
        return SkillResult(phrase_needs(spec, needs), ok=True, needs=needs,
                           data={"action": name})

    accepted = {k: v for k, v in args.items() if k in spec.properties}
    try:
        return spec.run(world, **accepted)
    except TypeError as exc:                 # a bad call shape from the model
        return SkillResult(f"I couldn't run {name}: {exc}", ok=False,
                           data={"action": name})


def categories_covered() -> Dict[str, List[str]]:
    """Which pre-registered category each action serves.

    CHARTER §5 says skills earn their place by task category. This makes that
    auditable in one call instead of by reading the charter and trusting it.
    """
    out: Dict[str, List[str]] = {c: [] for c in CATEGORIES}
    for spec in ACTION_SET.values():
        out[spec.category].append(spec.name)
    return out


__all__ = ["ACTION_SET", "tool_schemas", "dispatch", "categories_covered",
           "SkillResult", "ToolSpec", "parse_duration", "CATEGORIES"]
