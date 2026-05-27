"""Run agent eval tasks with real Playwright + LLM and merge into reports CSV."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from shared_harness.env import load_env
from shared_harness.eval_runner import (
    run_agent_eval,
    run_sec_eval,
    summarize_eval,
    write_eval_csv,
)


def main() -> None:
    load_env()
    print("Running agent train eval (Playwright + LLM)...\n")
    agent_results = run_agent_eval(split="train")

    for r in agent_results:
        icon = "OK" if r.status == "success" else "FAIL"
        print(
            f"  [{icon}] {r.task_id:30s} {r.status:10s} {r.elapsed_s:.1f}s  "
            f"steps={r.steps} llm={r.llm_calls} usd=${r.usd_per_task:.4f}  "
            f"recovery={r.recovery_count} silent={r.silent_failure}"
        )
        if r.extracted_result:
            preview = r.extracted_result[:120].replace("\n", " ")
            print(f"       result: {preview}")
        if r.error:
            print(f"       error: {r.error}")

    sec_results = run_sec_eval(split="train", use_arbiter=False)
    combined = [*sec_results, *agent_results]
    reports = _ROOT / "reports"
    csv_path = write_eval_csv(combined, reports / "eval_train.csv")
    write_eval_csv(combined, reports / "latest.csv")

    summary = summarize_eval(combined)
    summary_path = reports / "eval_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(f"\n{'=' * 70}")
    successes = int(summary.get("agent_tasks", 0) * summary.get("agent_success_rate", 0))
    print(
        f"Agent: {summary.get('agent_success_rate', 0):.0%} success "
        f"({successes}/{summary.get('agent_tasks', 0)})"
    )
    print(f"Silent failures: {summary.get('agent_silent_failures', 0)}")
    print(f"P50 latency: {summary.get('agent_latency_p50', 0):.1f}s")
    print(f"P95 latency: {summary.get('agent_latency_p95', 0):.1f}s")
    print(f"P50 cost: ${summary.get('agent_usd_p50', 0):.4f}")
    print(f"SEC filings ok: {summary.get('sec_ok', 0)}/{summary.get('sec_filings', 0)}")
    print(f"Wrote {csv_path}")
    print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()
