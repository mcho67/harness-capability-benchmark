"""
The routing design: classify -> one skill -> respond. One pass, no loop.

This is the conventional assistant pipeline and the control condition of the
architecture factor. A turn arrives, one classification happens, at most one
skill runs, and the skill's own answer is the reply. Nothing observes the
result and decides what to do next, because there is no next.

Read alongside `deciding.py`. The two files differ in control structure and
nothing else — same prompt, same 21 actions in the same order, same dispatch,
same world, same trace, all of it in `base.py`.

**Three properties make this a pipeline rather than a crippled loop**, and
each is a design decision rather than an omission:

1. **One model call.** The classification *is* the model call; there is no
   second call to phrase the answer. A pipeline that consulted the model
   again after seeing a tool result would be a two-step loop.
2. **At most one skill.** A router emits one intent. If the model asks for
   three tools, the first is honoured and the rest are recorded in
   `dropped_by_router` — dropped, not queued. That count is data: it says how
   often the single-dispatch limit actually bound, which is the difference
   between "routing decomposed less" and "routing was not allowed to".
3. **The skill's text is the reply.** In the snapshot the orchestrator
   returns what the skill returned, so a routed turn answers in the skill's
   voice rather than the model's. That is why the naturalness measure has
   something to find, and it is not a handicap added here — it is what the
   design is.

**How this arm asks.** Two paths, one rule and one model:

- a required argument is missing, so `dispatch` returns `needs`
  (`orchestrator.py:454`, a skill returning `requires_followup`) -> `rule`
- the turn routes to conversation and the model writes a question -> `model`

So this arm reaches both `ask_origin` values, and the withdrawn claim that a
pipeline structurally cannot ask is not quietly reintroduced here. What
differs from `deciding.py` is *what makes it ask*, which is the measurement.

`docs/protocol.md` §7 lists a third path — the risk/confidence confirmation
gate. It was implemented here and then withdrawn on 2026-08-19, pre-data,
because the snapshot's own risk table does not support it in this reduction.
The reasoning is in `base.py` where the gate used to be; the short version is
that reproducing it would have meant inventing a risk table.
"""

from __future__ import annotations

from typing import List

from .base import SYSTEM_PROMPT, Arm, DecisionTrace, TurnResult


class RoutingArm(Arm):
    """classify -> one skill -> respond."""

    name = "routing"

    def take_turn(self, text: str) -> TurnResult:
        trace = DecisionTrace()
        completions = []

        completion = self.provider.complete(
            system=SYSTEM_PROMPT,
            messages=self.conversation.user_says(text),
            tools=self.schemas(),
        )
        completions.append(completion)
        trace.iterations = 1

        # No tool wanted: the turn took the conversation route, and the
        # model's own text is the answer. This is the path that lets a
        # pipeline ask with ask_origin=model, and the path every reasoning
        # and grounding task takes in both arms — which is what keeps those
        # categories a control on the architecture factor rather than a
        # second measurement of it.
        if not completion.tool_calls:
            return self.finish(completion.text, trace, completions)

        call, *dropped = completion.tool_calls
        trace.dropped_by_router = [c.name for c in dropped]

        reply = self.run_action(trace, call.name, call.arguments)
        return self.finish(reply, trace, completions)


__all__ = ["RoutingArm"]
