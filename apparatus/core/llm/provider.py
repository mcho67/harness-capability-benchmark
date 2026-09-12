"""
The provider seam — the one call path both arms share.

Both arms reach the model through `Provider.complete()` and nothing else.
That is what makes deployment a single switch: swapping cloud for local
changes which subclass is constructed and nothing about how either arm is
written.

Three rules are enforced here rather than trusted:

1. **One model per cell.** `_check_model` compares what the provider says
   answered against what the cell pinned, on every call, and raises on a
   mismatch. This is the direct guard against the defect the pilot found —
   the deciding arm ran Haiku 4.5 in a cell labelled Sonnet 4.6, and every
   recorded row said Sonnet (`apparatus/derive/FINDINGS.md`). A label is an
   intention; the response is evidence.

2. **Nothing adaptive.** No tier selection, no fallback model, no prompt
   caching, no speculative second call, no behaviour that depends on how
   earlier calls went. Retries exist, but only for transport failures, only
   with identical parameters, and the count is recorded so latency analysis
   can see them.

3. **Loud failure.** Every unrecoverable condition raises `LLMError`. A run
   that yields rows while the model was unreachable looks complete and is
   not.
"""

from __future__ import annotations

import abc
import time
from typing import Any, Dict, List, Optional

from .types import Completion, LLMConfig, LLMError, ModelMismatch

# USD per 1M tokens. Rates, not measurements — they are multiplied by token
# counts to produce the reported cost, so they must be checked against the
# provider's current published pricing before the run and recorded in the run
# manifest. Local inference bills no money; its cost is wall-clock, captured
# separately.
PRICING: Dict[str, Dict[str, float]] = {
    "claude-sonnet-4-6":          {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5-20251001":  {"input": 1.00, "output":  5.00},
}


def price(model: str, input_tokens: int, output_tokens: int) -> float:
    """Cost of one call, or 0.0 for a model with no published rate.

    A missing rate returns zero rather than guessing. Zero is visible in the
    data as an anomaly; an invented rate is not.
    """
    rate = PRICING.get(model)
    if rate is None:
        for known, r in PRICING.items():          # tolerate date suffixes
            if model.startswith(known) or known.startswith(model):
                rate = r
                break
    if rate is None:
        return 0.0
    return (input_tokens * rate["input"] + output_tokens * rate["output"]) / 1e6


def models_match(pinned: str, reported: str) -> bool:
    """Is the model that answered the model the cell pinned?

    Tolerant of version suffixes in either direction, because providers
    resolve an alias to a dated id. Intolerant of anything else — a fast-tier
    substitution is exactly what this is here to catch.
    """
    if not reported:
        return True                      # nothing reported: cannot contradict
    p, r = pinned.strip().lower(), reported.strip().lower()
    return p == r or p.startswith(r) or r.startswith(p)


class Provider(abc.ABC):
    """One model, one call path."""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self.calls = 0
        self.total_cost_usd = 0.0

    # ---- what subclasses implement -------------------------------------

    @abc.abstractmethod
    def _call(self, *, system: str, messages: List[Dict[str, Any]],
              tools: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """One request. Returns a dict with text, tool_calls, model,
        input_tokens, output_tokens, stop_reason. Raises on transport
        failure so the retry policy in `complete` can see it."""

    @abc.abstractmethod
    def preflight(self) -> None:
        """Fail now, loudly, if this cell cannot run — before any task does.

        CHARTER §7: a subsystem that cannot work must not produce rows that
        look complete. The trace ran for 108 rows with retrieval silently
        inert and reported zero degradation events; that must not recur.
        """

    # ---- the shared path -----------------------------------------------

    def complete(self, *, system: str = "",
                 messages: List[Dict[str, Any]],
                 tools: Optional[List[Dict[str, Any]]] = None) -> Completion:
        """The only way either arm reaches a model."""
        if not messages:
            raise LLMError("complete() called with no messages")

        last_exc: Optional[Exception] = None
        started = time.perf_counter()
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                raw = self._call(system=system, messages=messages, tools=tools)
                break
            except LLMError:
                raise                       # already a study-fatal condition
            except Exception as exc:        # transport only
                last_exc = exc
                if attempt == self.config.max_attempts:
                    raise LLMError(
                        f"{self.config.provider}/{self.config.model}: "
                        f"{self.config.max_attempts} attempts failed — "
                        f"{type(exc).__name__}: {exc}") from exc
                time.sleep(min(2.0 ** (attempt - 1), 8.0))
        else:                               # pragma: no cover
            raise LLMError(f"unreachable: {last_exc}")

        latency_s = time.perf_counter() - started
        reported = raw.get("model") or ""
        self._check_model(reported)

        in_tok = int(raw.get("input_tokens") or 0)
        out_tok = int(raw.get("output_tokens") or 0)
        cost = (0.0 if self.config.deployment == "local"
                else price(reported or self.config.model, in_tok, out_tok))

        self.calls += 1
        self.total_cost_usd += cost
        return Completion(
            text=raw.get("text") or "",
            tool_calls=list(raw.get("tool_calls") or []),
            model_reported=reported or self.config.model,
            input_tokens=in_tok,
            output_tokens=out_tok,
            latency_s=round(latency_s, 4),
            cost_usd=round(cost, 8),
            stop_reason=raw.get("stop_reason"),
            attempts=attempt,
        )

    def _check_model(self, reported: str) -> None:
        if models_match(self.config.model, reported):
            return
        raise ModelMismatch(
            f"model mismatch: the cell pinned {self.config.model!r} but "
            f"{reported!r} answered. This is the failure the pilot found — a "
            f"tier selector silently substituted a cheaper model while the "
            f"rows kept the pinned name. The run stops rather than record it."
        )
