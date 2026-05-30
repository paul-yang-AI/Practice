"""Pure helpers for Browser Agent Streamlit page (unit-testable without Streamlit)."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def agent_heldout_badge(
    *,
    failure_category: str,
    status: str = "",
    silent_failure: int = 0,
) -> tuple[str, str]:
    """Return (emoji, short label) for held-out task baseline outcome."""
    cat = failure_category or "unknown"
    if cat == "ok" and silent_failure == 0:
        return "✅", "基線預期通過"
    if cat == "silent_failure" or silent_failure:
        return "⚠️", "silent failure"
    if cat == "max_steps":
        return "❌", f"預期失敗 — {cat}"
    if cat in ("reasoning_failure", "outcome_verify_fail", "recovery_exhausted"):
        return "❌", f"預期失敗 — {cat}"
    if status == "blocked":
        return "🚫", "blocked"
    return "⚠️", f"基線 {cat}"


def format_heldout_task_label(
    task: dict[str, Any],
    baseline_row: dict[str, Any] | None,
) -> str:
    """Dropdown label: task id + domain + baseline badge."""
    tid = task.get("id", "")
    domain = task.get("domain", "")
    if baseline_row:
        emoji, blabel = agent_heldout_badge(
            failure_category=str(baseline_row.get("failure_category", "")),
            status=str(baseline_row.get("status", "")),
            silent_failure=int(baseline_row.get("silent_failure") or 0),
        )
        badge = f"{emoji} {blabel}"
    else:
        badge = "🔬 未跑基線"
    notes = (task.get("notes") or "").strip()
    note_bit = f" — {notes[:50]}…" if len(notes) > 50 else (f" — {notes}" if notes else "")
    return f"{tid} ({domain}, {task.get('task_type', '')}) · {badge}{note_bit}"


def baseline_by_task_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(r.get("task_id")): r for r in rows if r.get("task_id")}


def sync_task_form_on_selection(
    session: dict[str, Any],
    *,
    key_prefix: str,
    selection_id: str,
    task: str,
    start_url: str,
    overwrite_fields: bool = True,
) -> bool:
    """When a dropdown/preset selection changes, update widget session keys.

    Returns True if fields were synced (selection changed).
    """
    active_key = f"{key_prefix}_active_id"
    if session.get(active_key) == selection_id:
        return False
    session[active_key] = selection_id
    if overwrite_fields:
        session[f"{key_prefix}_task"] = task
        session[f"{key_prefix}_url"] = start_url
    return True


def ensure_task_form_defaults(
    session: dict[str, Any],
    *,
    key_prefix: str,
    default_task: str,
    default_url: str,
) -> None:
    """Seed widget keys on first visit only."""
    task_key = f"{key_prefix}_task"
    url_key = f"{key_prefix}_url"
    if task_key not in session:
        session[task_key] = default_task
    if url_key not in session:
        session[url_key] = default_url


def sort_heldout_tasks_for_ui(
    tasks: list[dict[str, Any]],
    baseline_map: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Baseline-pass tasks first so default URL matches a known-good held-out case."""

    def _rank(t: dict[str, Any]) -> tuple[int, str]:
        row = baseline_map.get(str(t.get("id", "")))
        if row and row.get("failure_category") == "ok" and not row.get("silent_failure"):
            return (0, str(t.get("id", "")))
        return (1, str(t.get("id", "")))

    return sorted(tasks, key=_rank)
