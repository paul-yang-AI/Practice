"""Tier → litellm model configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class TierConfig:
    primary: str
    fallback: str
    reasoning_effort: str | None = None


def _env(key: str, default: str) -> str:
    return os.environ.get(key, default)


# Stretch defaults per PLAN; override via env. MVI fallback example:
# LLM_TIER1_FALLBACK=openrouter/deepseek/deepseek-v4-flash
# LLM_TIER2_FALLBACK=openrouter/openai/gpt-4o-mini
TIER1 = TierConfig(
    primary=_env("LLM_TIER1_PRIMARY", "gemini/gemini-3-flash-preview"),
    fallback=_env("LLM_TIER1_FALLBACK", "openrouter/deepseek/deepseek-v4-pro"),
    reasoning_effort=None,
)

TIER2 = TierConfig(
    primary=_env("LLM_TIER2_PRIMARY", "gemini/gemini-3.1-pro-preview"),
    fallback=_env("LLM_TIER2_FALLBACK", "openrouter/qwen/qwen3.5-397b-a17b"),
    reasoning_effort=None,
)

TIER_MAP = {1: TIER1, 2: TIER2}


def resolve_tier(tier: int) -> TierConfig:
    if tier not in TIER_MAP:
        raise ValueError(f"Unknown tier: {tier}")
    return TIER_MAP[tier]


def fallback_enabled() -> bool:
    return os.environ.get("LLM_FALLBACK_ENABLED", "true").lower() in ("1", "true", "yes")
