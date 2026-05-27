"""Detect Items incorporated by reference (e.g. Citi Items 10–14)."""

from __future__ import annotations

import re

INCORPORATION_RE = re.compile(
    r"incorporated\s+by\s+reference(?:\s+to|\s+from|\s+in|\s+herein)?",
    re.IGNORECASE,
)

PROXY_REFERENCE_RE = re.compile(
    r"incorporated\s+by\s+reference\s+to\s+(?:the\s+)?(?:definitive\s+)?proxy\s+statement",
    re.IGNORECASE,
)


def detect_incorporation(text: str) -> tuple[bool, str | None]:
    """
    Return (is_incorporated, note).
    Does not generate replacement body text.
    """
    if not text or not INCORPORATION_RE.search(text):
        return False, None
    if PROXY_REFERENCE_RE.search(text):
        return True, "此項目引用自 Proxy Statement，未包含於本文正文"
    return True, "此項目標記為 incorporated by reference，未包含於本文正文"
