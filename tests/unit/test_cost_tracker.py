import pytest

from shared_harness.cost_tracker import BudgetExceededError, check_budget, get_session_cost, record_cost
from shared_harness.job_store import create_run


@pytest.mark.unit
def test_cost_tracker_global_budget(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RUN_BUDGET_USD", "0.01")
    run_id = create_run("agent")
    record_cost(
        run_id=run_id,
        tier=1,
        provider="test",
        model="test/model",
        call_site="test",
        attempt="primary",
        usd=0.02,
    )
    assert get_session_cost() >= 0.02
    with pytest.raises(BudgetExceededError):
        check_budget(run_id, task_type="agent")


@pytest.mark.unit
def test_cost_tracker_per_run_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RUN_BUDGET_USD", "100")
    run_id = create_run("filing")
    record_cost(
        run_id=run_id,
        tier=2,
        provider="test",
        model="test/model",
        call_site="sec_boundary_arbiter",
        attempt="primary",
        usd=0.35,
    )
    with pytest.raises(BudgetExceededError):
        check_budget(run_id, task_type="filing")
