import pytest

from shared_harness.eval_ui import benchmark_kpi_items, kpi_row_html


@pytest.mark.unit
def test_benchmark_kpi_items_with_agent() -> None:
    summary = {
        "sec_ok": 3,
        "sec_filings": 3,
        "agent_tasks": 5,
        "agent_success_rate": 1.0,
        "agent_latency_p50": 9.29,
        "agent_usd_p50": 0.0077,
    }
    items = benchmark_kpi_items(summary)
    assert len(items) == 4
    assert items[0] == ("SEC 10-K", "3/3", "")
    assert items[1][0] == "Agent Train"
    assert items[1][1] == "5/5"


@pytest.mark.unit
def test_benchmark_kpi_items_sec_only() -> None:
    summary = {"sec_ok": 2, "sec_filings": 3, "agent_tasks": 0}
    items = benchmark_kpi_items(summary)
    assert items[1][0] == "Agent Train"
    assert items[1][1] == "—"


@pytest.mark.unit
def test_kpi_row_html_renders_values() -> None:
    html = kpi_row_html(
        {
            "sec_ok": 3,
            "sec_filings": 3,
            "agent_tasks": 5,
            "agent_success_rate": 1.0,
            "agent_latency_p50": 9.29,
            "agent_usd_p50": 0.0077,
        }
    )
    assert "SEC 10-K" in html
    assert "3/3" in html
    assert "Agent Train" in html
    assert "5/5" in html
    assert "<script" not in html
