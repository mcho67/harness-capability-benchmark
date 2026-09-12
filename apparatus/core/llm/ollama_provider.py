"""
The local half of the seam.

Uses Ollama's /api/chat over plain HTTP — the same endpoint the snapshot
uses, and no Python SDK, which is why the local cells ran during the trace
while the cloud cells could not.

Tool calling is native /api/chat `tools`, not prompt-engineered JSON. The
deciding arm needs tool calls in both deployments, and emulating them in the
prompt for the local arm only would make the arms differ by deployment — the
confound `core/` exists to prevent.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from .provider import Provider
from .types import LLMConfig, LLMError, ToolCall


class OllamaProvider(Provider):

    def __init__(self, config: LLMConfig) -> None:
        super().__init__(config)
        try:
            import requests
        except ImportError as exc:
            raise LLMError("the `requests` package is required for the local "
                           "cells") from exc
        self._requests = requests
        self._chat_url = f"{config.base_url.rstrip('/')}/api/chat"
        self._tags_url = f"{config.base_url.rstrip('/')}/api/tags"

    def preflight(self) -> None:
        """Free and definitive: ask Ollama what it has, and require the
        pinned model to be among it.

        The trace ran a whole grounding category with semantic retrieval
        silently inert because its embedding model was absent, and reported
        zero degradation events across 108 rows. A missing model is not
        allowed to be a quiet result here.
        """
        try:
            resp = self._requests.get(self._tags_url, timeout=10)
            resp.raise_for_status()
            installed = [m.get("name", "") for m in resp.json().get("models", [])]
        except Exception as exc:
            raise LLMError(
                f"cannot reach Ollama at {self._tags_url}: "
                f"{type(exc).__name__}: {exc}") from exc

        want = self.config.model
        if want not in installed:
            raise LLMError(
                f"the pinned local model {want!r} is not installed. "
                f"Available: {installed or '(none)'}. "
                f"Run: ollama pull {want}")

    @staticmethod
    def _to_ollama_messages(messages: List[Dict[str, Any]]
                            ) -> List[Dict[str, Any]]:
        """Neutral transcript (`core.llm.types`) -> Ollama's chat messages.

        Closer to the neutral shape than Anthropic's, but `ToolCall` still has
        to become the OpenAI-style `{"function": {...}}` envelope, and an
        assistant message with no text must not send `content: null`.
        """
        out: List[Dict[str, Any]] = []
        for m in messages:
            role = m.get("role")
            if role == "tool":
                out.append({"role": "tool", "content": m.get("content", ""),
                            "name": m.get("name", "")})
            elif role == "assistant":
                msg: Dict[str, Any] = {"role": "assistant",
                                       "content": m.get("content", "") or ""}
                calls = m.get("tool_calls") or []
                if calls:
                    msg["tool_calls"] = [
                        {"function": {"name": tc.name,
                                      "arguments": tc.arguments}}
                        for tc in calls]
                out.append(msg)
            else:
                out.append({"role": "user", "content": m.get("content", "")})
        return out

    def _call(self, *, system: str, messages: List[Dict[str, Any]],
              tools: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": self.config.model,
            "messages": ([{"role": "system", "content": system}] if system else [])
                        + self._to_ollama_messages(messages),
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                # Pinned so the local arm's context window is a stated
                # constant rather than whatever the model file defaults to.
                "num_predict": self.config.max_tokens,
            },
        }
        if tools:
            payload["tools"] = self._to_ollama_tools(tools)

        resp = self._requests.post(
            self._chat_url, json=payload, timeout=self.config.timeout_s)
        resp.raise_for_status()
        body = resp.json()

        message = body.get("message") or {}
        tool_calls = []
        for i, tc in enumerate(message.get("tool_calls") or []):
            fn = tc.get("function") or {}
            args = fn.get("arguments")
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except ValueError:
                    args = {"_raw": args}
            tool_calls.append(ToolCall(
                id=tc.get("id") or f"call_{i}",
                name=fn.get("name", ""),
                arguments=dict(args or {}),
            ))

        return {
            "text": message.get("content") or "",
            "tool_calls": tool_calls,
            "model": body.get("model") or "",
            "input_tokens": int(body.get("prompt_eval_count") or 0),
            "output_tokens": int(body.get("eval_count") or 0),
            "stop_reason": body.get("done_reason"),
        }

    @staticmethod
    def _to_ollama_tools(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Anthropic tool schemas -> Ollama's OpenAI-shaped ones.

        The arms author one tool schema and this translates it, so a tool is
        described identically to both models. Two hand-written schema sets
        would let wording differences ride along with the deployment
        variable.
        """
        out = []
        for t in tools:
            out.append({
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema")
                                  or t.get("parameters")
                                  or {"type": "object", "properties": {}},
                },
            })
        return out
