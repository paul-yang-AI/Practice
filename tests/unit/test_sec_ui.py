import pytest

from shared_harness.sec_ui import (
    compute_required_kpi,
    heldout_outcome_badge,
    sec_result_matches_context,
)


@pytest.mark.unit
def test_sec_result_matches_context_same_manifest() -> None:
    assert sec_result_matches_context(
        source="manifest",
        accession="0000950170-24-087843",
        result_source="manifest",
        result_accession="0000950170-24-087843",
    )


@pytest.mark.unit
def test_sec_result_matches_context_rejects_wrong_tab() -> None:
    assert not sec_result_matches_context(
        source="manifest",
        accession="0000950170-24-087843",
        result_source="custom",
        result_accession="0000950170-24-087843",
    )


@pytest.mark.unit
def test_sec_result_matches_context_rejects_wrong_accession() -> None:
    assert not sec_result_matches_context(
        source="manifest",
        accession="0000050863-25-000009",
        result_source="manifest",
        result_accession="0000950170-24-087843",
    )


@pytest.mark.unit
def test_compute_required_kpi_msft() -> None:
    from types import SimpleNamespace

    from shared_harness.schemas.sec_schema import ItemStatus

    items = [
        SimpleNamespace(item_id=i, text="x" * 600, status=ItemStatus.EXTRACTED)
        for i in ("1", "1A", "7", "8")
    ]
    kpi = compute_required_kpi(items, ["1", "1A", "7", "8"])
    assert kpi["passed"] is True
    assert kpi["label"] == "4/4"


@pytest.mark.unit
def test_compute_required_kpi_intc_contract() -> None:
    from types import SimpleNamespace

    from shared_harness.schemas.sec_schema import ItemStatus

    items = [
        SimpleNamespace(item_id="1A", text="risk" * 200, status=ItemStatus.EXTRACTED),
        SimpleNamespace(item_id="7", text="mda" * 200, status=ItemStatus.EXTRACTED),
        SimpleNamespace(item_id="8", text="fs" * 200, status=ItemStatus.EXTRACTED),
        SimpleNamespace(item_id="1", text="Pages 1-5", status=ItemStatus.EXTRACTED),
    ]
    kpi = compute_required_kpi(items, ["1A", "7", "8"])
    assert kpi["passed"] is True
    assert kpi["found"] == 3


@pytest.mark.unit
def test_heldout_outcome_badge_ok() -> None:
    emoji, label = heldout_outcome_badge(
        failure_category="ok",
        required_found=4,
        required_total=4,
    )
    assert emoji == "✅"
    assert "4/4" in label


@pytest.mark.unit
def test_heldout_outcome_badge_jpm_gap() -> None:
    emoji, label = heldout_outcome_badge(
        failure_category="toc_stub_required_item",
        required_found=2,
        required_total=4,
    )
    assert emoji == "⚠️"
    assert "toc_stub" in label


@pytest.mark.unit
def test_summarize_item_statuses_splits_expected_missing() -> None:
    from types import SimpleNamespace

    from shared_harness.schemas.sec_schema import ItemStatus
    from shared_harness.sec_ui import (
        format_coverage_summary,
        is_expected_missing,
        missing_item_display,
        summarize_item_statuses,
    )

    items = [
        SimpleNamespace(item_id="1A", status=ItemStatus.EXTRACTED),
        SimpleNamespace(item_id="1", status=ItemStatus.MISSING),
        SimpleNamespace(item_id="6", status=ItemStatus.MISSING),
        SimpleNamespace(item_id="4", status=ItemStatus.MISSING),
        SimpleNamespace(item_id="10", status=ItemStatus.INCORPORATED_BY_REFERENCE),
    ]
    counts = summarize_item_statuses(items, expected_missing=["1", "6", "16"])
    assert counts["extracted"] == 1
    assert counts["incorporated"] == 1
    assert counts["missing_expected"] == 2
    assert counts["missing_unexpected"] == 1
    assert is_expected_missing("1", ["1", "6"])
    assert "預期無獨立章節 2" in format_coverage_summary(counts)
    assert "待關注缺失 1" in format_coverage_summary(counts)

    icon, suffix, _bg, _border = missing_item_display("1", expected=True, item_name="Business")
    assert icon == "○"
    assert "預期" in suffix
    icon2, suffix2, _, _ = missing_item_display("4", expected=False, item_name="Mine Safety")
    assert icon2 == "⚠️"
    assert "未找到" in suffix2


@pytest.mark.unit
def test_sec_result_matches_context_heldout_tab() -> None:
    assert sec_result_matches_context(
        source="heldout",
        accession="0000019617-25-000270",
        result_source="heldout",
        result_accession="0000019617-25-000270",
    )
    assert not sec_result_matches_context(
        source="heldout",
        accession="0000019617-25-000270",
        result_source="manifest",
        result_accession="0000019617-25-000270",
    )
