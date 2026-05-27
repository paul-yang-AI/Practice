"""Run held-out SEC filing eval (local snapshot only — not for tuning)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from shared_harness.env import load_env
from shared_harness.eval_runner import run_sec_eval


def main() -> None:
    load_env()
    results = run_sec_eval(split="heldout", use_arbiter=False)
    snapshot = []
    for r in results:
        snapshot.append(
            {
                "accession": r.accession,
                "ticker": r.ticker,
                "split": r.split,
                "required_items_found": r.required_items_found,
                "required_items_total": r.required_items_total,
                "tier0_extracted_count": r.tier0_extracted_count,
                "incorporated_count": r.incorporated_count,
                "missing_count": r.missing_count,
                "failure_category": r.failure_category,
            }
        )
        print(
            f"{r.ticker or r.accession}: {r.required_items_found}/{r.required_items_total} required, "
            f"extracted={r.tier0_extracted_count}, failure={r.failure_category}"
        )

    out = _ROOT / "reports" / "heldout_snapshot.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
