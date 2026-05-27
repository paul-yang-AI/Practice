"""Demonstrate global budget circuit breaker (no API calls)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from shared_harness.cost_tracker import BudgetExceededError, check_budget, record_cost


def main() -> None:
    os.environ["RUN_BUDGET_USD"] = "0.001"
    os.environ["DATABASE_URL"] = "sqlite:///demo_circuit_breaker.db"

    print("Circuit breaker demo: RUN_BUDGET_USD=0.001")
    record_cost(
        run_id="demo-run",
        tier=1,
        provider="demo",
        model="demo/model",
        call_site="demo",
        attempt="primary",
        usd=0.002,
    )
    try:
        check_budget(run_id="demo-run", task_type="agent")
        print("FAIL: expected BudgetExceededError")
        sys.exit(1)
    except BudgetExceededError as exc:
        print(f"OK: BudgetExceededError raised — {exc}")
        print("Subsequent LLM calls would be blocked (no fallback after budget hit).")


if __name__ == "__main__":
    main()
