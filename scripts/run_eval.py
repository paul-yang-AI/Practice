"""Eval runner stub — full implementation on Day 4."""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default="train")
    parser.add_argument("--output", default="reports")
    args = parser.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / "eval_stub.csv"
    csv_path.write_text("phase,status\n0,scaffold\n", encoding="utf-8")
    print(f"Wrote {csv_path} (split={args.split})")


if __name__ == "__main__":
    main()
