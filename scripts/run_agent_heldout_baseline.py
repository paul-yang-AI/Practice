"""Run held-out browser agent tasks (Playwright + LLM) and write baseline JSON."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from shared_harness.env import load_env
from shared_harness.eval_runner import AgentEvalResult, run_agent_eval, write_eval_csv


def _result_row(r: AgentEvalResult) -> dict:
    preview = (r.extracted_result or "")[:160].replace("\n", " ")
    return {
        "task_id": r.task_id,
        "domain": r.domain,
        "task_type": r.task_type,
        "split": r.split,
        "status": r.status,
        "failure_category": r.failure_category,
        "steps": r.steps,
        "elapsed_s": round(r.elapsed_s, 2),
        "recovery_count": r.recovery_count,
        "llm_calls": r.llm_calls,
        "silent_failure": r.silent_failure,
        "usd_per_task": round(r.usd_per_task, 4),
        "extracted_result_preview": preview,
        "error": r.error,
    }


def main() -> None:
    load_env()
    print("Running agent held-out eval (Playwright + LLM)...\n")
    results = run_agent_eval(split="heldout")
    rows = [_result_row(r) for r in results]

    for r in results:
        icon = "OK" if r.status == "success" and r.silent_failure == 0 else "FAIL"
        print(
            f"  [{icon}] {r.task_id:28s} {r.failure_category:22s} "
            f"steps={r.steps} recovery={r.recovery_count} silent={r.silent_failure}"
        )
        if r.error:
            print(f"       error: {r.error[:120]}")

    ok = sum(1 for row in rows if row["failure_category"] == "ok")
    strict_ok = sum(
        1
        for row in rows
        if row["failure_category"] == "ok" and row["silent_failure"] == 0
    )

    out_dir = _ROOT / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)

    baseline = {
        "heldout": rows,
        "summary": {
            "heldout_tasks": len(rows),
            "heldout_ok": ok,
            "heldout_strict_ok": strict_ok,
        },
    }

    baseline_path = out_dir / "agent_heldout_baseline.json"
    baseline_path.write_text(json.dumps(baseline, indent=2), encoding="utf-8")
    print(f"\nWrote {baseline_path}")

    csv_path = out_dir / "eval_agent_heldout.csv"
    write_eval_csv(results, csv_path)
    print(f"Wrote {csv_path}")
    print(json.dumps(baseline["summary"], indent=2))


if __name__ == "__main__":
    main()
