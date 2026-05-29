"""Map natural-language tasks to structured intent (generic, not site-specific)."""

from __future__ import annotations

import re

_SEARCH_TASK_RE = re.compile(
    r"\b(search|find|query|look\s*up)\b|搜[寻尋]|搜索|查詢|寻找|尋找",
    re.I,
)

_QUERY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"(?:search(?:\s+for)?|find|look\s+up|query)\s+(?:for\s+)?['\"]?(.+?)['\"]?"
        r"(?:\s+and|\s+on|\s+in|\s+verify|\s+then|\.|$)",
        re.I,
    ),
    re.compile(
        r"(?:搜[寻尋]|搜索|查詢|寻找|尋找)\s*[「『\"']?(.+?)(?:[。\.]|$)",
        re.I,
    ),
    re.compile(
        r"(?:for|about|on)\s+['\"]([^'\"]+)['\"]",
        re.I,
    ),
]


def task_implies_search(task: str) -> bool:
    """True when the task description implies a search/find interaction."""
    return bool(_SEARCH_TASK_RE.search(task))


def extract_search_query(task: str) -> str | None:
    """Extract a search/query string from free-form task text."""
    quoted = re.findall(r"['\"]([^'\"]+)['\"]", task)
    for q in reversed(quoted):
        cleaned = q.strip()
        if len(cleaned) >= 2:
            return cleaned

    for pattern in _QUERY_PATTERNS:
        match = pattern.search(task.strip())
        if not match:
            continue
        query = match.group(1).strip(" '\"，。.;")
        if len(query) >= 2:
            return query
    return None


def normalize_type_action(task: str, selector: str, value: str) -> tuple[str, str, bool]:
    """Repair type actions: fill missing value from task intent for search tasks."""
    selector = (selector or "").strip()
    value = (value or "").strip()
    if value:
        return selector, value, False
    if not task_implies_search(task):
        return selector, value, False
    query = extract_search_query(task)
    if query:
        return selector, query, True
    return selector, value, False
