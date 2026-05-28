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
        html, _cik = fetch_filing_html(accession, url="https://sec.gov/example")
        mock_get.assert_not_called()

    assert "cached" in html


@pytest.mark.unit
def test_edgar_rate_limit_throttle(monkeypatch: pytest.MonkeyPatch) -> None:
    edgar_client.reset_throttle_for_tests()
    monkeypatch.setattr(edgar_client, "_MIN_INTERVAL_SEC", 0.05)
    t0 = time.monotonic()
    edgar_client._throttle()
    edgar_client._throttle()
    elapsed = time.monotonic() - t0
    assert elapsed >= 0.04
