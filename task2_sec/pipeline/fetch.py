"""Fetch filing HTML via shared_harness.edgar_client (sole SEC entry point)."""

from __future__ import annotations

from shared_harness import edgar_client


def fetch_filing_html(accession: str, url: str | None = None) -> str:
    """Return filing HTML; cached at task2_sec/eval/cache/{accession}.html."""
    return edgar_client.fetch_filing_html(accession, url=url)
