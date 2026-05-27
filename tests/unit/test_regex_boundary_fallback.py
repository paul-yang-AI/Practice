from pathlib import Path

import pytest

from task2_sec.pipeline.normalize import normalize
from task2_sec.pipeline.segment import SegmentMethod, Segmenter, assert_span_integrity

_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


@pytest.mark.unit
def test_regex_finds_item1a_and_item1b() -> None:
    html = (_FIXTURES / "dirty_regex_10k.html").read_text(encoding="utf-8")
    body = normalize(html)
    segmenter = Segmenter()
    _, segments = segmenter.segment(html)
    ids = {s.item_id for s in segments}
    assert "1" in ids
    assert "1A" in ids
    assert "1B" in ids
    assert "1C" in ids


@pytest.mark.unit
def test_regex_item1a_header_variants() -> None:
    html = (_FIXTURES / "dirty_regex_10k.html").read_text(encoding="utf-8")
    body = normalize(html)
    assert "ITEM 1A." in body
    assert "Item 1B." in body  # nbsp normalized
    assert "ITEM 1C." in body  # bold tags stripped


@pytest.mark.unit
def test_regex_negative_see_item1_not_header() -> None:
    html = (_FIXTURES / "dirty_regex_10k.html").read_text(encoding="utf-8")
    body = normalize(html)
    segmenter = Segmenter()
    _, segments = segmenter.segment(html)
    item1 = next(s for s in segments if s.item_id == "1")
    text = body[item1.start : item1.end]
    assert "see Item 1 above" in text
    assert text.count("Item 1.") == 1  # only the real header, not inline reference split


@pytest.mark.unit
def test_regex_no_gap_or_overlap_between_1a_and_1b() -> None:
    html = (_FIXTURES / "dirty_regex_10k.html").read_text(encoding="utf-8")
    body = normalize(html)
    segmenter = Segmenter()
    _, segments = segmenter.segment(html)
    item1a = next(s for s in segments if s.item_id == "1A")
    item1b = next(s for s in segments if s.item_id == "1B")
    assert item1a.end == item1b.start
    assert_span_integrity(body, item1a.start, item1a.end, body[item1a.start : item1a.end])
    assert "Primary risk factors" in body[item1a.start : item1a.end]


@pytest.mark.unit
def test_regex_segment_method_used_for_dirty_headers() -> None:
    html = (_FIXTURES / "dirty_regex_10k.html").read_text(encoding="utf-8")
    segmenter = Segmenter()
    _, segments = segmenter.segment(html)
    item1a = next(s for s in segments if s.item_id == "1A")
    assert item1a.method == SegmentMethod.REGEX


@pytest.mark.unit
def test_regex_item10_not_matched_as_item1() -> None:
    html = """
    <html><body>
    <h2>Item 1. Business</h2><p>Business overview.</p>
    <h2>Item 10. Directors</h2><p>Director bios here.</p>
    </body></html>
    """
    segmenter = Segmenter()
    body, segments = segmenter.segment(html)
    ids = {s.item_id for s in segments}
    assert "10" in ids
    assert "1" in ids
    item10 = next(s for s in segments if s.item_id == "10")
    item1 = next(s for s in segments if s.item_id == "1")
    assert item1.end == item10.start
    assert "Director bios" in body[item10.start : item10.end]
    assert "Business overview" in body[item1.start : item1.end]
