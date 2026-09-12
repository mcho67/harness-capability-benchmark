"""
core.llm — the model seam.

The deployment variable is this package and nothing else. `build_provider`
returns one of two objects with an identical surface; every other line of the
apparatus is written without knowing which it got.

    cfg = LLMConfig(provider="ollama", model="llama3.1:8b")
    llm = build_provider(cfg)
    llm.preflight()                      # fail here, not on task 37
    out = llm.complete(system=..., messages=[...], tools=[...])
    out.model_reported                   # what actually answered
"""

from __future__ import annotations

from .provider import PRICING, Provider, models_match, price
from .types import Completion, LLMConfig, LLMError, ToolCall


def build_provider(config: LLMConfig) -> Provider:
    """The one place a provider is chosen. Imports are local so a cell never
    needs the other provider's dependency installed."""
    if config.provider == "anthropic":
        from .anthropic_provider import AnthropicProvider
        return AnthropicProvider(config)
    if config.provider == "ollama":
        from .ollama_provider import OllamaProvider
        return OllamaProvider(config)
    raise LLMError(f"unknown provider: {config.provider!r}")


__all__ = ["LLMConfig", "LLMError", "Completion", "ToolCall",
           "Provider", "build_provider", "price", "models_match", "PRICING"]
