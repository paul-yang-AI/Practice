import pytest

from shared_harness.edgar_client import build_sec_document_url, build_sec_viewer_url
from shared_harness.schemas.sec_schema import ItemRecord, ItemStatus
from task2_sec.pipeline.html_snippet import attach_html_snippets
from task2_sec.pipeline.segment import Segmenter


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
