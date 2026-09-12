"""
What both arms share, so that the diff between them is the manipulation.

`routing.py` and `deciding.py` are the experiment. Everything either of them
could differ in *except* control structure lives here: the system prompt, the
conversation state, the tool schemas, the trace record, and every proxy the
trace measures. The two arm files then contain a loop and a single pass, and
nothing else worth reading.

That is deliberate and it is the study's answer to the closest published
comparison, whose own first-listed limitation is that its baseline arm had
different tools available than the others (`docs/related_work.md` §6). Here
the answer to *"how do you know the difference is the architecture and not
that you wrote one arm better?"* is `diff arms/routing.py arms/deciding.py`.

**The one thing the arms do not share, and why it is not that confound.**
The deciding arm offers the model an `ask_user` tool; the routing arm does
not. This looks exactly like the confound above and is not, for a reason
worth stating rather than asserting: `ask_user` touches no part of the world.
All 21 world-touching actions are the same objects, in the same order, with
the same schemas, reached through the same `dispatch`. What differs is how a
question gets raised, which is the architecture variable itself — and the
routing arm is not thereby unable to ask. It has two other paths, both
pre-registered (`docs/protocol.md` §7): a rule firing, and the model simply
writing a question when the turn takes the conversation route. Both arms can
reach both `ask_origin` values. See `docs/harness.md` §5(a).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.llm import Provider
from core.llm.types import Completion, assistant, user
from core.skills import dispatch, tool_schemas

# ── the shared system prompt ─────────────────────────────────────────────
#
# Identical for both arms and both deployments. It is a controlled variable,
# so it is written once, here, and never varied per arm, per cell or per task
# (CHARTER §7: no per-task tuning).
#
# **What is in it, and why each line earns its place.**
#
# *Speech-ready prose.* The snapshot is a voice-first assistant and the
# response-length bands and naturalness proxies (`docs/protocol.md` §6d) are
# calibrated to spoken answers. Without this, half the measure would be
# whether a model defaults to bullet points.
#
# *The path convention.* Found in the end-to-end test of the action set: both
# models chose `delete_file` correctly for "delete the file called
# draft-old.txt", and then `claude-sonnet-4-6` guessed the convention right
# while `llama3.1:8b` emitted `/path/to/draft-old.txt`. Left unstated, several
# action tasks would measure whether a model can guess an undocumented path
# convention rather than whether it can choose and sequence tools, inflating
# the deployment effect for a reason nobody is interested in. A convention
# stated once, globally, for all 48 tasks is environment context and a
# control. The same sentence added because one task failed would be per-task
# tuning and is forbidden. Recorded in `derive/FINDINGS.md`.
#
# **What is deliberately NOT in it.** No instruction about when to ask, when
# to refuse, when to decompose, or when to defer long work. Those are the
# measured decisions. A prompt that told the model to "ask if the request is
# unclear" would hand the clarification result to the experimenter, and the
# fact that it would raise every arm's score equally is not a defence — it
# would replace the finding with an instruction-following check. The date is
# also absent, because `triv-02` asks for it and its ideal is to call `date`.

SYSTEM_PROMPT = """You are an assistant running on the user's own computer.

You speak your answers aloud, so reply in plain spoken prose: no markdown, no
bullet points, no headings, no code blocks. Keep it short.

You can act on the user's files, notes, timers and machine using the tools you
have been given. Use a tool when the request calls for one, and answer
directly when it does not.

File paths are relative to the user's home folder: `draft-old.txt` is a file
in the home folder and `documents/budget.csv` is inside the documents folder.
There is no drive letter and no leading slash."""

# The deciding arm's loop needs a bound. Fixed in advance at 8, before any
# data (CHARTER §7, and the standing rule that thresholds go in before
# results come out). Eight is above the longest ideal decomposition in the
# task set (act-15 needs two tools) with room for a model to look around
# first; hitting it is recorded as a degradation event rather than silently
# truncated.
MAX_ITERATIONS = 8

# **There is no risk-confirmation gate, and the reason is in the snapshot.**
#
# Withdrawn 2026-08-19 (pre-data), after it was written and before any data.
# `docs/protocol.md` §7 lists three routing ask paths, one of them the
# risk/confidence confirmation gate at `orchestrator.py:370-392`. It was
# implemented here as an always-confirm table over `delete_file` and
# `remove_note`. Checking that against the snapshot showed it wrong twice:
#
# - `state/models.py` `RISK_TABLE` classifies `remove_note` as **LOW**. The
#   risk was invented here, not carried over. (`clear_notes` is the MEDIUM
#   one, and the apparatus has no such action.)
# - `delete_file` is **MEDIUM**, and the snapshot's MEDIUM tier does not
#   always confirm. It confirms only when the routed intent's NLU confidence
#   is below 0.85 (`orchestrator.py:388`, `_CONFIDENCE_NEAR_CERTAIN`). The
#   always-confirm tier is HIGH/CRITICAL, whose only members anywhere in the
#   table are `delete_folder` and `system_shutdown` — neither of which is an
#   apparatus action.
#
# So the always-fire tier is **empty** in this reduction, and the conditional
# tier depends on a confidence score the apparatus does not produce: its
# router emits a tool call, not an intent with a probability. Keeping the
# gate would have meant shipping a risk table I wrote myself, wired to the
# arm the clarification category is sharpest on (clar-07). That is
# fabricating an architectural difference, which is worse than losing one.
#
# What is left is the honest observation that the MEDIUM tier's condition —
# consequential *and* the router is not near-certain — has an exact analogue
# already in the shared half: a required argument the model did not supply is
# the uncertainty signal, and `dispatch` already refuses to guess on it. The
# gate collapses into the `needs` path rather than adding to it.
#
# Routing therefore has two ask paths, not three: `needs` (rule) and the
# model writing a question on the conversation route (model). Both
# `ask_origin` values remain reachable by both arms — the smoke test
# observed `rule` and `model` in the deciding arm on the same task under
# different deployments — so nothing about the mechanism contrast depends on
# the gate. Filed as a pre-data scope reduction in `docs/protocol.md`
# alongside CHARTER §6's three.


# ── the decision trace ───────────────────────────────────────────────────

@dataclass
class DecisionTrace:
    """What the arm decided, per turn. `docs/harness.md` §5(a).

    Mechanically derived, never graded. The judged scorer (cell-blind) is the
    authority on `declined` and `backgrounded`; the proxies here exist so the
    mechanism analysis has a deterministic signal to compare a human rating
    against, and so a disagreement between them is visible.
    """
    tools: List[str] = field(default_factory=list)
    asked: bool = False
    ask_origin: str = "none"           # model | rule | none
    backgrounded: bool = False         # proxy — see `reads_as_deferred`
    declined: bool = False             # proxy — see `reads_as_declined`
    decomposed: bool = False
    model_calls: int = 0
    iterations: int = 0
    hit_iteration_cap: bool = False
    models_reported: List[str] = field(default_factory=list)

    # Failure modes kept apart on purpose. A model that picks the right tool
    # and mis-forms its argument has made a different error from one that
    # picks the wrong tool, and collapsing them into "used the wrong tool"
    # would charge a path-formatting slip to the decision. Found in the
    # action set's end-to-end test; see the path convention above.
    bad_arguments: int = 0             # right tool, argument the world refused
    missing_arguments: int = 0         # required argument absent -> rule ask
    unknown_tools: List[str] = field(default_factory=list)
    dropped_by_router: List[str] = field(default_factory=list)

    def note_ask(self, origin: str) -> None:
        """First origin wins. A rule that fires before the model gets to
        judge is what made this turn a question, and overwriting it with a
        later signal would report the wrong mechanism."""
        self.asked = True
        if self.ask_origin == "none":
            self.ask_origin = origin

    def as_row(self) -> Dict[str, Any]:
        return {
            "tools": list(self.tools),
            "asked": self.asked,
            "ask_origin": self.ask_origin,
            "backgrounded": self.backgrounded,
            "declined": self.declined,
            "decomposed": self.decomposed,
            "model_calls": self.model_calls,
            "iterations": self.iterations,
            "hit_iteration_cap": self.hit_iteration_cap,
            "models_reported": list(self.models_reported),
            "bad_arguments": self.bad_arguments,
            "missing_arguments": self.missing_arguments,
            "unknown_tools": list(self.unknown_tools),
            "dropped_by_router": list(self.dropped_by_router),
        }


@dataclass
class TurnResult:
    """One turn's answer, plus everything the harness meters."""
    text: str
    trace: DecisionTrace
    completions: List[Completion] = field(default_factory=list)

    @property
    def latency_s(self) -> float:
        return round(sum(c.latency_s for c in self.completions), 4)

    @property
    def cost_usd(self) -> float:
        return round(sum(c.cost_usd for c in self.completions), 8)

    @property
    def input_tokens(self) -> int:
        return sum(c.input_tokens for c in self.completions)

    @property
    def output_tokens(self) -> int:
        return sum(c.output_tokens for c in self.completions)


# ── proxies, and what they are not ───────────────────────────────────────
#
# Three ideal components cannot be read off a tool call, because the
# apparatus has no tool for them: asking in prose, declining, and deferring
# long work. Each gets a deterministic textual proxy here.
#
# A proxy is not the measurement. The cell-blind judged scorer decides
# `declined` and `backgrounded`; these exist so that (a) the trace carries a
# signal computed identically in all four cells, and (b) proxy-versus-rating
# disagreement is a number the paper can report rather than an unknown.
#
# `backgrounded` deserves the sharpest statement: the snapshot's background
# worker is removed and the sandbox completes instantly, so what is measured
# is **the stated decision to defer**, never the benefit of deferring. It is
# derived on two of the 48 tasks, is descriptive only, and carries no test
# and no conclusion (`tasks/SCHEMA.md`).

_QUESTION_END = re.compile(r"\?\s*$")

_DEFER_MARKERS = (
    "i'll start", "i will start", "i'll get started", "i'll work on",
    "i'll begin", "in the background", "while i work", "let you know",
    "come back to you", "report back", "this may take", "this will take",
    "i'll have that", "get back to you",
)

_DECLINE_MARKERS = (
    "i can't", "i cannot", "i'm not able", "i am not able", "i won't",
    "i will not", "i'm unable", "i am unable", "no way for me",
    "not something i can", "i don't have the ability", "i'd rather not",
)


def reads_as_question(text: str) -> bool:
    """A turn that ends on a question mark is putting a question to the user.

    Anchored at the end deliberately. A mid-answer rhetorical question, or a
    "would you like me to also…?" after the work is done, is not the arm
    asking before acting — and that distinction is the whole clarification
    category. Whether the question is the *right* one is the judged scorer's
    call, not this function's.
    """
    return bool(_QUESTION_END.search((text or "").strip()))


def reads_as_deferred(text: str) -> bool:
    t = (text or "").lower()
    return any(m in t for m in _DEFER_MARKERS)


def reads_as_declined(text: str) -> bool:
    t = (text or "").lower()
    return any(m in t for m in _DECLINE_MARKERS)


# ── the shared turn machinery ────────────────────────────────────────────

class Conversation:
    """Transcript state for one task.

    Context carries **within** a task and never across one. CHARTER §7 puts
    the isolation boundary at the task rather than the turn because the
    grounding category depends on carry-over inside a task, and because the
    pilot found a fact learned in one task appearing in the prompt of an
    unrelated later one. A fresh `Conversation` and a fresh `World` per task
    is what stops that being possible rather than merely avoided.
    """

    def __init__(self) -> None:
        self.messages: List[Dict[str, Any]] = []

    def user_says(self, text: str) -> List[Dict[str, Any]]:
        """The messages for this turn: everything so far, plus the new turn.

        Returns a copy. An arm may append tool traffic to what it gets back
        without that traffic entering the stored transcript — the loop's
        intermediate steps are its own business, and letting them persist
        would make the two arms' *inputs* diverge turn by turn.
        """
        return self.messages + [user(text)]

    def turn_done(self, text: str, reply: str) -> None:
        self.messages.append(user(text))
        self.messages.append(assistant(reply))


class Arm:
    """One assistant design. Subclasses implement `take_turn` and nothing
    else — every other member is here so it cannot vary between them."""

    name = "?"

    def __init__(self, provider: Provider, world: Any) -> None:
        self.provider = provider
        self.world = world
        self.conversation = Conversation()

    # -- what the subclass writes -----------------------------------------

    def take_turn(self, text: str) -> TurnResult:      # pragma: no cover
        raise NotImplementedError

    # -- what neither subclass may vary -----------------------------------

    def schemas(self) -> List[Dict[str, Any]]:
        """The 21 world-touching actions, same objects, same order."""
        return tool_schemas()

    def run_action(self, trace: DecisionTrace, name: str,
                   arguments: Dict[str, Any]) -> str:
        """Dispatch one action and record what it cost the trace to learn.

        Both arms reach every action through here, so tool accounting cannot
        differ between them either.
        """
        result = dispatch(self.world, name, dict(arguments or {}))
        if result.data.get("unknown_action"):
            trace.unknown_tools.append(name)
            return result.text
        trace.tools.append(name)
        if result.needs:
            trace.missing_arguments += len(result.needs)
            trace.note_ask("rule")
        elif not result.ok:
            trace.bad_arguments += 1
        return result.text

    def finish(self, text: str, trace: DecisionTrace,
               completions: List[Completion]) -> TurnResult:
        """Close out a turn: fill the text-derived proxies, count the
        distinct tools, and record which models actually answered."""
        trace.decomposed = len(set(trace.tools)) > 1
        trace.backgrounded = reads_as_deferred(text)
        trace.declined = reads_as_declined(text)
        trace.model_calls = len(completions)
        trace.models_reported = [c.model_reported for c in completions]
        if reads_as_question(text):
            trace.note_ask("model")
        return TurnResult(text=text, trace=trace, completions=completions)

    def run_task(self, turns: List[str]) -> List[TurnResult]:
        """Every turn of one task, in order, sharing one conversation and one
        world. The harness scores the last turn; the earlier ones are what
        the grounding category is made of."""
        out = []
        for t in turns:
            result = self.take_turn(t)
            self.conversation.turn_done(t, result.text)
            out.append(result)
        return out


__all__ = ["SYSTEM_PROMPT", "MAX_ITERATIONS", "Arm",
           "Conversation", "DecisionTrace", "TurnResult", "reads_as_question",
           "reads_as_deferred", "reads_as_declined"]
