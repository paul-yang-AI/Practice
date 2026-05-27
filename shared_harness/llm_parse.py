"""Cross-provider JSON normalization and Pydantic parsing."""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def parse_json_text(raw: str) -> str:
    """Strip markdown fences and whitespace from LLM JSON output."""
    t = raw.strip()
    if t.startswith("```"):
        t = t.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return t


def parse_model(raw: str, schema: type[T]) -> T:
    """Parse LLM output into a Pydantic model."""
    return schema.model_validate_json(parse_json_text(raw))
