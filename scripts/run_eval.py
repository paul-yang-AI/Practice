"""Run SEC + optional agent eval and export CSV."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from shared_harness.env import load_env
from shared_harness.eval_runner import (
    run_agent_eval,
    run_eval,
    run_sec_eval,
    summarize_eval,
    write_eval_csv,
)


def main() -> None:
    load_env()
    parser = argparse.ArgumentParser(description="Run eval harness (SEC 10-K + optional agent)")
    parser.add_argument("--split", default="train", choices=["train", "heldout"])
    parser.add_argument("--output", default="reports")
    parser.add_argument(
        "--include-agent",
        action="store_true",
        help="Include live Browser Agent tasks (train split only; requires Playwright + LLM key)",
    )
    parser.add_argument(
        "--write-summary",
        action="store_true",
        help="Write eval_summary.json alongside CSV",
    )
    args = parser.parse_args()

    if args.include_agent and args.split == "train":
        sec_results = run_sec_eval(split="train", use_arbiter=False)
        agent_results = run_agent_eval(split="train")
        results = [*sec_results, *agent_results]
        out_dir = Path(args.output)
        csv_path = out_dir / "eval_train.csv"
        write_eval_csv(results, csv_path)
        write_eval_csv(results, out_dir / "latest.csv")
        csv_path = str(csv_path)
    else:
        csv_path = run_eval(split=args.split, output_dir=args.output, include_agent=False)

    print(f"Wrote {csv_path} (split={args.split}, agent={args.include_agent})")

    if args.write_summary:
        from shared_harness.eval_runner import FilingEvalResult, AgentEvalResult
        import csv

        rows: list = []
        with open(csv_path, encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                if row["task"] == "sec_10k":
                    rows.append(
                        FilingEvalResult(
                            accession=row["record_id"],
                            ticker=row["domain"],
                            cik="",
                            split=row["split"],
                            required_items_found=int(row["required_items_found"]),
                            required_items_total=int(row["required_items_total"]),
                            failure_category=row["failure_category"],
                        )
                    )
                elif row["task"] == "agent":
                    rows.append(
                        AgentEvalResult(
                            task_id=row["record_id"],
                            domain=row["domain"],
                            task_type=row["task_type"],
                            split=row["split"],
                            status=row["status"],
                            steps=int(row["steps"] or 0),
                            elapsed_s=float(row["elapsed_s"] or 0),
                            recovery_count=int(row["recovery_count"] or 0),
                            llm_calls=int(row["llm_calls"] or 0),
                            silent_failure=int(row["silent_failure"] or 0),
                            failure_category=row["failure_category"],
                        )
                    )
        summary = summarize_eval(rows)
        summary_path = Path(args.output) / "eval_summary.json"
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(f"Wrote {summary_path}")
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
