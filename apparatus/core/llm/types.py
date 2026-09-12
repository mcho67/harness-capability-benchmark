"""
The data that crosses the model seam.

One request shape and one response shape, identical for both providers and
both arms. If an arm could see a provider-specific field, the provider would
be part of the architecture variable instead of the deployment variable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class LLMError(RuntimeError):
    """A call that could not be completed as specified.

    Raised rather than returned. CHARTER §7 requires missing capability to
    be a loud failure: a run that produces rows while the model was
    unreachable, or while a different model answered, looks complete and is
    not. The harness catches this at the task boundary and aborts the cell.
    """


class ModelMismatch(LLMError):
    """A different model answered than the cell pinned.

    Split out from `LLMError` 2026-08-19 (pre-data) so the harness can tell
    two failures apart that are not alike:

    - **This cell is invalid.** A different model answered, or the provider
      cannot be reached at all. Every row the cell has written is suspect,
      so the run aborts. This is the tier confound the pilot found
      (`apparatus/derive/FINDINGS.md`) and CHARTER §7's "one model per cell".
    - **This task degraded.** The pinned model timed out or errored on one
      hard task after its retries. That is a result — `docs/harness.md` §7
      requires it recorded as a fail with a degradation note, never a hang —
      and the cell continues.

    Collapsing them would mean either aborting a whole cell over one slow
    local answer, or recording rows a substituted model produced.
    """


@dataclass(frozen=True)
class ToolCall:
    """A tool the model asked to run."""
    id: str
    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Completion:
    """One model response.

    `model_reported` is the field that exists because of the tier confound
    (`apparatus/derive/FINDINGS.md`). It is what the provider said answered
    the call, read from the response body — never the configured name, never
    the cell label. Every downstream row carries it, so "which model actually
    answered" is data rather than an assumption.
    """
    text: str
    tool_calls: List[ToolCall]
    model_reported: str
    input_tokens: int
    output_tokens: int
    latency_s: float
    cost_usd: float
    stop_reason: Optional[str] = None
    attempts: int = 1

    @property
    def wanted_tools(self) -> bool:
        return bool(self.tool_calls)


@dataclass(frozen=True)
class LLMConfig:
    """Everything the seam needs, fixed for the whole cell.

    There is no fast/smart pair and no fallback model, deliberately: the
    snapshot's tier selector routed the deciding arm to a cheaper model than
    the routing arm while both cells recorded the same model name. One cell,
    one model, asserted on every response.
    """
    provider: str                 # "anthropic" | "ollama"
    model: str                    # the single pinned model
    temperature: float = 0.0
    max_tokens: int = 1024
    timeout_s: float = 120.0
    max_attempts: int = 3         # transport retries only, same model, same params
    base_url: str = "http://localhost:11434"
    api_key: Optional[str] = None

    def __post_init__(self) -> None:
        if self.provider not in ("anthropic", "ollama"):
            raise LLMError(f"unknown provider: {self.provider!r}")
        if not self.model:
            raise LLMError("no model pinned; the cell must name exactly one")
        if self.temperature != 0.0:
            # Not forbidden, but it must be a deliberate act: the study
            # compares designs, and sampling noise is not a design.
            raise LLMError(
                f"temperature is {self.temperature}, expected 0.0. Change this "
                "only with a dated pre-data amendment.")

    @property
    def deployment(self) -> str:
        return "local" if self.provider == "ollama" else "cloud"


# ── the neutral transcript ───────────────────────────────────────────────
#
# Added 2026-08-19 (pre-data), while building the arms. The two providers
# want tool results in different shapes: Anthropic as `tool_result` content
# blocks inside a user message, Ollama as a `tool` role. If an arm built
# either shape, the arm would know which deployment it was running under —
# and deployment would have leaked into the architecture variable, which is
# the one thing `core/` exists to prevent.
#
# So the arms speak this shape and only this shape, and each provider
# translates it in `_call`. An arm that cannot name a provider cannot differ
# by one.
#
#   {"role": "user",      "content": str}
#   {"role": "assistant", "content": str, "tool_calls": [ToolCall, ...]}
#   {"role": "tool",      "tool_call_id": str, "name": str, "content": str}


def user(content: str) -> Dict[str, Any]:
    return {"role": "user", "content": str(content)}


def assistant(content: str = "",
              tool_calls: Optional[List[ToolCall]] = None) -> Dict[str, Any]:
    return {"role": "assistant", "content": str(content),
            "tool_calls": list(tool_calls or [])}


def tool_result(call: ToolCall, content: str) -> Dict[str, Any]:
    return {"role": "tool", "tool_call_id": call.id, "name": call.name,
            "content": str(content)}
