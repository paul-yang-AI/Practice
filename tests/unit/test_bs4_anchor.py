import pytest

from task2_sec.pipeline.segment import SegmentMethod, Segmenter, assert_span_integrity


@pytest.mark.unit
def test_bs4_anchor_item1_offset(mini_10k_html: str) -> None:
    segmenter = Segmenter()
    body, segments = segmenter.segment(mini_10k_html)
    item1 = next(s for s in segments if s.item_id == "1")
    assert item1.method in (SegmentMethod.TOC, SegmentMethod.REGEX)
    header = body[item1.start : item1.start + 20]
    assert "Item 1" in header
    text = body[item1.start : item1.end]
    assert_span_integrity(body, item1.start, item1.end, text)
    assert "software globally" in text


@pytest.mark.unit
def test_bs4_anchor_item1a_follows_item1(mini_10k_html: str) -> None:
    segmenter = Segmenter()
    body, segments = segmenter.segment(mini_10k_html)
    item1 = next(s for s in segments if s.item_id == "1")
    item1a = next(s for s in segments if s.item_id == "1A")
    assert item1.start < item1a.start
    assert item1.end == item1a.start
