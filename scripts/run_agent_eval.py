"""Run agent eval tasks with real Playwright and report results."""
from __future__ import annotations

import os
import sys
import time
import yaml
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("SEC_USER_AGENT", "WhaleforceCodingTest Paul bravo336629@gmail.com")
os.environ.setdefault("DATABASE_URL", "sqlite:///agent_eval.db")

from shared_harness import job_store
from task1_agent.agent.browser import PlaywrightExecutor
from task1_agent.agent.loop import run as agent_run

TASKS_FILE = Path(__file__).resolve().parent.parent / "task1_agent" / "eval" / "tasks.yaml"


def main():
    with open(TASKS_FILE, encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    tasks = [t for t in manifest["tasks"] if t.get("split", "train") == "train"]
    print(f"Running {len(tasks)} train tasks...\n")

    results = []
    executor = PlaywrightExecutor(headless=True, timeout_ms=20000)
    executor.start()

    try:
        for task in tasks:
            task_id = task["id"]
            desc = task["description"]
            start_url = task.get("start_url", "https://example.com")

            run_id = job_store.create_run("agent")
            t0 = time.perf_counter()
            result = agent_run(
                task_description=desc,
                start_url=start_url,
                run_id=run_id,
                execute_action=executor,
            )
            elapsed = time.perf_counter() - t0

            results.append({
                "task_id": task_id,
                "domain": task.get("domain", ""),
                "task_type": task.get("task_type", ""),
                "status": result.status,
                "steps": len(result.steps),
                "final_url": result.final_url,
                "elapsed_s": round(elapsed, 2),
                "error": result.error,
            })
            status_icon = "OK" if result.status == "success" else "FAIL"
            print(f"  [{status_icon}] {task_id:30s} {result.status:10s} {elapsed:.1f}s  steps={len(result.steps)}  url={result.final_url}")
    finally:
        executor.close()

    print(f"\n{'='*70}")
    successes = sum(1 for r in results if r["status"] == "success")
    print(f"Results: {successes}/{len(results)} success")
    print(f"Total time: {sum(r['elapsed_s'] for r in results):.1f}s")
    print(f"Avg time/task: {sum(r['elapsed_s'] for r in results)/len(results):.1f}s")

    recovery_count = sum(r["steps"] - 1 for r in results if r["steps"] > 1)
    print(f"Recovery steps: {recovery_count}")
    silent_failures = sum(1 for r in results if r["status"] == "success" and "wrong" in (r.get("error") or "").lower())
    print(f"Silent failures: {silent_failures}")

    for r in results:
        if r["status"] != "success":
            print(f"  FAIL: {r['task_id']} — {r['error']}")


if __name__ == "__main__":
    main()
