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


@pytest.mark.unit
def test_prompt_loader_agent_plan() -> None:
    text = load_prompt("agent_plan")
    assert "browser automation planner" in text.lower()
    assert "done=true" in text


@pytest.mark.unit
def test_prompt_loader_agent_extract() -> None:
    text = load_prompt("agent_extract")
    assert "extract information" in text.lower()
    assert '"result"' in text


@pytest.mark.unit
def test_prompt_loader_sec_segment_fallback_template() -> None:
    text = load_prompt("sec_segment_fallback")
    rendered = text.format(
        missing_items="Item 7, Item 8",
        chunk_start=0,
        chunk_end=100,
        chunk_text="Item 7. MD&A",
    )
    assert "Item 7, Item 8" in rendered
    assert "offset_in_chunk" in rendered
