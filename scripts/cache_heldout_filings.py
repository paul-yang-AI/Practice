"""Download and cache HTML for held-out manifest filings (Phase 0)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from shared_harness.env import load_env
from shared_harness.eval_runner import DEFAULT_MANIFEST, load_manifest
from shared_harness.edgar_client import cache_path
from task2_sec.pipeline.fetch import fetch_filing_html


def main() -> None:
    load_env()
    manifest = load_manifest(DEFAULT_MANIFEST)
    heldout = [f for f in manifest["filings"] if f.get("split") == "heldout"]
    cached = 0
    fetched = 0
    for filing in heldout:
        accession = filing["accession"]
        path = cache_path(accession)
        if path.exists():
            cached += 1
            print(f"SKIP (cached) {filing.get('ticker', '?')} {accession}")
            continue
        print(f"FETCH {filing.get('ticker', '?')} {accession} …")
        html, _, url = fetch_filing_html(
            accession,
            url=filing.get("url"),
            cik=filing.get("cik"),
            force_refresh=True,
        )
        fetched += 1
        print(f"  OK {len(html):,} chars → {path.name} ({url or filing.get('url', '')})")

    print(f"\nDone: {cached} already cached, {fetched} newly fetched, {len(heldout)} held-out total.")


if __name__ == "__main__":
    main()
