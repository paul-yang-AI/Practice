"""Pure helpers for SEC 10-K Streamlit page (unit-testable without Streamlit)."""

from __future__ import annotations


def heldout_outcome_badge(
    *,
    failure_category: str,
    required_found: int,
    required_total: int,
) -> tuple[str, str]:
    """Return (emoji, short label) for held-out filing expected baseline outcome."""
    req = f"{required_found}/{required_total}"
    cat = failure_category or "unknown"
    if cat == "ok":
        return "✅", f"基線預期通過 ({req})"
    if cat == "toc_stub_required_item":
        return "⚠️", f"已知部分失敗 ({req}) — {cat}"
    if cat == "missing_item_header":
        return "❌", f"預期失敗 ({req}) — {cat}"
    return "⚠️", f"基線 {req} — {cat}"


def sec_result_matches_context(
    *,
    source: str,
    accession: str,
    result_source: str | None,
    result_accession: str | None,
) -> bool:
    """True when cached extraction belongs to the active tab + accession selection."""
    accession = (accession or "").strip()
    if not accession or not result_accession or not result_source:
        return False
    return result_source == source and result_accession.strip() == accession
