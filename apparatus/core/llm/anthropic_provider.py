"""
The cloud half of the seam.

Deliberately thinner than the snapshot's provider. Prompt caching is not used
here: it is a cloud-only latency and cost advantage with no local counterpart,
and the snapshot's cache-warming path is one of the three adaptive mechanisms
CHARTER §7 removes. Measuring a cloud arm that primes a cache against a local
arm that cannot would put an engineering optimisation inside the deployment
variable.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from .provider import Provider
from .types import LLMConfig, LLMError, ToolCall


class AnthropicProvider(Provider):

    def __init__(self, config: LLMConfig) -> None:
        super().__init__(config)
        try:
            import anthropic
        except ImportError as exc:
            raise LLMError(
                "the `anthropic` package is not installed; the cloud cells "
                "cannot run. pip install 'anthropic>=0.40.0,<1.0.0'") from exc
        key = config.api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise LLMError("ANTHROPIC_API_KEY is not set; the cloud cells "
                           "cannot run")
        self._client = anthropic.Anthropic(api_key=key, timeout=config.timeout_s)

    def preflight(self) -> None:
        """One minimal call, to fail here rather than mid-run.

        It costs a fraction of a cent and it verifies three things at once:
        the key works, the pinned model exists, and the model that answers is
        the model that was pinned. That last check is the whole reason this
        method exists — a tier substitution discovered on task 1 of 48 is a
        bug report, and on task 48 it is a discarded cell.
        """
        try:
            resp = self._client.messages.create(
                model=self.config.model,
                max_tokens=1,
                temperature=self.config.temperature,
                messages=[{"role": "user", "content": "ok"}],
            )
        except Exception as exc:
            raise LLMError(
                f"preflight failed for {self.config.model!r}: "
                f"{type(exc).__name__}: {exc}") from exc
        self._check_model(getattr(resp, "model", "") or "")

    @staticmethod
    def _to_anthropic(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Neutral transcript (`core.llm.types`) -> Anthropic content blocks.

        Tool results are user-role `tool_result` blocks here, and consecutive
        results must share one message — a loop that called three tools in a
        turn sends one user message with three blocks, not three messages.
        """
        out: List[Dict[str, Any]] = []
        for m in messages:
            role = m.get("role")
            if role == "tool":
                block = {"type": "tool_result",
                         "tool_use_id": m.get("tool_call_id", ""),
                         "content": m.get("content", "")}
                if out and out[-1]["role"] == "user" and                         isinstance(out[-1]["content"], list) and                         out[-1]["content"][0].get("type") == "tool_result":
                    out[-1]["content"].append(block)
                else:
                    out.append({"role": "user", "content": [block]})
                continue
            if role == "assistant":
                content: List[Dict[str, Any]] = []
                if m.get("content"):
                    content.append({"type": "text", "text": m["content"]})
                for tc in m.get("tool_calls") or []:
                    content.append({"type": "tool_use", "id": tc.id,
                                    "name": tc.name, "input": tc.arguments})
                out.append({"role": "assistant",
                            "content": content or [{"type": "text", "text": ""}]})
                continue
            out.append({"role": "user", "content": m.get("content", "")})
        return out

    def _call(self, *, system: str, messages: List[Dict[str, Any]],
              tools: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        kwargs: Dict[str, Any] = {
            "model": self.config.model,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "messages": self._to_anthropic(messages),
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = tools

        resp = self._client.messages.create(**kwargs)

        text = "".join(
            getattr(b, "text", "") for b in resp.content
            if getattr(b, "type", "") == "text"
        )
        tool_calls = [
            ToolCall(id=b.id, name=b.name, arguments=dict(b.input or {}))
            for b in resp.content
            if getattr(b, "type", "") == "tool_use"
        ]
        usage = getattr(resp, "usage", None)
        return {
            "text": text,
            "tool_calls": tool_calls,
            "model": getattr(resp, "model", "") or "",
            "input_tokens": getattr(usage, "input_tokens", 0) or 0,
            "output_tokens": getattr(usage, "output_tokens", 0) or 0,
            "stop_reason": getattr(resp, "stop_reason", None),
        }
