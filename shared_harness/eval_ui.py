"""Pure helpers for Eval dashboard UI (unit-testable without Streamlit)."""

from __future__ import annotations

import html as html_module


def benchmark_kpi_items(summary: dict) -> list[tuple[str, str, str]]:
    """Return (label, value, hint) for the train benchmark KPI row."""
    sec_ok = int(summary.get("sec_ok", 0))
    sec_total = int(summary.get("sec_filings", 0))
    agent_total = int(summary.get("agent_tasks", 0))
    agent_rate = float(summary.get("agent_success_rate", 0))
    agent_ok = int(agent_rate * agent_total) if agent_rate <= 1 else int(agent_rate)

    items: list[tuple[str, str, str]] = [
        ("SEC 10-K", f"{sec_ok}/{sec_total}", ""),
    ]
    if agent_total:
        items.extend(
            [
                ("Agent Train", f"{agent_ok}/{agent_total}", ""),
                ("P50 延遲", f"{float(summary.get('agent_latency_p50', 0)):.1f}s", ""),
                ("P50 成本", f"${float(summary.get('agent_usd_p50', 0)):.4f}", ""),
            ]
        )
    else:
        items.extend(
            [
                ("Agent Train", "—", "執行完整基準以包含 Agent"),
                ("Silent failures", str(summary.get("agent_silent_failures", 0)), ""),
                ("Recovery steps", str(summary.get("agent_recovery_total", 0)), ""),
            ]
        )
    return items


def kpi_card_html(label: str, value: str, *, hint: str = "") -> str:
    label_e = html_module.escape(label)
    value_e = html_module.escape(value)
    hint_e = html_module.escape(hint) if hint else ""
    hint_html = (
        f'<div style="font-size:0.72rem;color:#6b7280;margin-top:0.2rem;">{hint_e}</div>'
        if hint
        else ""
    )
    return (
        f'<div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;'
        f'padding:0.85rem 1rem;min-height:4.25rem;">'
        f'<div style="font-size:0.78rem;color:#6b7280;font-weight:600;">{label_e}</div>'
        f'<div style="font-size:1.35rem;font-weight:700;color:#111827;line-height:1.25;">'
        f"{value_e}</div>{hint_html}</div>"
    )


def kpi_row_html(summary: dict) -> str:
    cards = [kpi_card_html(l, v, hint=h) for l, v, h in benchmark_kpi_items(summary)]
    return (
        '<div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));'
        f'gap:0.75rem;margin:0.5rem 0 0.75rem;">{"".join(cards)}</div>'
    )
