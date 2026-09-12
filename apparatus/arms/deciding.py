"""
The deciding design: perceive -> decide -> act -> repeat, until done.

The treatment condition of the architecture factor. The model sees the
request, chooses whether to act, sees what happened, and chooses again. It
ends the turn itself, by answering instead of calling a tool.

Read alongside `routing.py`. Same prompt, same 21 actions in the same order,
same dispatch, same world, same trace — all in `base.py`. What is here and
not there is the loop, and one tool that touches nothing.

**Three properties make this a loop rather than a better router**, mirroring
the three that make the other file a pipeline:

1. **N model calls.** Every tool result goes back to the model, so the model
   composes the final answer having seen what the tools returned. The extra
   calls are the loop's cost and are metered per turn; `docs/protocol.md` §6c
   reports them as the price of any success recovered, never as success.
2. **Every requested tool runs.** Three tool calls in one response means
   three dispatches, so decomposition is available without a plan step.
3. **`ask_user`.** The only tool either arm has that the other lacks. It
   touches no part of the world — it ends the turn with a question — which is
   why it does not reintroduce the tool-availability confound that the
   closest published comparison reports as its own first limitation. The
   argument is set out in full in `base.py`.

**How this arm asks.** Two paths:

- the model calls `ask_user`, having judged the request underspecified
  -> `model`
- a required argument is missing, so `dispatch` returns `needs` -> `rule`.
  This arm gets the rule-driven path too, identically, because it is a
  property of the shared action set rather than of either design.

The contrast with `routing.py` is therefore not *whether* an arm can ask but
what makes it: a model's judgement, whose coverage moves when the model is
swapped, against a rule, whose coverage was fixed at design time and does
not. How each responds to the deployment switch is the result. No direction
is asserted anywhere in this file or the protocol; the sign comes from the
data.
"""

from __future__ import annotations

from typing import Any, Dict, List

from core.llm.types import assistant, tool_result

from .base import (MAX_ITERATIONS, SYSTEM_PROMPT, Arm, DecisionTrace,
                   TurnResult)

# Described by its mechanics, not by advice. "Use this instead of guessing"
# would be an instruction about *when* to ask, and when to ask is the
# measured decision — CHARTER §7, and the note on the system prompt in
# `base.py`. The routing arm needs no counterpart schema: its model asks by
# writing a question on the conversation route, which this arm's model can
# also do.
ASK_USER = {
    "name": "ask_user",
    "description": ("Put a question to the user. The turn ends and the user "
                    "answers next; nothing else happens."),
    "input_schema": {
        "type": "object",
        "properties": {
            "question": {"type": "string",
                         "description": "the question to put to the user"},
        },
        "required": ["question"],
    },
}


class DecidingArm(Arm):
    """perceive -> decide -> act -> repeat."""

    name = "deciding"

    def schemas(self) -> List[Dict[str, Any]]:
        return super().schemas() + [ASK_USER]

    def take_turn(self, text: str) -> TurnResult:
        trace = DecisionTrace()
        completions = []
        messages = self.conversation.user_says(text)
        reply = ""

        for iteration in range(1, MAX_ITERATIONS + 1):
            trace.iterations = iteration
            completion = self.provider.complete(
                system=SYSTEM_PROMPT, messages=messages, tools=self.schemas())
            completions.append(completion)

            # No tool call is how the model says it is done. The turn ends on
            # the model's decision rather than on a step count, which is the
            # property that makes this a loop.
            if not completion.tool_calls:
                reply = completion.text
                break

            messages = messages + [assistant(completion.text,
                                             completion.tool_calls)]

            asked = False
            for call in completion.tool_calls:
                if call.name == ASK_USER["name"]:
                    # The question is the answer. Any tool call the model put
                    # alongside it is abandoned unrun: it asked, so it does
                    # not also act, and the effect log has to be able to
                    # confirm that nothing happened.
                    reply = str(call.arguments.get("question") or "").strip()
                    trace.note_ask("model")
                    asked = True
                    break
                messages = messages + [
                    tool_result(call, self.run_action(
                        trace, call.name, call.arguments))]
            if asked:
                break
        else:
            # The cap bound. Recorded, never hidden: a turn that ran out of
            # iterations is a degradation event, and the last thing the model
            # said is reported as the answer so the row is still scoreable.
            trace.hit_iteration_cap = True
            reply = completions[-1].text if completions else ""

        return self.finish(reply, trace, completions)


__all__ = ["DecidingArm", "ASK_USER"]
