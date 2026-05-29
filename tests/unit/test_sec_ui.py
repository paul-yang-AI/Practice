import pytest

from shared_harness.sec_ui import heldout_outcome_badge, sec_result_matches_context


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
