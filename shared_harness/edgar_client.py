"""SEC EDGAR client — single entry point for all SEC HTTP requests."""

from __future__ import annotations

import logging
import os
import re
import threading
import time
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

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


def _http_get(url: str, *, retries: int = 2) -> httpx.Response:
    """Throttled HTTP GET with SEC User-Agent and retry on 503."""
    ua = get_user_agent()
    headers = {"User-Agent": ua, "Accept-Encoding": "gzip, deflate"}
    last_exc: Exception | None = None
    for attempt in range(retries + 1):
        _throttle()
        with httpx.Client(timeout=60.0, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
        if response.status_code in (403, 429):
            raise EdgarRateLimitedError(f"SEC rate limited: HTTP {response.status_code}")
        if response.status_code == 503 and attempt < retries:
            logger.warning("SEC 503, retrying (%d/%d): %s", attempt + 1, retries, url)
            time.sleep(2 * (attempt + 1))
            continue
        response.raise_for_status()
        return response
    raise last_exc or EdgarClientError(f"Failed after {retries} retries: {url}")


def _lookup_cik_from_accession(accession: str) -> str | None:
    """Use EDGAR submissions API to find the company CIK that owns this filing."""
    filer_cik = accession.split("-")[0].lstrip("0") or "0"
    padded = filer_cik.zfill(10)
    submissions_url = f"https://data.sec.gov/submissions/CIK{padded}.json"
    logger.info("Looking up CIK from submissions: %s", submissions_url)
    try:
        resp = _http_get(submissions_url)
        import json as _json
        data = _json.loads(resp.text)
        company_cik = str(data.get("cik", "")).lstrip("0") or filer_cik
        recent = data.get("filings", {}).get("recent", {})
        accession_list = recent.get("accessionNumber", [])
        if accession in accession_list:
            return company_cik
        return company_cik
    except Exception as exc:
        logger.warning("CIK lookup failed for %s: %s", accession, exc)
        return None


def _try_resolve_index(cik_clean: str, accession: str) -> httpx.Response | None:
    """Try to fetch the filing index page for a given CIK."""
    accession_nodash = accession.replace("-", "")
    index_url = (
        f"https://www.sec.gov/Archives/edgar/data/{cik_clean}"
        f"/{accession_nodash}/{accession}-index.htm"
    )
    try:
        return _http_get(index_url)
    except (httpx.HTTPStatusError, EdgarClientError):
        return None


def resolve_filing_url(accession: str, cik: str | None = None) -> tuple[str, str]:
    """Resolve the primary 10-K HTML document URL from EDGAR filing index.

    Tries multiple CIK candidates: provided CIK, accession-derived CIK,
    and EDGAR submissions API lookup.

    Returns (url, resolved_cik).
    """
    accession_nodash = accession.replace("-", "")
    acc_prefix_cik = accession.split("-")[0].lstrip("0") or "0"

    cik_candidates: list[str] = []
    if cik:
        cik_candidates.append(cik.lstrip("0") or "0")
    cik_candidates.append(acc_prefix_cik)

    response = None
    resolved_cik = None
    for candidate in cik_candidates:
        response = _try_resolve_index(candidate, accession)
        if response is not None:
            resolved_cik = candidate
            break

    if response is None:
        looked_up = _lookup_cik_from_accession(accession)
        if looked_up and looked_up not in cik_candidates:
            response = _try_resolve_index(looked_up, accession)
            if response is not None:
                resolved_cik = looked_up

    if response is None:
        tried = ", ".join(cik_candidates)
        raise EdgarClientError(
            f"無法解析報表 URL — 嘗試了 CIK: {tried}。"
            f"請提供正確的 CIK 或直接貼上完整的 EDGAR 報表 URL。"
        )

    cik_clean = resolved_cik
    html = response.text
    base_path = f"/Archives/edgar/data/{cik_clean}/{accession_nodash}/"

    htm_links = re.findall(
        r'href="([^"]+\.htm[l]?)"',
        html,
        re.IGNORECASE,
    )
    if not htm_links:
        raise EdgarClientError(
            f"報表索引頁中未找到 .htm 文件：{base_path}"
        )

    filing_docs: list[str] = []
    for link in htm_links:
        ix_match = re.search(r"/ix\?doc=(.+)$", link)
        if ix_match:
            doc_path = ix_match.group(1)
            filing_docs.append(f"https://www.sec.gov{doc_path}")
            continue

        if link in ("/index.htm", "/index.html"):
            continue
        if "/searchedgar/" in link or "/edgar/searchedgar" in link:
            continue
        if "-index" in link:
            continue
        if "R1.htm" in link or "R2.htm" in link:
            continue
        if "-exh" in link.lower() or "exhibit" in link.lower():
            continue

        if link.startswith("/Archives/"):
            full = f"https://www.sec.gov{link}"
        elif link.startswith("/"):
            continue
        elif link.startswith("http"):
            full = link
        else:
            full = f"https://www.sec.gov{base_path}{link}"

        filing_docs.append(full)

    if not filing_docs:
        raise EdgarClientError(
            f"無法在索引頁中找到報表文件：{base_path}"
        )

    primary = filing_docs[0]
    for doc in filing_docs:
        if "_d2" not in doc and "_d3" not in doc:
            primary = doc
            break

    logger.info("Resolved filing URL: %s (CIK: %s)", primary, cik_clean)
    return primary, cik_clean


def fetch_filing_html(
    accession: str,
    url: str | None = None,
    *,
    cik: str | None = None,
    force_refresh: bool = False,
) -> tuple[str, str | None]:
    """Fetch filing HTML from EDGAR.

    Returns:
        (html_content, resolved_cik) — resolved_cik may differ from input cik.
    """
    path = cache_path(accession)

    if not force_refresh and path.exists():
        return path.read_text(encoding="utf-8", errors="replace"), cik

    resolved_cik = cik
    if not url:
        url, resolved_cik = resolve_filing_url(accession, cik=cik)

    try:
        response = _http_get(url)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            logger.warning("URL returned 404, resolving from EDGAR index: %s", url)
            url, resolved_cik = resolve_filing_url(accession, cik=cik)
            response = _http_get(url)
        else:
            raise

    html = response.text
    path.write_text(html, encoding="utf-8")
    return html, resolved_cik


def search_filings(
    company: str,
    form_type: str = "10-K",
    max_results: int = 10,
) -> list[dict]:
    """Search for SEC filings by ticker, CIK, or company name.

    Resolution order (generic, not ticker-specific hardcoding):
    1. Ticker-like query → SEC company_tickers.json → submissions API (latest form)
    2. EDGAR EFTS full-text search fallback
    """
    query = company.strip()
    if not query:
        return []

    results: list[dict] = []
    seen: set[str] = set()

    cik = resolve_cik_from_ticker(query)
    if cik:
        sub = _latest_filing_from_submissions(cik, form_type)
        if sub and sub["accession"] not in seen:
            results.append(sub)
            seen.add(sub["accession"])

    for hit in _search_filings_efts(query, form_type, max_results):
        if hit["accession"] not in seen:
            results.append(hit)
            seen.add(hit["accession"])

    return results[:max_results]


_TICKER_QUERY_RE = re.compile(r"^[A-Za-z]{1,5}(\.[A-Za-z]{1,2})?$")
_COMPANY_TICKERS_CACHE: dict | None = None
_COMPANY_TICKERS_LOCK = threading.Lock()


def _load_company_tickers() -> dict:
    """Fetch SEC company_tickers.json (cached in-process)."""
    global _COMPANY_TICKERS_CACHE
    with _COMPANY_TICKERS_LOCK:
        if _COMPANY_TICKERS_CACHE is not None:
            return _COMPANY_TICKERS_CACHE
        import json as _json

        url = "https://www.sec.gov/files/company_tickers.json"
        try:
            resp = _http_get(url)
            _COMPANY_TICKERS_CACHE = _json.loads(resp.text)
        except Exception as exc:
            logger.warning("company_tickers.json fetch failed: %s", exc)
            _COMPANY_TICKERS_CACHE = {}
        return _COMPANY_TICKERS_CACHE


def resolve_cik_from_ticker(query: str) -> str | None:
    """Resolve CIK from a ticker symbol using SEC company_tickers.json."""
    q = query.strip().upper()
    if not _TICKER_QUERY_RE.match(q):
        return None
    data = _load_company_tickers()
    for entry in data.values():
        if str(entry.get("ticker", "")).upper() == q:
            return str(entry.get("cik_str", "")).lstrip("0") or "0"
    return None


def _latest_filing_from_submissions(cik: str, form_type: str = "10-K") -> dict | None:
    """Return the most recent filing of form_type for a CIK via submissions API."""
    import json as _json

    cik_clean = cik.lstrip("0") or "0"
    padded = cik_clean.zfill(10)
    url = f"https://data.sec.gov/submissions/CIK{padded}.json"
    try:
        resp = _http_get(url)
        data = _json.loads(resp.text)
    except Exception as exc:
        logger.warning("Submissions lookup failed for CIK %s: %s", cik, exc)
        return None

    name = data.get("name", "")
    tickers = data.get("tickers", [])
    ticker = tickers[0] if tickers else ""

    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accessions = recent.get("accessionNumber", [])
    dates = recent.get("filingDate", [])

    target = form_type.upper().replace(" ", "")
    for form, accession, filed in zip(forms, accessions, dates):
        if form.upper().replace(" ", "") == target:
            return {
                "company": name,
                "ticker": ticker,
                "cik": cik_clean,
                "accession": accession,
                "filed": filed,
                "form": form,
                "source": "submissions",
            }
    return None


def _search_filings_efts(
    company: str,
    form_type: str = "10-K",
    max_results: int = 10,
) -> list[dict]:
    """Search EDGAR EFTS for filings by company name or free text."""
    import json as _json
    from urllib.parse import quote

    query = quote(company)
    url = (
        f"https://efts.sec.gov/LATEST/search-index?"
        f"q={query}&forms={form_type}"
        f"&dateRange=custom&startdt=2020-01-01&enddt=2026-12-31"
    )
    logger.info("EDGAR EFTS search: %s", url)

    try:
        resp = _http_get(url)
    except Exception:
        url_fallback = (
            f"https://efts.sec.gov/LATEST/search-index?"
            f"q=%22{query}%22&forms={form_type}"
        )
        try:
            resp = _http_get(url_fallback)
        except Exception as exc:
            logger.warning("EDGAR EFTS search failed: %s", exc)
            return []

    try:
        data = _json.loads(resp.text)
    except Exception:
        return []

    hits = data.get("hits", {}).get("hits", [])
    results: list[dict] = []
    for hit in hits[:max_results]:
        src = hit.get("_source", {})
        entity = src.get("entity_name", "")
        filed = src.get("file_date", "")
        form = src.get("form_type", form_type)

        file_parts = hit.get("_id", "").split(":")
        accession = file_parts[0] if file_parts else ""
        if not accession:
            continue

        tickers = src.get("tickers", "")
        if isinstance(tickers, list):
            ticker = tickers[0] if tickers else ""
        else:
            ticker = str(tickers)

        cik = str(src.get("entity_id", ""))

        results.append({
            "company": entity,
            "ticker": ticker,
            "cik": cik,
            "accession": accession,
            "filed": filed,
            "form": form,
            "source": "efts",
        })

    return results


def find_proxy_filing(cik: str) -> dict | None:
    """Find the most recent DEF 14A (proxy statement) for a CIK.

    Returns dict with keys: accession, filed, form, cik — or None if not found.
    """
    import json as _json

    cik_clean = cik.lstrip("0") or "0"
    padded = cik_clean.zfill(10)
    url = f"https://data.sec.gov/submissions/CIK{padded}.json"
    try:
        resp = _http_get(url)
        data = _json.loads(resp.text)
    except Exception as exc:
        logger.warning("Proxy lookup failed for CIK %s: %s", cik, exc)
        return None

    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    accessions = recent.get("accessionNumber", [])
    dates = recent.get("filingDate", [])

    for form, accession, filed in zip(forms, accessions, dates):
        if form in ("DEF 14A", "DEFA14A"):
            return {
                "accession": accession,
                "filed": filed,
                "form": form,
                "cik": cik_clean,
                "url": (
                    f"https://www.sec.gov/cgi-bin/browse-edgar?"
                    f"action=getcompany&CIK={cik_clean}&type=DEF+14A&dateb=&owner=include&count=10"
                ),
            }
    return None


def reset_throttle_for_tests() -> None:
    global _last_request_at, _user_agent_validated, _COMPANY_TICKERS_CACHE
    with _lock:
        _last_request_at = 0.0
    _user_agent_validated = False
    _COMPANY_TICKERS_CACHE = None
