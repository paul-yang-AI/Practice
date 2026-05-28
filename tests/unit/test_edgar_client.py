import time
from pathlib import Path
from unittest.mock import patch

import pytest

from shared_harness import edgar_client
from shared_harness.edgar_client import (
    EdgarConfigurationError,
    cache_path,
    fetch_filing_html,
    get_user_agent,
)


@pytest.mark.unit
def test_edgar_requires_user_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SEC_USER_AGENT", raising=False)
    edgar_client.reset_throttle_for_tests()
    with pytest.raises(EdgarConfigurationError):
        get_user_agent()


@pytest.mark.unit
def test_edgar_cache_hit_zero_network(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    accession = "0000000000-00-000001"
    cache_file = tmp_path / f"{accession}.html"
    cache_file.write_text("<html>cached</html>", encoding="utf-8")
    monkeypatch.setattr(edgar_client, "_CACHE_DIR", tmp_path)

    with patch("httpx.Client.get") as mock_get:
        html, _cik, _url = fetch_filing_html(accession, url="https://sec.gov/example")
        mock_get.assert_not_called()

    assert "cached" in html


@pytest.mark.unit
def test_cik_from_accession() -> None:
    from shared_harness.edgar_client import cik_from_accession

    assert cik_from_accession("0000950170-24-087843") == "950170"
    assert cik_from_accession("0001083301-26-000031") == "1083301"


@pytest.mark.unit
def test_normalize_search_hit_enriches_from_submissions(monkeypatch: pytest.MonkeyPatch) -> None:
    from shared_harness.edgar_client import normalize_search_hit

    def _fake_submissions(cik: str):
        assert cik == "1083301"
        return {"name": "EXAMPLE CORP", "tickers": ["EXMP"]}

    monkeypatch.setattr("shared_harness.edgar_client._fetch_submissions", _fake_submissions)
    raw = {
        "company": "",
        "ticker": "",
        "cik": "",
        "accession": "0001083301-26-000031",
        "filed": "2026-02-27",
        "source": "efts",
    }
    out = normalize_search_hit(raw)
    assert out is not None
    assert out["company"] == "EXAMPLE CORP"
    assert out["ticker"] == "EXMP"
    assert out["cik"] == "1083301"


@pytest.mark.unit
def test_normalize_search_hit_drops_unidentified() -> None:
    from shared_harness.edgar_client import normalize_search_hit

    assert normalize_search_hit({
        "company": "",
        "ticker": "",
        "cik": "",
        "accession": "bad-format",
        "filed": "",
        "source": "efts",
    }) is None


@pytest.mark.unit
def test_search_quality_hint_for_keyword() -> None:
    from shared_harness.edgar_client import search_quality_hint

    assert search_quality_hint("google") is not None
    assert search_quality_hint("GOOGL") is None


@pytest.mark.unit
def test_format_filing_search_label() -> None:
    from shared_harness.edgar_client import format_filing_search_label

    label = format_filing_search_label({
        "company": "MICROSOFT CORP",
        "ticker": "MSFT",
        "accession": "0000950170-24-087843",
        "filed": "2024-07-30",
        "source": "submissions",
    })
    assert "MICROSOFT CORP (MSFT)" in label
    assert "ticker 精準" in label


@pytest.mark.unit
def test_edgar_rate_limit_throttle(monkeypatch: pytest.MonkeyPatch) -> None:
    edgar_client.reset_throttle_for_tests()
    monkeypatch.setattr(edgar_client, "_MIN_INTERVAL_SEC", 0.05)
    t0 = time.monotonic()
    edgar_client._throttle()
    edgar_client._throttle()
    elapsed = time.monotonic() - t0
    assert elapsed >= 0.04
