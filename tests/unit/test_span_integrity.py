import pytest

from task2_sec.pipeline.segment import assert_span_integrity


@pytest.mark.unit
def test_span_integrity_passes() -> None:
    body = "Item 1. Business\nContent here."
    text = "Item 1. Business\nContent here."
    assert_span_integrity(body, 0, len(text), text)


@pytest.mark.unit
def test_span_integrity_fails_on_tampered_offset() -> None:
    body = "Item 1. Business\nContent here."
    with pytest.raises(AssertionError):
        assert_span_integrity(body, 0, 5, "WRONG")
