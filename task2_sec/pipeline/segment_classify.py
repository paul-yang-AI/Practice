"""Heuristic (+ optional LLM) classification of extracted Item segments."""

from __future__ import annotations

import enum
import os

from task2_sec.pipeline.content_quality import is_cross_reference_index, is_likely_toc_stub
from task2_sec.pipeline.segment import is_page_reference_text


class SegmentClass(str, enum.Enum):
    REAL_CONTENT = "real_content"
    TOC_INDEX = "toc_index"
    CROSS_REF_ONLY = "cross_ref_only"
    INCORPORATED = "incorporated"
    UNKNOWN = "unknown"


def classify_segment_text(
    text: str | None,
    *,
    incorporated: bool = False,
) -> SegmentClass:
    """Tier0 structure classifier — no LLM, no ticker-specific rules."""
    if incorporated:
        return SegmentClass.INCORPORATED
    if not text or not text.strip():
        return SegmentClass.UNKNOWN
    clean = text.strip()
    if is_likely_toc_stub(clean):
        return SegmentClass.TOC_INDEX
    if is_cross_reference_index(clean):
        return SegmentClass.CROSS_REF_ONLY
    if is_page_reference_text(clean):
        return SegmentClass.CROSS_REF_ONLY
    if len(clean) >= 300:
        return SegmentClass.REAL_CONTENT
    return SegmentClass.UNKNOWN


def classify_segment_text_with_llm(
    text: str,
    item_id: str,
    *,
    run_id: str | None = None,
) -> SegmentClass:
    """Optional Tier1 override when heuristic is UNKNOWN and env flag is set."""
    base = classify_segment_text(text)
    if base != SegmentClass.UNKNOWN:
        return base
    if os.getenv("ENABLE_SEC_LLM_CLASSIFY", "false").lower() not in {"1", "true", "yes"}:
        return base
    if run_id is None:
        return base

    try:
        from shared_harness.llm_router import complete
        from shared_harness.schemas.common import SegmentClassDecision
    except ImportError:
        return base

    preview = text.strip()[:1200]
    prompt = (
        f"Classify this SEC 10-K Item {item_id} excerpt. "
        "Return JSON only: "
        '{"class": "real_content"|"toc_index"|"cross_ref_only"|"incorporated"}'
        f"\n\nExcerpt:\n{preview}"
    )
    try:
        raw = complete(
            tier=1,
            call_site="sec_segment_classify",
            messages=[{"role": "user", "content": prompt}],
            run_id=run_id,
            task_type="filing",
            response_model=SegmentClassDecision,
            max_tokens=128,
        )
        if isinstance(raw, SegmentClassDecision):
            return SegmentClass(raw.klass)
    except Exception:
        pass
    return base
