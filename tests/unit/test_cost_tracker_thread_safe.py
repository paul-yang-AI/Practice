import threading

import pytest

from shared_harness.cost_tracker import get_session_cost, record_cost
from shared_harness.job_store import create_run


@pytest.mark.unit
def test_cost_tracker_thread_safe() -> None:
    run_id = create_run("agent")
    n_threads = 8
    per_thread = 5
    usd_each = 0.001

    def worker(tid: int) -> None:
        for i in range(per_thread):
            record_cost(
                run_id=run_id,
                tier=1,
                provider="test",
                model=f"model/{tid}",
                call_site="test",
                attempt="primary",
                usd=usd_each,
            )

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    expected = n_threads * per_thread * usd_each
    assert abs(get_session_cost() - expected) < 1e-6
