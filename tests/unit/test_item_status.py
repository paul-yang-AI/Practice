import pytest

from shared_harness.schemas.sec_schema import ItemStatus
from task2_sec.pipeline.incorporation import detect_incorporation
from task2_sec.pipeline.metrics import evaluate_output_ratio
from task2_sec.pipeline.validate import validate_segment
from task2_sec.pipeline.segment import SegmentResult, SegmentMethod


@pytest.mark.unit
def test_incorporation_by_reference_no_fake_fulltext() -> None:
    text = (
        "Item 10. Directors, Executive Officers and Corporate Governance.\n"
        "The information required by this item is incorporated by reference to the "
        "definitive proxy statement for our 2025 annual meeting."
    )
    is_ref, note = detect_incorporation(text)
    assert is_ref is True
    assert note is not None

    seg = SegmentResult(item_id="10", start=0, end=len(text), method=SegmentMethod.REGEX)
    record = validate_segment(text, seg, use_arbiter=False)
    assert record.status == ItemStatus.INCORPORATED_BY_REFERENCE
    assert record.text is None


@pytest.mark.unit
def test_extracted_item_has_fulltext(mini_10k_html: str) -> None:
    from task2_sec.pipeline.segment import Segmenter

    body, segments = Segmenter().segment(mini_10k_html)
    item1 = next(s for s in segments if s.item_id == "1")
    record = validate_segment(body, item1, use_arbiter=False)
    assert record.status == ItemStatus.EXTRACTED
    assert record.text is not None
    assert "software globally" in record.text


@pytest.mark.unit
def test_missing_items_filled() -> None:
    from shared_harness.schemas.sec_schema import STANDARD_ITEMS, ItemRecord
    from task2_sec.pipeline.validate import fill_missing_items

    items = fill_missing_items(
        [ItemRecord(item_id="1", status=ItemStatus.EXTRACTED, text="x", confidence=0.9)]
    )
    assert len(items) == len(STANDARD_ITEMS)
    missing = [i for i in items if i.status == ItemStatus.MISSING]
    assert len(missing) == len(STANDARD_ITEMS) - 1
