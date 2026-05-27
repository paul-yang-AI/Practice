"""SEC EDGAR client — single entry point for all SEC HTTP requests."""

from __future__ import annotations

import os
import re
import threading
import time
from pathlib import Path

import httpx

_CACHE_DIR = Path(__file__).resolve().parent.parent / "task2_sec" / "eval" / "cache"
_MIN_INTERVAL_SEC = 0.11
_lock = threading.Lock()
_last_request_at = 0.0
_user_agent_validated = False


class EdgarClientError(Exception):
    """Base EDGAR client error."""


class EdgarConfigurationError(EdgarClientError):
    """Missing or invalid SEC configuration."""


class EdgarRateLimitedError(EdgarClientError):
    """SEC returned 403/429."""


def _validate_user_agent() -> str:
    global _user_agent_validated
    ua = os.environ.get("SEC_USER_AGENT", "").strip()
    if not ua:
        raise EdgarConfigurationError(
            "SEC_USER_AGENT is required (format: 'CompanyName ContactName email@domain.com')"
        )
    if not re.search(r"\S+\s+\S+\s+\S+@\S+\.\S+", ua):
        raise EdgarConfigurationError(
            f"SEC_USER_AGENT format invalid: {ua!r}. Expected 'Company Contact email@domain.com'"
        )
    _user_agent_validated = True
    return ua


def get_user_agent() -> str:
    if not _user_agent_validated:
        return _validate_user_agent()
    ua = os.environ.get("SEC_USER_AGENT", "").strip()
    if not ua:
        raise EdgarConfigurationError("SEC_USER_AGENT is required")
    return ua


def cache_path(accession: str) -> Path:
    safe = accession.replace("/", "-")
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _CACHE_DIR / f"{safe}.html"


def _throttle() -> None:
    global _last_request_at
    with _lock:
        elapsed = time.monotonic() - _last_request_at
        if elapsed < _MIN_INTERVAL_SEC:
            time.sleep(_MIN_INTERVAL_SEC - elapsed)
        _last_request_at = time.monotonic()


def fetch_filing_html(accession: str, url: str | None = None) -> str:
    """Fetch filing HTML; returns cached content when available."""
    path = cache_path(accession)
    if path.exists():
        return path.read_text(encoding="utf-8", errors="replace")

    ua = get_user_agent()
    if not url:
        raise EdgarClientError("url is required when cache miss")

    _throttle()
    headers = {"User-Agent": ua, "Accept-Encoding": "gzip, deflate"}
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        response = client.get(url, headers=headers)
    if response.status_code in (403, 429):
        raise EdgarRateLimitedError(f"SEC rate limited: HTTP {response.status_code}")
    response.raise_for_status()
    html = response.text
    path.write_text(html, encoding="utf-8")
    return html


def reset_throttle_for_tests() -> None:
    global _last_request_at, _user_agent_validated
    with _lock:
        _last_request_at = 0.0
    _user_agent_validated = False
