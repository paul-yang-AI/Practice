"""Pure helpers for SEC 10-K Streamlit page (unit-testable without Streamlit)."""

from __future__ import annotations

from task2_sec.pipeline.content_quality import assess_required_item


def default_required_items(manifest_default: list[str] | None = None) -> list[str]:
    return list(manifest_default or ["1", "1A", "7", "8"])


def required_item_satisfied(item_id: str, text: str | None, status_value: str) -> bool:
    """Match eval_runner strict required-item check."""
    quality = assess_required_item(item_id, text, status_value)
    return quality in {"ok", "incorporated", "low_confidence", "cross_ref"}


def compute_required_kpi(
    items: list,
    required_item_ids: list[str],
) -> dict:
    """Summarize Required KPI for UI (primary pass/fail metric)."""
    by_id = {
        (i.get("item_id") if isinstance(i, dict) else i.item_id): i
        for i in items
    }
    found = 0
    prose = 0
    missing_ids: list[str] = []
    failing_ids: list[str] = []

    for item_id in required_item_ids:
        item = by_id.get(item_id)
        if item is None:
            missing_ids.append(item_id)
            failing_ids.append(item_id)
            continue
        if isinstance(item, dict):
            text = item.get("text")
            status = str(item.get("status", "missing"))
        else:
            text = item.text
            status = item.status.value
        quality = assess_required_item(item_id, text, status)
        if quality == "ok":
            prose += 1
        if required_item_satisfied(item_id, text, status):
            found += 1
        else:
            failing_ids.append(item_id)

    total = len(required_item_ids)
    passed = found == total and not failing_ids
    return {
        "found": found,
        "total": total,
        "prose": prose,
        "passed": passed,
        "missing_ids": missing_ids,
        "failing_ids": failing_ids,
        "label": f"{found}/{total}",
    }


def format_required_kpi_banner(
    *,
    ticker: str,
    required_item_ids: list[str],
    kpi: dict,
) -> tuple[str, str]:
    """Return (markdown_html, severity) for train-tab KPI callout."""
    items_str = ", ".join(required_item_ids)
    if kpi["passed"]:
        return (
            f"**Required KPI ✅ {kpi['label']}** — "
            f"{ticker or 'Filing'} 必需項 `{items_str}` 全部通過 "
            f"（真實正文 {kpi['prose']}/{kpi['total']}）。"
            "此為 Eval train 主指標。",
            "success",
        )
    fail = ", ".join(kpi["failing_ids"]) or "—"
    return (
        f"**Required KPI ❌ {kpi['label']}** — "
        f"必需項 `{items_str}`；未達標 Item：**{fail}**。"
        "TOC stub / missing 不算通過。",
        "error",
    )


def heldout_outcome_badge(
    *,
    failure_category: str,
    required_found: int,
    required_total: int,
) -> tuple[str, str]:
    """Return (emoji, short label) for held-out filing expected baseline outcome."""
    req = f"{required_found}/{required_total}"
    cat = failure_category or "unknown"
    if cat == "ok":
        return "✅", f"基線預期通過 ({req})"
    if cat == "toc_stub_required_item":
        return "⚠️", f"已知部分失敗 ({req}) — {cat}"
    if cat == "missing_item_header":
        return "❌", f"預期失敗 ({req}) — {cat}"
    return "⚠️", f"基線 {req} — {cat}"


def sec_result_matches_context(
    *,
    source: str,
    accession: str,
    result_source: str | None,
    result_accession: str | None,
) -> bool:
    """True when cached extraction belongs to the active tab + accession selection."""
    accession = (accession or "").strip()
    if not accession or not result_accession or not result_source:
        return False
    return result_source == source and result_accession.strip() == accession
