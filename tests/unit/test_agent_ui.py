import pytest

from shared_harness.agent_ui import (
    agent_heldout_badge,
    ensure_task_form_defaults,
    format_heldout_task_label,
    sort_heldout_tasks_for_ui,
    sync_task_form_on_selection,
)


@pytest.mark.unit
def test_agent_heldout_badge_ok() -> None:
    emoji, label = agent_heldout_badge(failure_category="ok", status="success", silent_failure=0)
    assert emoji == "✅"
    assert "通過" in label


@pytest.mark.unit
def test_agent_heldout_badge_max_steps() -> None:
    emoji, label = agent_heldout_badge(failure_category="max_steps", status="failed")
    assert emoji == "❌"
    assert "max_steps" in label


@pytest.mark.unit
def test_format_heldout_task_label() -> None:
    task = {
        "id": "python_docs_heldout",
        "domain": "docs.python.org",
        "task_type": "navigate",
        "notes": "Frozen held-out",
    }
    row = {"failure_category": "ok", "status": "success", "silent_failure": 0}
    label = format_heldout_task_label(task, row)
    assert "python_docs_heldout" in label
    assert "✅" in label


@pytest.mark.unit
def test_sync_task_form_on_selection_updates_fields() -> None:
    session: dict = {}
    changed = sync_task_form_on_selection(
        session,
        key_prefix="heldout",
        selection_id="python_docs_heldout",
        task="Navigate to docs",
        start_url="https://docs.python.org/3/",
    )
    assert changed
    assert session["heldout_active_id"] == "python_docs_heldout"
    assert session["heldout_url"] == "https://docs.python.org/3/"

    changed2 = sync_task_form_on_selection(
        session,
        key_prefix="heldout",
        selection_id="python_docs_heldout",
        task="other",
        start_url="https://example.com",
    )
    assert not changed2
    assert session["heldout_url"] == "https://docs.python.org/3/"


@pytest.mark.unit
def test_sync_task_form_skips_overwrite_for_custom_preset() -> None:
    session = {"train_task": "keep me", "train_url": "https://keep.test"}
    sync_task_form_on_selection(
        session,
        key_prefix="train",
        selection_id="custom",
        task="",
        start_url="",
        overwrite_fields=False,
    )
    assert session["train_task"] == "keep me"
    assert session["train_url"] == "https://keep.test"


@pytest.mark.unit
def test_ensure_task_form_defaults_only_seeds_missing() -> None:
    session = {"heldout_url": "https://existing.test"}
    ensure_task_form_defaults(
        session,
        key_prefix="heldout",
        default_task="default task",
        default_url="https://default.test",
    )
    assert session["heldout_task"] == "default task"
    assert session["heldout_url"] == "https://existing.test"


@pytest.mark.unit
def test_sort_heldout_tasks_puts_baseline_ok_first() -> None:
    tasks = [
        {"id": "duckduckgo_search"},
        {"id": "python_docs_heldout"},
        {"id": "forms_heldout"},
    ]
    baseline = {
        "python_docs_heldout": {"failure_category": "ok", "silent_failure": 0},
        "forms_heldout": {"failure_category": "max_steps", "silent_failure": 0},
    }
    ordered = sort_heldout_tasks_for_ui(tasks, baseline)
    assert ordered[0]["id"] == "python_docs_heldout"
