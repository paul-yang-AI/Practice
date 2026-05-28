"""L1: agent verification — navigation vs terminal outcome (generic, no site hardcoding)."""

from __future__ import annotations

import pytest

from task1_agent.agent.loop import infer_max_steps
from task1_agent.agent.verify import (
    verify_extracted_result,
    verify_navigation,
    verify_step,
    verify_task_outcome,
)


@pytest.mark.unit
def test_navigation_does_not_require_quoted_task_terms() -> None:
    task = "Search Wikipedia for 'Alan Turing' and verify the article page loads."
    page = "Wikipedia\nThe Free Encyclopedia\nMain Page content here " * 5
    nav = verify_navigation(
        url="https://en.wikipedia.org/wiki/Main_Page",
        page_text=page,
        start_url="https://en.wikipedia.org",
    )
    assert nav.passed, nav.reason

    step = verify_step(
        url="https://en.wikipedia.org/wiki/Main_Page",
        page_text=page,
        task=task,
        start_url="https://en.wikipedia.org",
        check_task_keywords=True,
    )
    assert not step.passed


@pytest.mark.unit
def test_intermediate_step_skips_task_keywords() -> None:
    task = "Search DuckDuckGo for 'playwright browser automation'"
    page = "DuckDuckGo\nPrivacy. Simplified.\n" * 5
    vr = verify_step(
        url="https://duckduckgo.com/",
        page_text=page,
        task=task,
        start_url="https://duckduckgo.com",
        check_task_keywords=False,
    )
    assert vr.passed, vr.reason


@pytest.mark.unit
def test_verify_extracted_result_in_json_page() -> None:
    page = '{"headers": {"User-Agent": "Mozilla/5.0 Chrome/120.0.0.0"}}'
    vr = verify_extracted_result("Mozilla/5.0 Chrome/120.0.0.0", page)
    assert vr.passed, vr.reason


@pytest.mark.unit
def test_verify_extracted_result_rejects_hallucination() -> None:
    page = '{"headers": {"User-Agent": "OtherAgent/1.0"}}'
    vr = verify_extracted_result("Mozilla/5.0 Chrome/120.0.0.0", page)
    assert not vr.passed


@pytest.mark.unit
def test_verify_task_outcome_requires_quoted_terms_on_final_page() -> None:
    task = "Search for 'Alan Turing' and verify results."
    fail = verify_task_outcome(
        task=task,
        url="https://example.com/",
        page_text="Example domain page with enough text " * 5,
        extracted_result="",
        start_url="https://example.com",
    )
    assert not fail.passed

    ok = verify_task_outcome(
        task=task,
        url="https://en.wikipedia.org/wiki/Alan_Turing",
        page_text="Alan Turing was a mathematician. " * 5,
        extracted_result="",
        start_url="https://en.wikipedia.org",
    )
    assert ok.passed, ok.reason


@pytest.mark.unit
def test_infer_max_steps_from_task_wording() -> None:
    assert infer_max_steps("Search DuckDuckGo for foo") == 15
    assert infer_max_steps("Extract the title from the page") == 12
    assert infer_max_steps("Go to example.com") == 10
