"""L2: Blind Critic gate — L0 pass + critic NO → run must NOT succeed."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from shared_harness.job_store import create_run
from shared_harness.schemas.common import CriticVerdict
from task1_agent.agent.loop import StepResult, run
from task1_agent.agent.verify import VerifyResult


def _success_executor(action: str, context: dict) -> StepResult:
    """Executor where L0 verify always passes."""
    return StepResult(
        step_index=context.get("step", 0),
        action=action,
        url="https://example.com",
        page_text="Example Domain",
        a11y_tree="<root><heading>Example Domain</heading></root>",
        verify=VerifyResult(passed=True),
    )


def _mock_plan_done(*args, **kwargs):
    """Mock LLM plan that immediately marks task done."""
    return {"done": True, "action": "none", "selector": "", "value": "", "reasoning": "Page loaded", "result": "Example Domain"}


@pytest.mark.integration
def test_blind_critic_rejects_means_run_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """When Blind Critic says NO, run status must be 'failed' even if L0 all passed."""
    monkeypatch.setenv("ENABLE_BLIND_CRITIC", "true")
    run_id = create_run("agent")

    mock_verdict = CriticVerdict(passed=False)

    with patch("task1_agent.agent.loop.verify_via_blind_critic", return_value=mock_verdict), \
         patch("task1_agent.agent.loop._plan_next_action", side_effect=_mock_plan_done):
        result = run(
            task_description="Navigate to example.com and verify the title.",
            start_url="https://example.com",
            run_id=run_id,
            execute_action=_success_executor,
        )

    assert result.status == "failed"
    assert "Blind Critic" in (result.error or "")


@pytest.mark.integration
def test_blind_critic_accepts_means_run_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    """When Blind Critic says YES, run status should be 'success'."""
    monkeypatch.setenv("ENABLE_BLIND_CRITIC", "true")
    run_id = create_run("agent")

    mock_verdict = CriticVerdict(passed=True)

    with patch("task1_agent.agent.loop.verify_via_blind_critic", return_value=mock_verdict), \
         patch("task1_agent.agent.loop._plan_next_action", side_effect=_mock_plan_done):
        result = run(
            task_description="Navigate to example.com and verify the title.",
            start_url="https://example.com",
            run_id=run_id,
            execute_action=_success_executor,
        )

    assert result.status == "success"


@pytest.mark.integration
def test_blind_critic_disabled_skips_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    """When ENABLE_BLIND_CRITIC is false, critic is not called and run succeeds on L0."""
    monkeypatch.setenv("ENABLE_BLIND_CRITIC", "false")
    run_id = create_run("agent")

    with patch("task1_agent.agent.loop.verify_via_blind_critic") as mock_critic, \
         patch("task1_agent.agent.loop._plan_next_action", side_effect=_mock_plan_done):
        result = run(
            task_description="Navigate to example.com.",
            start_url="https://example.com",
            run_id=run_id,
            execute_action=_success_executor,
        )
        mock_critic.assert_not_called()

    assert result.status == "success"
