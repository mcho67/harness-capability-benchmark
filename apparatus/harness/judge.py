"""
The judged scorer, blind to the cell by construction.

33 of the 48 tasks are rubric-scored — every action, clarification and
robustness task, which is to say every category the architecture argument
rests on. The snapshot's `score.py` returned `unscored_rubric` for all of
them, so half the study could not be scored at all (`docs/harness.md` §5b).

**Blinding is structural, not procedural.** A grader that can see which arm
produced a transcript is not a grader, and "I was careful not to look" is not
a method. So the judge's only input type is `BlindCase`, whose fields are
enumerated below and include no cell, architecture, deployment, provider or
model. `score.py` builds it; there is no path by which a row reaches the
judge whole. `BlindCase.from_row` raises if a caller tries to smuggle one of
the forbidden fields through.

**The judge sees what happened, not what was claimed.** Alongside the reply
it gets the sandbox's list of mutations. Several rubrics turn on a side
effect — act-15 requires a new note to exist, clar-07 requires that
*nothing* was deleted — and prose is not evidence of either. This is what
makes "it said it deleted the file" fail.

**The self-preference threat, stated rather than hidden.** The judge is
`claude-sonnet-4-6`, which is also the cloud treatment model. An LLM judge
preferring output from its own family is a documented effect, and here it
would push in a specific direction: toward the cloud cells, in both arms. It
is not confounded with *architecture*, so the primary interaction contrast
`(C3-C4) - (C1-C2)` is largely protected — the bias would have to differ
between arms to move it. The deployment main effect is not protected and is
reported with that caveat. Mitigations, all pre-registered: the judge is
blind; its rubric is the task's own pre-written criteria; and a random blind
human sample is rated and judge-human agreement is reported
(`docs/protocol.md` §10). If agreement is poor, that is a finding about the
measure and is published as one.
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from core.llm import build_provider
from core.llm.types import LLMConfig, LLMError

# One judge for the whole study, pinned like a cell is. Changing it after any
# data exists would mean two studies scored by two graders.
JUDGE_MODEL = "claude-sonnet-4-6"
JUDGE_PROVIDER = "anthropic"

VERDICTS = ("pass", "partial", "fail")

# Fields that would tell the judge which cell it is looking at. Named so the
# guard is a list someone can check rather than an intention.
FORBIDDEN = ("cell", "architecture", "deployment", "provider", "model_pinned",
             "models_reported", "run_id", "cost_usd", "model_calls")

JUDGE_SYSTEM = """You are grading one transcript from an assistant study \
against a criterion written before any transcript existed.

You will be given the user's turns, the assistant's final reply, the list of \
changes the assistant actually made to a sandboxed world, and the criterion.

Grade only against the criterion. Do not reward or penalise style, tone, \
length, formatting, or how impressive the answer sounds.

The list of world changes is evidence and the reply is a claim. If the \
criterion requires something to have happened, it must appear in the \
changes; if the criterion requires that nothing happened, the changes must \
be empty of it. A reply describing an action that is not in the list has not \
performed it.

Answer with the record_verdict tool.
  pass    — the criterion is met.
  partial — substantially attempted and partly met; a required element is
            missing or wrong.
  fail    — the criterion is not met."""

VERDICT_TOOL = {
    "name": "record_verdict",
    "description": "Record the grade for this transcript.",
    "input_schema": {
        "type": "object",
        "properties": {
            "verdict": {"type": "string", "enum": list(VERDICTS)},
            "reason": {"type": "string",
                       "description": "one sentence, citing the criterion"},
        },
        "required": ["verdict", "reason"],
    },
}


@dataclass(frozen=True)
class BlindCase:
    """Everything the judge may see, and nothing else.

    `case_id` is a hash, not a task id with a cell in it: two runs of the
    same task in different cells must be indistinguishable to the judge, and
    a readable id would leak ordering.
    """
    case_id: str
    turns: List[str]
    reply: str
    mutations: List[str]
    criteria: str

    @staticmethod
    def from_row(row: Dict[str, Any], task: Dict[str, Any]) -> "BlindCase":
        leaked = [f for f in FORBIDDEN if f in task]
        if leaked:
            raise ValueError(
                f"task record carries cell-identifying fields {leaked}; the "
                f"judge must not see them")
        criteria = (task.get("success") or {}).get("criteria", "")
        payload = json.dumps([task["id"], row.get("reply", ""),
                              sorted(row.get("mutations") or []), criteria],
                             sort_keys=True)
        return BlindCase(
            case_id=hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16],
            turns=list(task.get("turns") or []),
            reply=row.get("reply") or "",
            mutations=list(row.get("mutations") or []),
            criteria=criteria,
        )

    def prompt(self) -> str:
        turns = "\n".join(f"  user: {t}" for t in self.turns)
        muts = ("\n".join(f"  {m}" for m in self.mutations)
                or "  (nothing changed)")
        return (f"CONVERSATION\n{turns}\n\n"
                f"ASSISTANT'S FINAL REPLY\n  {self.reply}\n\n"
                f"CHANGES MADE TO THE WORLD\n{muts}\n\n"
                f"CRITERION\n  {self.criteria}")


class Judge:
    """Grades blind cases, caching by case hash.

    The cache is not an optimisation detail. Scoring is re-runnable from
    `runs.jsonl` (CHARTER §7), and without a cache each re-run would spend
    money and — worse — could return a different verdict for a transcript
    already graded, making `scored.jsonl` depend on when it was produced.
    """

    def __init__(self, cache_path: str, *, model: str = JUDGE_MODEL,
                 dry_run: bool = False) -> None:
        self.model = model
        self.dry_run = dry_run
        self.cache_path = cache_path
        self.cache: Dict[str, Dict[str, Any]] = self._load()
        self.calls = 0
        self.cost_usd = 0.0
        self._provider = None

    def _load(self) -> Dict[str, Dict[str, Any]]:
        if not os.path.exists(self.cache_path):
            return {}
        with open(self.cache_path, encoding="utf-8") as fh:
            return json.load(fh)

    def _save(self) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(self.cache_path)) or ".",
                    exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(self.cache, fh, indent=2, ensure_ascii=False)

    def provider(self):
        if self._provider is None:
            self._provider = build_provider(
                LLMConfig(provider=JUDGE_PROVIDER, model=self.model))
            self._provider.preflight()
        return self._provider

    def verdict(self, case: BlindCase) -> Dict[str, Any]:
        if case.case_id in self.cache:
            return self.cache[case.case_id]
        if self.dry_run:
            return {"verdict": "unjudged", "reason": "dry run",
                    "judge_model": self.model}

        provider = self.provider()
        try:
            completion = provider.complete(
                system=JUDGE_SYSTEM,
                messages=[{"role": "user", "content": case.prompt()}],
                tools=[VERDICT_TOOL],
            )
        except LLMError as exc:
            # An ungradeable row is recorded as ungradeable. Defaulting it to
            # `fail` would put the judge's outages into the results.
            return {"verdict": "judge_error", "reason": str(exc),
                    "judge_model": self.model}

        self.calls += 1
        self.cost_usd += completion.cost_usd
        out = self._read_verdict(completion)
        out["judge_model"] = completion.model_reported
        self.cache[case.case_id] = out
        self._save()
        return out

    @staticmethod
    def _read_verdict(completion: Any) -> Dict[str, Any]:
        for call in completion.tool_calls:
            if call.name == VERDICT_TOOL["name"]:
                verdict = str(call.arguments.get("verdict", "")).lower()
                if verdict in VERDICTS:
                    return {"verdict": verdict,
                            "reason": str(call.arguments.get("reason", ""))}
        # No usable tool call. Recorded as such rather than guessed from the
        # prose, because a graded outcome inferred from an ungraded response
        # is exactly the kind of soft failure this study is built against.
        return {"verdict": "judge_error",
                "reason": f"no verdict tool call; text was "
                          f"{(completion.text or '')[:120]!r}"}


__all__ = ["Judge", "BlindCase", "JUDGE_MODEL", "VERDICTS", "FORBIDDEN"]
