import pytest

from shared_harness.edgar_client import build_sec_document_url, build_sec_viewer_url
from shared_harness.schemas.sec_schema import ItemRecord, ItemStatus
from task2_sec.pipeline.html_snippet import (
    _find_best_in_html,
    _marker_from_body,
    _pick_best_html_pos,
    attach_html_snippets,
)
from task2_sec.pipeline.segment import SegmentResult, Segmenter


_SAMPLE_HTML = """
<html><body>
<a href="#item1">Item 1</a>
<a href="#item1a">Item 1A</a>
<div id="item1"><p>Item 1. Business</p></div>
<p>We sell software globally.</p>
<table>
  <tr><th>Year</th><th>Revenue</th></tr>
  <tr><td>2024</td><td>$100</td></tr>
</table>
<div id="item1a"><p>Item 1A. Risk Factors</p></div>
<p>Competition may intensify.</p>
</body></html>
"""


@pytest.mark.unit
def test_build_sec_viewer_url_with_anchor() -> None:
    url = build_sec_viewer_url("0000950170-24-087843", cik="789019", anchor="item7")
    assert "cik=789019" in url
    assert "0000950170-24-087843" in url
    assert url.endswith("#item7")


@pytest.mark.unit
def test_build_sec_document_url_with_anchor() -> None:
    doc = "https://www.sec.gov/Archives/edgar/data/1/2/filing.htm"
    assert build_sec_document_url(doc, "item8") == f"{doc}#item8"


@pytest.mark.unit
def test_attach_html_snippets_preserves_table() -> None:
    body, segments = Segmenter().segment(_SAMPLE_HTML, use_llm_fallback=False)
    item1_seg = next(s for s in segments if s.item_id == "1")

    items = [
        ItemRecord(
            item_id="1",
            status=ItemStatus.EXTRACTED,
            text=body[item1_seg.start : item1_seg.end],
        )
    ]
    attach_html_snippets(_SAMPLE_HTML, body, segments, items)

    assert items[0].html_snippet is not None
    assert "<table" in items[0].html_snippet.lower()
    assert items[0].source_anchor == "item1"
    assert "2024" in items[0].html_snippet


@pytest.mark.unit
def test_attach_html_snippets_on_real_segmentation() -> None:
    body, segments = Segmenter().segment(_SAMPLE_HTML, use_llm_fallback=False)
    assert segments
    items = [
        ItemRecord(
            item_id=seg.item_id,
            status=ItemStatus.EXTRACTED,
            text=body[seg.start : seg.end],
            start=seg.start,
            end=seg.end,
        )
        for seg in segments
    ]
    attach_html_snippets(_SAMPLE_HTML, body, segments, items)
    item1 = next(i for i in items if i.item_id == "1")
    assert item1.html_snippet
    assert "Business" in item1.html_snippet or "software" in item1.html_snippet


@pytest.mark.unit
def test_pick_best_html_pos_skips_toc_occurrence() -> None:
    # First occurrence sits in the TOC zone (top of doc); content occurrence later.
    html_len = 100_000
    toc_pos = 500
    content_pos = 40_000
    assert _pick_best_html_pos([toc_pos, content_pos], html_len) == content_pos


@pytest.mark.unit
def test_pick_best_html_pos_single_occurrence() -> None:
    assert _pick_best_html_pos([1234], 100_000) == 1234


@pytest.mark.unit
def test_find_best_in_html_prefers_content_over_toc() -> None:
    # A large filing whose header text appears first in the TOC, then in the body.
    filler = "x" * 50_000
    html = (
        "<table>Table of Contents Item 1A. Risk Factors page 12</table>"
        + filler
        + "<div>Item 1A. Risk Factors</div><p>Real risk content here.</p>"
    )
    toc_pos = html.lower().find("item 1a. risk factors")
    pos = _find_best_in_html(html, "Item 1A. Risk Factors", fallback="Item 1A")
    assert pos > toc_pos  # skipped the TOC hit, landed in the body


@pytest.mark.unit
def test_marker_from_body_uses_first_line() -> None:
    body = "Item 7. Management Discussion\nRevenue grew this year."
    seg = SegmentResult(item_id="7", start=0, end=len(body), method="regex")
    marker = _marker_from_body(body, seg)
    assert marker.item_id == "7"
    assert marker.anchor_id is None
    assert marker.body_offset == 0
    assert marker.header_text.startswith("Item 7")


# Citi-like: no resolvable TOC anchors AND headers wrapped so the DOM leaf-scan
# in _collect_header_markers finds no markers. Previously the whole filing got
# zero snippets; now per-segment body fallback still attaches them.
_NO_MARKER_HTML = """
<html><body>
<p>Item 1A. Risk Factors <span>(see detail)</span></p>
<p>Our operations face significant competitive and regulatory risks worldwide.</p>
<p>Item 7. Management Discussion <span>(see detail)</span></p>
<p>Net revenue grew across all major business segments during the fiscal year.</p>
</body></html>
"""


@pytest.mark.unit
def test_attach_html_snippets_body_fallback_when_no_markers() -> None:
    body, segments = Segmenter().segment(_NO_MARKER_HTML, use_llm_fallback=False)
    assert segments
    items = [
        ItemRecord(
            item_id=seg.item_id,
            status=ItemStatus.EXTRACTED,
            text=body[seg.start : seg.end],
            start=seg.start,
            end=seg.end,
        )
        for seg in segments
    ]
    attach_html_snippets(_NO_MARKER_HTML, body, segments, items)
    item1a = next((i for i in items if i.item_id == "1A"), None)
    assert item1a is not None
    assert item1a.html_snippet, "body fallback should still attach a snippet"
    assert "competitive" in item1a.html_snippet
