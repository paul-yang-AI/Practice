import pytest

from task2_sec.pipeline.metrics import RATIO_MIN, evaluate_output_ratio, evaluate_segment_metrics


@pytest.mark.unit
def test_metrics_conservation_low_ratio_flags_low_confidence() -> None:
    input_segment = "x" * 500
    output_text = "y" * 100
    result = evaluate_output_ratio(input_segment, output_text, ratio_min=RATIO_MIN)
    assert result.low_confidence is True
    assert any("token_ratio_low" in w for w in result.warnings)


@pytest.mark.unit
def test_metrics_segment_passes_for_full_span(mini_10k_html: str) -> None:
    from task2_sec.pipeline.segment import Segmenter

    body, segments = Segmenter().segment(mini_10k_html)
    item1 = next(s for s in segments if s.item_id == "1")
    result = evaluate_segment_metrics(body, item1.start, item1.end, "1")
    assert result.passed is True
    assert result.low_confidence is False
