"""Load versioned prompts and SOP fragments."""

from __future__ import annotations

import re
from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def load_prompt(name: str, *, variant: str | None = None) -> str:
    """
    Load a prompt by name.

    name: recovery | boundary_arbiter | blind_critic | agent_plan
    variant: FailureType.value for recovery fragments in sops/recovery.md
    Prefer prompts/sops/{name}.md; fallback prompts/v1_{name}.txt
    """
    sops_path = _PROMPTS_DIR / "sops" / f"{name}.md"
    v1_path = _PROMPTS_DIR / f"v1_{name}.txt"

    if sops_path.exists():
        content = sops_path.read_text(encoding="utf-8")
        if variant:
            return _extract_variant_section(content, variant)
        return content

    if v1_path.exists():
        return v1_path.read_text(encoding="utf-8")

    raise FileNotFoundError(f"Prompt not found: {name!r} (variant={variant!r})")


def _extract_variant_section(content: str, variant: str) -> str:
    pattern = rf"^##\s+{re.escape(variant)}\s*$"
    match = re.search(pattern, content, flags=re.MULTILINE | re.IGNORECASE)
    if not match:
        raise ValueError(f"Variant section not found: {variant!r}")
    start = match.end()
    next_header = re.search(r"^##\s+", content[start:], flags=re.MULTILINE)
    end = start + next_header.start() if next_header else len(content)
    return content[start:end].strip()
