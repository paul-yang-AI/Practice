"""Unit tests for content-quality heuristics."""

from __future__ import annotations

import pytest

from task2_sec.pipeline.content_quality import (
    assess_required_item,
    is_cross_reference_index,
    is_k1_exhibit_reference_index,
    is_likely_toc_stub,
)


@pytest.mark.unit
def test_cross_reference_index_with_pages_keyword() -> None:
    text = "Item 1.\nBusiness\nPages 3-4, 13\n"
    assert is_cross_reference_index(text) is True
    assert is_likely_toc_stub(text) is False
    assert assess_required_item("1", text, "extracted") == "cross_ref"


@pytest.mark.unit
def test_bare_page_range_is_toc_stub_not_cross_ref() -> None:
    text = "Item 7A.\nQuantitative and Qualitative Disclosures About Market Risk\n70–129, 174–178\n"
    assert is_cross_reference_index(text) is False
    assert is_likely_toc_stub(text) is True


@pytest.mark.unit
def test_toc_stub_detects_short_page_reference() -> None:
    text = "Item 7A.\nQuantitative and Qualitative Disclosures About Market Risk\n70–129, 174–178\n"
    assert is_likely_toc_stub(text) is True


@pytest.mark.unit
def test_long_body_not_toc_stub() -> None:
    text = "MARKET RISK\nOverview\n" + ("We face interest rate risk. " * 50)
    assert is_likely_toc_stub(text) is False


@pytest.mark.unit
def test_assess_required_item_flags_toc_stub() -> None:
    text = "Item 7A.\nMarket Risk\n70–129, 174–178\n"
    assert assess_required_item("7A", text, "extracted") == "toc_stub"


@pytest.mark.unit
def test_assess_required_item_ok_for_real_content() -> None:
    text = "Business\n" + ("Microsoft provides cloud services. " * 30)
    assert assess_required_item("1", text, "extracted") == "ok"


@pytest.mark.unit
def test_assess_incorporated() -> None:
    assert assess_required_item("10", None, "incorporated_by_reference") == "incorporated"


@pytest.mark.unit
def test_assess_not_applicable() -> None:
    assert assess_required_item("4", "Mine Safety Disclosures\nNot Applicable", "not_applicable") == "ok"


@pytest.mark.unit
def test_brk_k1_exhibit_reference_is_cross_ref() -> None:
    text = "Risk Factors\n\nK-24\nItem 1B.\n"
    assert is_k1_exhibit_reference_index(text) is True
    assert is_cross_reference_index(text) is True
    assert is_likely_toc_stub(text) is False
    assert assess_required_item("1A", text, "extracted") == "cross_ref"


@pytest.mark.unit
def test_brk_mda_k33_exhibit_reference() -> None:
    text = (
        "Management's Discussion and Analysis of Financial Condition "
        "and Results of Operations\n\nK-33\nItem 7A.\n"
    )
    assert is_k1_exhibit_reference_index(text) is True
    assert assess_required_item("7", text, "extracted") == "cross_ref"


@pytest.mark.unit
def test_long_body_with_k_ref_not_cross_ref() -> None:
    text = "Business\n" + ("We operate insurance and railroads. " * 40) + "\nSee K-24.\n"
    assert is_k1_exhibit_reference_index(text) is False
    assert assess_required_item("1", text, "extracted") == "ok"
