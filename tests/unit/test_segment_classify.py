"""Unit tests for segment structure classification."""

from __future__ import annotations

import pytest

from task2_sec.pipeline.segment_classify import SegmentClass, classify_segment_text


@pytest.mark.unit
def test_classify_incorporated() -> None:
    assert classify_segment_text("any", incorporated=True) == SegmentClass.INCORPORATED


@pytest.mark.unit
def test_classify_toc_index() -> None:
    text = "Item 7A.\nMarket Risk\n70–129, 174–178\n"
    assert classify_segment_text(text) == SegmentClass.TOC_INDEX


@pytest.mark.unit
def test_classify_cross_ref() -> None:
    text = "Item 1.\nBusiness\nPages 3-4, 13\n"
    assert classify_segment_text(text) == SegmentClass.CROSS_REF_ONLY


@pytest.mark.unit
def test_classify_real_content() -> None:
    text = "Risk Factors\n" + ("Competition may harm us. " * 40)
    assert classify_segment_text(text) == SegmentClass.REAL_CONTENT
