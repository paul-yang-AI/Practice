"""Content-quality heuristics for extracted Item text (TOC stub detection)."""

from __future__ import annotations

import re

from task2_sec.pipeline.segment import is_page_reference_text

# Required items shorter than this with page citations are likely TOC index rows.
TOC_STUB_MAX_CHARS = 500

_PAGES_KW_RE = re.compile(r"\bPages?\s+\d", re.IGNORECASE)
_K_EXHIBIT_REF_RE = re.compile(r"\bK-\d+\b", re.IGNORECASE)
_ITEM_HEADER_RE = re.compile(r"Item\s+\d+[A-Z]?\.?", re.IGNORECASE)


def is_k1_exhibit_reference_index(
    text: str | None, *, max_chars: int = TOC_STUB_MAX_CHARS
) -> bool:
    """BRK-style K-1 internal refs (e.g. K-24, K-33) — title + pointer, not full Item body."""
    if not text:
        return False
    clean = text.strip()
    if len(clean) >= max_chars:
        return False
    if _K_EXHIBIT_REF_RE.search(clean) is None:
        return False
    residual = _K_EXHIBIT_REF_RE.sub("", clean)
    residual = _ITEM_HEADER_RE.sub("", residual)
    residual = re.sub(r"\s+", " ", residual).strip()
    return len(residual) < 200


def is_cross_reference_index(text: str | None, *, max_chars: int = TOC_STUB_MAX_CHARS) -> bool:
    """Cross-ref index row: INTC 'Pages N' or BRK K-1 'K-xx' pointers — not bank TOC stubs."""
    if not text:
        return False
    clean = text.strip()
    if len(clean) >= max_chars:
        return False
    if is_k1_exhibit_reference_index(clean, max_chars=max_chars):
        return True
    return is_page_reference_text(clean) and _PAGES_KW_RE.search(clean) is not None


def is_likely_toc_stub(text: str | None, *, max_chars: int = TOC_STUB_MAX_CHARS) -> bool:
    """True when extracted text looks like a TOC index row, not real section body."""
    if not text:
        return False
    clean = text.strip()
    if len(clean) >= max_chars:
        return False
    if not is_page_reference_text(clean):
        return False
    if is_cross_reference_index(clean, max_chars=max_chars):
        return False
    return True


def assess_required_item(item_id: str, text: str | None, status_value: str) -> str:
    """Return quality label: ok | toc_stub | cross_ref | missing | incorporated | low_confidence."""
    if status_value == "missing":
        return "missing"
    if status_value == "not_applicable":
        return "ok"
    if status_value == "incorporated_by_reference":
        return "incorporated"
    if status_value == "low_confidence":
        return "low_confidence"
    if status_value == "extracted" and is_likely_toc_stub(text):
        return "toc_stub"
    if status_value == "extracted" and is_cross_reference_index(text):
        return "cross_ref"
    if status_value == "extracted":
        return "ok"
    return status_value
