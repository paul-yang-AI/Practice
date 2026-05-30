"""Unit tests for not-applicable and note cross-reference heuristics."""

from __future__ import annotations

import pytest

from shared_harness.schemas.sec_schema import ItemStatus
from task2_sec.pipeline.item_heuristics import detect_not_applicable, detect_note_cross_reference
from task2_sec.pipeline.segment import SegmentMethod, SegmentResult
from task2_sec.pipeline.validate import validate_segment


@pytest.mark.unit
def test_detect_not_applicable_mine_safety() -> None:
    text = "\n\nMine Safety Disclosures\nNot Applicable\n\nPart II\n"
    ok, note = detect_not_applicable(text)
    assert ok is True
    assert note == "not_applicable"


@pytest.mark.unit
def test_detect_not_applicable_rejects_page_index() -> None:
    text = "Item 7A.\nMarket Risk\n70–129, 174–178\n"
    assert detect_not_applicable(text) == (False, None)


@pytest.mark.unit
def test_detect_note_cross_reference() -> None:
    text = (
        "\n\nLegal Proceedings—See Note 30 to the Consolidated Financial Statements\n"
        "301–308\n"
    )
    ok, note = detect_note_cross_reference(text)
    assert ok is True
    assert note == "cross_ref_financial_note"


@pytest.mark.unit
def test_validate_segment_not_applicable() -> None:
    text = "\n\nProperties\nNot Applicable\n"
    seg = SegmentResult(item_id="2", start=0, end=len(text), method=SegmentMethod.SECTION_NAME)
    record = validate_segment(text, seg, use_arbiter=False)
    assert record.status == ItemStatus.NOT_APPLICABLE
    assert record.text is not None
