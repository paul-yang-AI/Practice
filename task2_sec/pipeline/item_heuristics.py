"""Generic Item-level heuristics (not-applicable, note cross-refs)."""

from __future__ import annotations

import re

_NA_BODY_RE = re.compile(
    r"^(?:Not\s+Applicable|\[?\s*Reserved\s*\]?)\.?\s*$",
    re.IGNORECASE,
)
_NOTE_XREF_RE = re.compile(
    r"See\s+Note\s+\d+\s+to\s+the\s+Consolidated\s+Financial\s+Statements",
    re.IGNORECASE,
)
# Strip a leading SEC section title before checking N/A body.
_SECTION_PREFIX_RE = re.compile(
    r"^(?:"
    r"Mine\s+Safety\s+Disclosures?"
    r"|Properties"
    r"|Cybersecurity"
    r"|Unresolved\s+Staff\s+Comments"
    r"|Market\s+for\s+Registrant.s\s+Common\s+Equity\b[^\n]*"
    r"|Form\s+10-K\s+Summary"
    r"|Item\s+\d+[A-Z]?[\.\:\-\u2014]?\s*[^\n]*"
    r")\s*\n+",
    re.IGNORECASE,
)


def detect_not_applicable(text: str) -> tuple[bool, str | None]:
    """True when an Item section is explicitly N/A or [Reserved] (short, no page index)."""
    clean = text.strip()
    if not clean or len(clean) > 280:
        return False, None
    if _NOTE_XREF_RE.search(clean):
        return False, None
    if re.search(r"\d+\s*[–\-]\s*\d+", clean):
        return False, None
    if _NA_BODY_RE.match(clean):
        return True, "not_applicable"
    stripped = _SECTION_PREFIX_RE.sub("", clean, count=1).strip()
    stripped = re.sub(r"\s*Part\s+[IV]+[\s\S]*", "", stripped, flags=re.I).strip()
    if stripped and _NA_BODY_RE.match(stripped):
        return True, "not_applicable"
    return False, None


def detect_note_cross_reference(text: str) -> tuple[bool, str | None]:
    """Item points to a financial statement note instead of standalone prose."""
    clean = text.strip()
    if not clean or len(clean) > 450:
        return False, None
    if _NOTE_XREF_RE.search(clean):
        return True, "cross_ref_financial_note"
    return False, None
