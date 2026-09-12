"""
What an action is, and what it hands back.

One `ToolSpec` per action, authored once. The deciding arm offers the specs
to the model as tools; the routing arm dispatches to them after classifying.
Same objects, same schemas, same implementations, same world — the arms
differ in *when and how* they choose an action, never in which actions exist.

That is the guarantee `core/` is for, and it is the thing the closest
published comparison got wrong: its baseline arm had different tools
available than the others, so loop structure was confounded with tool
availability (`docs/related_work.md` §6).

**What is deliberately not here: asking.** `ask_user` is not an action,
because it does not touch the world. Asking is a property of the control
structure, so it lives in the arms — which is where the architecture
variable lives. Keeping it out of the shared set is what lets `ACTION_SET`
be *identical* rather than merely similar.

What both arms do share is the **rule-driven** half of asking: a `ToolSpec`
declares its required arguments, and `dispatch` refuses to run without them,
returning `needs` instead of guessing. Both arms see that identically. It is
the mechanism the pilot found in the routing arm (`orchestrator.py:454`, a
skill returning `requires_followup`), and it is recorded as `ask_origin=rule`
to keep it distinct from a model deciding on its own that it should ask.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Tuple

# The six pre-registered task categories (protocol §7). Every action names
# the one that justifies it, so CHARTER §5 -- "skills earn their place by
# task category" -- is checkable in code rather than asserted in a document.
CATEGORIES = ("trivial", "reasoning", "action",
              "clarification", "grounding", "robustness")


@dataclass(frozen=True)
class SkillResult:
    """The outcome of one action.

    `needs` is the rule-driven clarification: a non-empty tuple means the
    action refused to run because a required argument was absent. It is not
    an error — refusing to guess is the correct behaviour, and for several
    tasks it is the ideal one.
    """
    text: str
    ok: bool = True
    needs: Tuple[str, ...] = ()
    data: Dict[str, Any] = field(default_factory=dict)

    @property
    def asked(self) -> bool:
        return bool(self.needs)


@dataclass(frozen=True)
class ToolSpec:
    """One action, described once for both arms and both models."""
    name: str
    description: str
    properties: Dict[str, Dict[str, Any]]
    required: Tuple[str, ...]
    run: Callable[..., SkillResult]
    category: str
    justification: str

    def __post_init__(self) -> None:
        if self.category not in CATEGORIES:
            raise ValueError(
                f"{self.name}: category {self.category!r} is not a "
                f"pre-registered task category (CHARTER §5)")
        missing = [r for r in self.required if r not in self.properties]
        if missing:
            raise ValueError(f"{self.name}: required args not declared: {missing}")

    def schema(self) -> Dict[str, Any]:
        """Anthropic tool shape. `core.llm.ollama_provider` translates it for
        the local model, so neither arm nor either model ever sees a
        hand-written variant."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": dict(self.properties),
                "required": list(self.required),
            },
        }


def missing_args(spec: ToolSpec, args: Dict[str, Any]) -> Tuple[str, ...]:
    """Required arguments that are absent or empty.

    Empty counts as absent on purpose: a model that calls delete_file with
    path="" has not supplied a path, and running on it would turn a
    clarification case into an error case.
    """
    out = []
    for r in spec.required:
        v = args.get(r)
        if v is None or (isinstance(v, str) and not v.strip()):
            out.append(r)
    return tuple(out)


def phrase_needs(spec: ToolSpec, needs: Tuple[str, ...]) -> str:
    """The question the rule-driven path asks. Deterministic, so it is the
    same sentence in every cell and cannot itself become a variable."""
    labels = [spec.properties.get(n, {}).get("description", n) for n in needs]
    if len(labels) == 1:
        return f"I need to know: {labels[0]}."
    return "I need to know: " + "; ".join(labels[:-1]) + f"; and {labels[-1]}."
