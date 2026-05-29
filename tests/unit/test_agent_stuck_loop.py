import pytest

from task1_agent.agent.loop import StepResult, _is_stuck_type_loop


@pytest.mark.unit
def test_stuck_type_loop_detects_repeated_types_same_url() -> None:
    steps = [
        StepResult(step_index=i, action=f"type:box{i}", url="https://www.google.com/")
        for i in range(3)
    ]
    assert _is_stuck_type_loop(steps) is True


@pytest.mark.unit
def test_stuck_type_loop_ignores_mixed_actions() -> None:
    steps = [
        StepResult(step_index=1, action="type:q", url="https://www.google.com/"),
        StepResult(step_index=2, action="click:Search", url="https://www.google.com/"),
        StepResult(step_index=3, action="type:q", url="https://www.google.com/"),
    ]
    assert _is_stuck_type_loop(steps) is False


@pytest.mark.unit
def test_stuck_type_loop_ignores_url_change() -> None:
    steps = [
        StepResult(step_index=1, action="type:q", url="https://www.google.com/"),
        StepResult(step_index=2, action="type:q", url="https://www.google.com/search?q=x"),
        StepResult(step_index=3, action="type:q", url="https://www.google.com/search?q=x"),
    ]
    assert _is_stuck_type_loop(steps) is False
