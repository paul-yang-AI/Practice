"""L3 agent task eval — manifest depth + train split policy."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from shared_harness.eval_runner import load_tasks, run_agent_eval, summarize_eval
from task1_agent.agent.loop import StepResult, run as agent_run
from task1_agent.agent.verify import VerifyResult

TASKS_PATH = Path(__file__).resolve().parents[2] / "task1_agent" / "eval" / "tasks.yaml"


@pytest.mark.eval
def test_agent_tasks_manifest_depth() -> None:
    manifest = load_tasks(TASKS_PATH)
    tasks = manifest["tasks"]
    train = [t for t in tasks if t.get("split", "train") == "train"]
    domains = {t.get("domain") for t in tasks}
    task_types = {t.get("task_type") for t in tasks}

    assert len(tasks) >= 9
    assert len(train) >= 5
    assert len(domains) >= 4
    assert len(task_types) >= 3
    heldout = [t for t in tasks if t.get("split") == "heldout"]
    assert any(t["id"] == "python_docs_heldout" for t in heldout)


@pytest.mark.unit
def test_verify_task_outcome_success_hints() -> None:
    from task1_agent.agent.verify import verify_task_outcome

    ok = verify_task_outcome(
        task="Navigate docs",
        url="https://docs.python.org/3/tutorial/index.html",
        page_text="Python documentation tutorial overview",
        start_url="https://docs.python.org/3/",
        task_type="navigate",
        success_hints={"expect_body_contains": "Python"},
    )
    assert ok.passed

    bad = verify_task_outcome(
        task="Navigate docs",
        url="https://example.com/",
        page_text="Example Domain",
        start_url="https://docs.python.org/3/",
        success_hints={"expect_url_contains": "/3/"},
    )
    assert not bad.passed


@pytest.mark.eval
def test_agent_tasks_silent_failure_zero_with_mock_executor() -> None:
    """Train tasks with deterministic mock executor — no silent success."""

    def _page_for_task(task_desc: str) -> tuple[str, str]:
        t = task_desc.lower()
        if "alan turing" in t or "wikipedia" in t:
            return (
                "https://en.wikipedia.org/wiki/Alan_Turing",
                "Alan Turing was a mathematician and computer scientist. " * 5,
            )
        if "httpbin" in t or "user-agent" in t:
            return (
                "https://httpbin.org/headers",
                '{"headers": {"User-Agent": "Mozilla/5.0 MockAgent/1.0"}}',
            )
        if "hacker news" in t or "ranked story" in t:
            return (
                "https://news.ycombinator.com/",
                "Mock HN Title — top ranked story on the front page. " * 3,
            )
        if "cpython" in t or "repository" in t:
            return (
                "https://github.com/python/cpython",
                "python / cpython repository title visible " * 3,
            )
        return (
            "https://example.com",
            "Example Domain\nThis domain is for use in illustrative examples.",
        )

    def mock_executor(action: str, context: dict) -> StepResult:
        step_idx = context.get("step", 0)
        planned = context.get("planned_action")
        task_desc = context.get("task", "")
        url, page_text = _page_for_task(task_desc)
        if step_idx == 0:
            return StepResult(
                step_index=step_idx,
                action=action,
                url=url,
                page_text=page_text,
                a11y_tree="<root>mock</root>",
                verify=VerifyResult(passed=True),
            )
        if planned and planned.get("done"):
            return StepResult(
                step_index=step_idx,
                action="task_complete",
                url=url,
                page_text=page_text,
                verify=VerifyResult(passed=True),
                extracted_result=planned.get("result", "mock result"),
            )
        return StepResult(
            step_index=step_idx,
            action=action,
            url=url,
            page_text=page_text,
            verify=VerifyResult(passed=True),
        )

    def mock_plan(task_description, *_args, **_kwargs):
        _, page_text = _page_for_task(task_description)
        snippet = page_text[:80].strip()
        return {
            "done": True,
            "action": "none",
            "selector": "",
            "value": "",
            "reasoning": "Task complete in mock eval",
            "result": snippet,
        }

    def mock_extract(*, task_description, page_text, **_kwargs):
        _, text = _page_for_task(task_description)
        if "User-Agent" in task_description or "httpbin" in task_description.lower():
            return "Mozilla/5.0 MockAgent/1.0"
        if "story" in task_description.lower():
            return "Mock HN Title"
        if "Example Domain" in text:
            return "Example Domain"
        return text.split("\n")[0][:120]

    manifest = load_tasks(TASKS_PATH)
    train = [t for t in manifest["tasks"] if t.get("split", "train") == "train"]

    with patch("task1_agent.agent.loop._plan_next_action", side_effect=mock_plan), patch(
        "task1_agent.agent.loop.extract_from_page", side_effect=mock_extract
    ):
        from shared_harness import job_store

        results = []
        for task in train:
            run_id = job_store.create_run("agent")
            result = agent_run(
                task_description=task["description"],
                start_url=task.get("start_url", "https://example.com"),
                run_id=run_id,
                execute_action=mock_executor,
            )
            results.append(result)

    assert all(r.status == "success" for r in results)
    assert sum(1 for r in results if not r.extracted_result) == 0


@pytest.mark.eval
def test_agent_eval_csv_fields_when_included(tmp_path: Path) -> None:
    import csv

    from shared_harness.eval_runner import AgentEvalResult, FilingEvalResult, run_eval, write_eval_csv

    sec = FilingEvalResult(
        accession="0000950170-24-087843",
        ticker="MSFT",
        cik="789019",
        split="train",
        required_items_found=4,
        required_items_total=4,
    )
    agent = AgentEvalResult(
        task_id="smoke_example_title",
        domain="example.com",
        task_type="navigate",
        split="train",
        status="success",
        steps=2,
        elapsed_s=1.0,
    )
    csv_path = write_eval_csv([sec, agent], tmp_path / "eval_train.csv")
    with csv_path.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    assert len(rows) == 2
    assert rows[0]["task"] == "sec_10k"
    assert rows[1]["task"] == "agent"
    assert "failure_category" in rows[0]
    assert "silent_failure" in rows[1]

    # run_eval without agent still works (SEC only)
    sec_only = Path(run_eval(split="train", output_dir=str(tmp_path / "sec_only")))
    with sec_only.open(encoding="utf-8") as fh:
        sec_rows = list(csv.DictReader(fh))
    assert len(sec_rows) == 3
    assert all(r["task"] == "sec_10k" for r in sec_rows)

    summary = summarize_eval([sec, agent])
    assert summary["agent_success_rate"] == 1.0
    assert summary["agent_silent_failures"] == 0
