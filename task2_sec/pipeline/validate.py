"""Validate segmented items — metrics, incorporation, optional arbiter."""

from __future__ import annotations

from shared_harness.schemas.sec_schema import STANDARD_ITEMS, ItemRecord, ItemStatus
from task2_sec.pipeline.arbiter import arbitrate_boundary
from task2_sec.pipeline.incorporation import detect_incorporation
from task2_sec.pipeline.metrics import evaluate_segment_metrics
from task2_sec.pipeline.segment import SegmentResult, assert_span_integrity


def _part_for_item(item_id: str) -> str | None:
    if item_id in {"1", "1A", "1B", "1C", "2", "3", "4"}:
        return "I"
    if item_id in {"5", "6", "7", "7A", "8"}:
        return "II"
    if item_id in {"9", "9A", "9B"}:
        return "III"
    if item_id in {"10", "11", "12", "13", "14", "15", "16"}:
        return "IV"
    return None


def validate_segment(
    body: str,
    seg: SegmentResult,
    *,
    run_id: str | None = None,
    use_arbiter: bool = True,
) -> ItemRecord:
    text = body[seg.start : seg.end]
    metrics = evaluate_segment_metrics(body, seg.start, seg.end, seg.item_id)

    incorporated, note = detect_incorporation(text)
    if incorporated:
        warnings = list(metrics.warnings)
        if note:
            warnings.append(note)
        snippet = text.strip()[:400]
        if snippet:
            warnings.append(f"引用原文：{snippet}")
        return ItemRecord(
            item_id=seg.item_id,
            part=_part_for_item(seg.item_id),
            status=ItemStatus.INCORPORATED_BY_REFERENCE,
            text=None,
            confidence=0.95,
            segment_method=seg.method.value,
            warnings=warnings,
            start=seg.start,
            end=seg.end,
        )

    if metrics.low_confidence and use_arbiter and run_id is not None:
        decision = arbitrate_boundary(
            body=body,
            chunk_start=seg.start,
            chunk_end=seg.end,
            item_id=seg.item_id,
            run_id=run_id,
        )
        new_start, new_end = decision.start, decision.end
        new_text = body[new_start:new_end]
        assert_span_integrity(body, new_start, new_end, new_text)
        remetrics = evaluate_segment_metrics(body, new_start, new_end, seg.item_id)
        status = ItemStatus.EXTRACTED if remetrics.passed else ItemStatus.LOW_CONFIDENCE
        return ItemRecord(
            item_id=seg.item_id,
            part=_part_for_item(seg.item_id),
            status=status,
            text=new_text,
            confidence=decision.confidence,
            segment_method="arbiter",
            warnings=remetrics.warnings,
            start=new_start,
            end=new_end,
        )

    if metrics.low_confidence:
        return ItemRecord(
            item_id=seg.item_id,
            part=_part_for_item(seg.item_id),
            status=ItemStatus.LOW_CONFIDENCE,
            text=text,
            confidence=metrics.confidence,
            segment_method=seg.method.value,
            warnings=metrics.warnings,
            start=seg.start,
            end=seg.end,
        )

    assert_span_integrity(body, seg.start, seg.end, text)
    return ItemRecord(
        item_id=seg.item_id,
        part=_part_for_item(seg.item_id),
        status=ItemStatus.EXTRACTED,
        text=text,
        confidence=metrics.confidence,
        segment_method=seg.method.value,
        warnings=metrics.warnings,
        start=seg.start,
        end=seg.end,
    )


def fill_missing_items(items: list[ItemRecord]) -> list[ItemRecord]:
    by_id = {i.item_id: i for i in items}
    complete: list[ItemRecord] = []
    for item_id in STANDARD_ITEMS:
        if item_id in by_id:
            complete.append(by_id[item_id])
        else:
            complete.append(
                ItemRecord(
                    item_id=item_id,
                    part=_part_for_item(item_id),
                    status=ItemStatus.MISSING,
                    text=None,
                    confidence=0.0,
                    warnings=["missing_item_header"],
                )
            )
    return complete


def validate_segments(
    body: str,
    segments: list[SegmentResult],
    *,
    run_id: str | None = None,
    use_arbiter: bool = False,
) -> list[ItemRecord]:
    items = [
        validate_segment(body, seg, run_id=run_id, use_arbiter=use_arbiter) for seg in segments
    ]
    return fill_missing_items(items)
