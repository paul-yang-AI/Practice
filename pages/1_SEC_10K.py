"""SEC 10-K 結構化抽取 — 信心條、狀態卡片、分部瀏覽。"""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from shared_harness.edgar_client import search_filings
from shared_harness.schemas.sec_schema import ItemStatus, STANDARD_ITEMS
from task2_sec.pipeline.fetch import fetch_filing_html
from task2_sec.pipeline.run import extract_from_html

_MANIFEST = Path(__file__).resolve().parent.parent / "task2_sec" / "eval" / "manifest.json"
_PART_ORDER = ["I", "II", "III", "IV"]

_ITEM_NAMES = {
    "1": "Business",
    "1A": "Risk Factors",
    "1B": "Unresolved Staff Comments",
    "1C": "Cybersecurity",
    "2": "Properties",
    "3": "Legal Proceedings",
    "4": "Mine Safety Disclosures",
    "5": "Market for Registrant's Common Equity",
    "6": "[Reserved]",
    "7": "Management's Discussion and Analysis (MD&A)",
    "7A": "Quantitative and Qualitative Disclosures About Market Risk",
    "8": "Financial Statements and Supplementary Data",
    "9": "Changes in and Disagreements with Accountants",
    "9A": "Controls and Procedures",
    "9B": "Other Information",
    "10": "Directors, Executive Officers and Corporate Governance",
    "11": "Executive Compensation",
    "12": "Security Ownership",
    "13": "Certain Relationships and Related Transactions",
    "14": "Principal Accountant Fees and Services",
    "15": "Exhibits and Financial Statement Schedules",
    "16": "Form 10-K Summary",
}


def _load_manifest() -> list[dict]:
    data = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    return [f for f in data["filings"] if f.get("split", "train") == "train"]


def _status_color(status: ItemStatus) -> str:
    return {
        ItemStatus.EXTRACTED: "#10b981",
        ItemStatus.LOW_CONFIDENCE: "#f59e0b",
        ItemStatus.MISSING: "#ef4444",
        ItemStatus.INCORPORATED_BY_REFERENCE: "#6366f1",
        ItemStatus.NOT_APPLICABLE: "#9ca3af",
    }.get(status, "#6b7280")


def _status_icon(status: ItemStatus) -> str:
    return {
        ItemStatus.EXTRACTED: "✅",
        ItemStatus.LOW_CONFIDENCE: "⚠️",
        ItemStatus.MISSING: "❌",
        ItemStatus.INCORPORATED_BY_REFERENCE: "📎",
        ItemStatus.NOT_APPLICABLE: "➖",
    }.get(status, "❓")


def _render_item(item) -> None:
    icon = _status_icon(item.status)
    color = _status_color(item.status)
    name = _ITEM_NAMES.get(item.item_id, "")
    title = f"Item {item.item_id}" + (f" — {name}" if name else "")

    if item.status == ItemStatus.EXTRACTED and item.text:
        is_page_ref = _is_page_reference_only(item.text)
        suffix = "（交叉引用）" if is_page_ref else ""
        with st.expander(f"{icon} {title}{suffix}", expanded=False):
            col_conf, col_len = st.columns([2, 1])
            with col_conf:
                st.progress(item.confidence, text=f"信心度：{item.confidence:.0%}")
            with col_len:
                word_count = len(item.text.split())
                st.caption(f"📝 {word_count:,} 詞 · {len(item.text):,} 字元")

            if is_page_ref:
                st.info(
                    "📄 此項目為頁碼交叉引用，完整內容位於 PDF 附件中。"
                )

            # Render text as markdown with basic structure
            formatted = _format_sec_text(item.text)
            st.markdown(
                f'<div style="border-left: 4px solid {color}; padding-left: 1rem; '
                f'max-height: 500px; overflow-y: auto; font-size: 0.9rem; '
                f'line-height: 1.6; background: #fafafa; border-radius: 4px; padding: 1rem;">'
                f"{formatted}</div>",
                unsafe_allow_html=True,
            )

            if item.warnings:
                st.caption("⚠️ " + " · ".join(item.warnings))

    elif item.status == ItemStatus.INCORPORATED_BY_REFERENCE:
        with st.expander(f"{icon} {title} — 合併引用", expanded=False):
            st.progress(item.confidence, text=f"信心度：{item.confidence:.0%}")
            st.info("此項目透過合併引用方式，引自公司的委託書（Proxy Statement）。")
            if item.warnings:
                for w in item.warnings:
                    st.caption(f"📋 {w}")

    elif item.status == ItemStatus.MISSING:
        st.markdown(
            f'<div style="padding: 0.5rem 1rem; border-left: 4px solid {color}; '
            f'background: #fef2f2; border-radius: 4px; margin: 0.3rem 0;">'
            f'{icon} <strong>{title}</strong> — 報表中未找到</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div style="padding: 0.5rem 1rem; border-left: 4px solid {color}; '
            f'background: #f9fafb; border-radius: 4px; margin: 0.3rem 0;">'
            f'{icon} <strong>{title}</strong> — {item.status.value}</div>',
            unsafe_allow_html=True,
        )


def _is_page_reference_only(text: str) -> bool:
    """Detect if extracted text is just a TOC page reference (e.g. 'Pages 3-4, 13')."""
    import re
    clean = text.strip()
    if len(clean) < 200:
        # Short text that's mostly page numbers
        page_refs = re.findall(r"(?:Pages?|pp?\.?)\s*[\d\-–,\s]+", clean, re.IGNORECASE)
        non_ref = re.sub(r"(?:Pages?|pp?\.?)\s*[\d\-–,\s]+", "", clean, flags=re.IGNORECASE)
        non_ref = re.sub(r"Item\s+\d+[A-Z]?\.?", "", non_ref).strip()
        non_ref = re.sub(r"[:\n\r\s]+", "", non_ref)
        if page_refs and len(non_ref) < 80:
            return True
    return False


def _format_sec_text(text: str) -> str:
    """Convert raw SEC text into basic HTML with paragraph breaks and headers."""
    import html as html_mod

    lines = text.strip().split("\n")
    parts: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            parts.append("<br>")
            continue
        escaped = html_mod.escape(stripped)
        if stripped.isupper() and len(stripped) > 3 and len(stripped) < 120:
            parts.append(f"<strong style='color:#1e40af;'>{escaped}</strong><br>")
        elif stripped.endswith(":") and len(stripped) < 80:
            parts.append(f"<strong>{escaped}</strong><br>")
        else:
            parts.append(f"{escaped}<br>")

    return "\n".join(parts)


# --- Page Layout ---

st.markdown(
    '<h1 style="margin-bottom:0;">📄 SEC 10-K 結構化抽取</h1>',
    unsafe_allow_html=True,
)
st.caption(
    "混合管線：Tier0（BS4 + 正則分段）→ 跨度完整性驗證 → "
    "LLM 仲裁（低信心段落自動調整邊界）"
)

tab_manifest, tab_custom = st.tabs(["📋 已註冊報表", "🔗 自訂報表"])

_run_source: str | None = None

with tab_manifest:
    filings = _load_manifest()
    labels = [f"{f['ticker']} — {f['accession']} ({f.get('label', '')})" for f in filings]
    choice = st.selectbox("選擇報表", labels, index=0)
    selected = filings[labels.index(choice)]
    if st.button("🚀 開始抽取", type="primary", use_container_width=True, key="run_manifest"):
        _run_source = "manifest"

with tab_custom:
    st.markdown("搜尋公司名稱或股票代碼，快速找到 10-K 報表。")

    col_search, col_btn = st.columns([3, 1])
    with col_search:
        search_query = st.text_input(
            "🔍 搜尋公司",
            placeholder="例：Microsoft、AAPL、Tesla",
            label_visibility="collapsed",
        )
    with col_btn:
        do_search = st.button("搜尋", use_container_width=True)

    if do_search and search_query.strip():
        with st.spinner("搜尋 EDGAR…"):
            hits = search_filings(search_query.strip())
        if hits:
            st.session_state["edgar_search_results"] = hits
        else:
            st.warning("未找到結果，請嘗試其他關鍵字。")

    search_results = st.session_state.get("edgar_search_results", [])
    if search_results:
        search_labels = [
            f"{r['company']} ({r['ticker']}) — {r['accession']} [{r['filed']}]"
            for r in search_results
        ]
        search_choice = st.selectbox("選擇報表", search_labels, key="search_select")
        chosen = search_results[search_labels.index(search_choice)]
        if st.button("📄 使用此報表", use_container_width=True, key="use_search_result"):
            st.session_state["custom_acc_fill"] = chosen["accession"]
            st.session_state["custom_cik_fill"] = chosen["cik"]
            st.session_state["custom_ticker_fill"] = chosen.get("ticker", "")

    st.divider()
    st.markdown("或直接輸入 Accession Number：")

    custom_accession = st.text_input(
        "Accession Number",
        value=st.session_state.get("custom_acc_fill", ""),
        placeholder="例：0000950170-24-087843",
        help="格式：XXXXXXXXXX-YY-ZZZZZZ（含連字號）",
    )
    col_cik, col_ticker = st.columns(2)
    with col_cik:
        custom_cik = st.text_input(
            "CIK（選填，建議填寫）",
            value=st.session_state.get("custom_cik_fill", ""),
            placeholder="例：789019（微軟）",
            help="公司的 CIK 編號。若不填，系統會自動從 EDGAR 查詢。",
        )
    with col_ticker:
        custom_ticker = st.text_input(
            "股票代碼（選填）",
            value=st.session_state.get("custom_ticker_fill", ""),
            placeholder="MSFT",
        )
    custom_url = st.text_input(
        "報表 URL（選填，留空自動解析）",
        placeholder="https://www.sec.gov/Archives/edgar/data/.../filing.htm",
    )
    if st.button("🚀 開始抽取", type="primary", use_container_width=True, key="run_custom"):
        if not custom_accession.strip():
            st.error("請輸入 Accession Number。")
        else:
            _run_source = "custom"

use_arbiter = True

if _run_source == "manifest":
    accession = selected["accession"]
    filing_url = selected.get("url")
    ticker = selected.get("ticker")
    cik = selected.get("cik")
elif _run_source == "custom":
    accession = custom_accession.strip()
    filing_url = custom_url.strip() or None
    ticker = custom_ticker.strip() or None
    cik = custom_cik.strip() or None

if _run_source:
    with st.spinner(f"正在抽取 {accession}…"):
        try:
            html = fetch_filing_html(
                accession,
                url=filing_url,
                cik=cik,
                force_refresh=False,
            )
            st.session_state["sec_result"] = None
            result = extract_from_html(
                html,
                accession=accession,
                cik=cik,
                ticker=ticker,
                use_arbiter=use_arbiter,
                run_id=None,
            )
            st.session_state["sec_result"] = result
            st.session_state["sec_html_len"] = len(html)
        except Exception as exc:
            err_msg = str(exc)
            st.error(f"❌ 抽取失敗：{err_msg}")
            if "CIK" in err_msg or "404" in err_msg or "index" in err_msg.lower():
                st.info(
                    "💡 **常見原因**：\n"
                    "1. Accession number 格式不正確（需含連字號，如 `0000950170-24-087843`）\n"
                    "2. 該報表的 CIK 無法自動解析 — 請在上方填入公司的 CIK\n"
                    "3. 直接貼上完整的 EDGAR 報表 URL 可以跳過 CIK 解析"
                )

result = st.session_state.get("sec_result")
if result:
    st.divider()

    # Filing metadata card
    html_len = st.session_state.get("sec_html_len", 0)
    st.markdown(
        f'<div style="background: linear-gradient(135deg, #eff6ff 0%, #f0fdf4 100%); '
        f'border-radius: 12px; padding: 1.2rem; margin-bottom: 1rem;">'
        f'<strong style="font-size: 1.3rem;">{result.ticker or "N/A"}</strong> &nbsp;'
        f'<span style="color:#666;">CIK: {result.cik or "N/A"} &nbsp;|&nbsp; '
        f'Accession: {result.accession}</span><br>'
        f'<span style="font-size: 0.85rem; color: #888;">'
        f'Source: {html_len:,} chars HTML</span></div>',
        unsafe_allow_html=True,
    )

    # Summary metrics
    extracted = sum(1 for i in result.items if i.status == ItemStatus.EXTRACTED)
    incorporated = sum(1 for i in result.items if i.status == ItemStatus.INCORPORATED_BY_REFERENCE)
    missing = sum(1 for i in result.items if i.status == ItemStatus.MISSING)
    low_conf = sum(1 for i in result.items if i.status == ItemStatus.LOW_CONFIDENCE)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("✅ 已抽取", extracted)
    c2.metric("📎 合併引用", incorporated)
    c3.metric("⚠️ 低信心", low_conf)
    c4.metric("❌ 缺失", missing)
    c5.metric("📊 總計", len(result.items))

    total = len(result.items) or 1
    st.progress(
        (extracted + incorporated) / total,
        text=f"涵蓋率：{extracted + incorporated}/{total} 項已解析 "
        f"({(extracted + incorporated) / total:.0%})",
    )

    st.divider()

    # Items grouped by Part
    by_part: dict[str, list] = {p: [] for p in _PART_ORDER}
    by_part["Other"] = []
    for item in result.items:
        part = item.part or "Other"
        by_part.setdefault(part, []).append(item)

    for part in _PART_ORDER + (["Other"] if by_part.get("Other") else []):
        items = by_part.get(part) or []
        if not items:
            continue
        st.markdown(f"### Part {part}")
        for item in items:
            _render_item(item)

    st.divider()
    col_dl1, col_dl2 = st.columns(2)
    with col_dl1:
        st.download_button(
            "📥 下載 JSON",
            data=result.model_dump_json(indent=2),
            file_name=f"{result.accession or 'filing'}.json",
            mime="application/json",
            use_container_width=True,
        )
    with col_dl2:
        md_lines = [f"# {result.ticker} 10-K 抽取報告\n\n"]
        md_lines.append(f"Accession: {result.accession}\n\n")
        for item in result.items:
            name = _ITEM_NAMES.get(item.item_id, "")
            md_lines.append(f"## Item {item.item_id} — {name}\n\n")
            md_lines.append(f"狀態：{item.status.value} | 信心度：{item.confidence:.0%}\n\n")
            if item.text:
                md_lines.append(item.text[:3000] + "\n\n---\n\n")
        st.download_button(
            "📥 下載 Markdown",
            data="".join(md_lines),
            file_name=f"{result.accession or 'filing'}.md",
            mime="text/markdown",
            use_container_width=True,
        )
