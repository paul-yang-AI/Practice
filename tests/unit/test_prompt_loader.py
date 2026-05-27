import pytest

from shared_harness.prompt_loader import load_prompt


@pytest.mark.unit
def test_prompt_loader_recovery_timeout_variant() -> None:
    text = load_prompt("recovery", variant="TIMEOUT")
    assert "Extend wait" in text
    assert "ELEMENT_NOT_FOUND" not in text


@pytest.mark.unit
def test_prompt_loader_blind_critic_fallback_txt() -> None:
    text = load_prompt("blind_critic")
    assert "independent verifier" in text.lower()
    assert "passed" in text
