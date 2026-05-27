"""Run SEC manifest eval and export CSV."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from shared_harness.env import load_env
from shared_harness.eval_runner import run_eval


def main() -> None:
    load_env()
    parser = argparse.ArgumentParser(description="Run SEC 10-K eval harness")
    parser.add_argument("--split", default="train", choices=["train", "heldout"])
    parser.add_argument("--output", default="reports")
    args = parser.parse_args()
    csv_path = run_eval(split=args.split, output_dir=args.output)
    print(f"Wrote {csv_path} (split={args.split})")


if __name__ == "__main__":
    main()
