"""Action-step recovery: one deterministic strategy before LLM replan."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from shared_harness.job_store import create_run
from task1_agent.agent.loop import StepResult, run
from task1_agent.agent.recovery import FailureType
from task1_agent.agent.verify import VerifyResult


@pytest.mark.integration
def test_action_step_recovery_before_replan() -> None:
    run_id = create_run("agent")
    calls = {"n": 0}

    def executor(action: str, context: dict) -> StepResult:
        step_idx = context.get("step", 0)
        if action.startswith("recovery:"):
            return StepResult(
                step_index=step_idx,
                action=action,
                url="https://example.com/fixed",
                page_text="Fixed page content after recovery strategy",
                verify=VerifyResult(passed=True),
                recovery_strategy=action.split(":", 1)[-1],
            )
        calls["n"] += 1
        if step_idx == 0:
            return StepResult(
                step_index=step_idx,
                action=action,
                url="https://example.com",
                page_text="Landing page content here",
                verify=VerifyResult(passed=True),
            )
        if calls["n"] == 2:
            return StepResult(
                step_index=step_idx,
                action="click:missing",
                url="https://example.com",
                page_text="Still landing",
                verify=VerifyResult(passed=False, reason="Element not found"),
                failure_type=FailureType.ELEMENT_NOT_FOUND,
                error="Element not found",
            )
        return StepResult(
            step_index=step_idx,
            action="task_complete",
            url="https://example.com/fixed",
            page_text="Fixed page content after recovery strategy",
            verify=VerifyResult(passed=True),
            extracted_result="Fixed page content after recovery strategy",
        )

    plans = [
        {"done": False, "action": "click", "selector": "missing", "value": "", "reasoning": "try"},
        {
            "done": True,
            "action": "none",
            "selector": "",
            "value": "",
            "result": "Fixed page content after recovery strategy",
            "reasoning": "ok",
        },
    ]

    def mock_plan(*_args, **_kwargs):
        return plans.pop(0)

    with patch("task1_agent.agent.loop._plan_next_action", side_effect=mock_plan):
        result = run(
            task_description="Click through to target",
            start_url="https://example.com",
            run_id=run_id,
            execute_action=executor,
        )

    assert result.status == "success"
    assert any(s.action.startswith("recovery:") for s in result.steps)
