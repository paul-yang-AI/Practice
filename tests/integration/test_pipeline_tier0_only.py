from unittest.mock import patch

import pytest

from task2_sec.pipeline.run import extract_from_html


@pytest.mark.integration
def test_pipeline_tier0_only_zero_llm(mini_10k_html: str) -> None:
    with patch("shared_harness.llm_router.litellm.completion") as mock_completion:
        result = extract_from_html(mini_10k_html, accession="test-000", use_arbiter=False)
        mock_completion.assert_not_called()
    extracted = [i for i in result.items if i.status.value == "extracted"]
    assert len(extracted) >= 2
    item1 = next(i for i in result.items if i.item_id == "1")
    assert item1.text and "software globally" in item1.text
