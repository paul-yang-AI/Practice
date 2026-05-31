"""首頁 — 專案概覽、設計文件、架構圖。"""

from __future__ import annotations

import streamlit as st

st.markdown(
    """
<style>
.hero-title { font-size: 2.6rem; font-weight: 900; margin-bottom: 0; letter-spacing: 0.03em; }
.hero-sub { font-size: 1.05rem; color: #555; margin-top: 0.3rem; line-height: 1.8; }
.arch-card {
    border: 1px solid #e0e0e0; border-radius: 14px; padding: 1.3rem;
    text-align: center; background: linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%);
    transition: box-shadow 0.2s; min-height: 160px;
}
.arch-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
.arch-card h3 { margin: 0.5rem 0 0.3rem; font-size: 1.05rem; font-weight: 700; }
.arch-card p { margin: 0; font-size: 0.82rem; color: #555; line-height: 1.6; }
.design-card {
    border-left: 4px solid #4f46e5; background: #f8faff; border-radius: 0 12px 12px 0;
    padding: 1rem 1.2rem; margin-bottom: 1rem;
}
.design-card h4 { margin: 0 0 0.3rem; font-size: 0.95rem; color: #4f46e5; }
.design-card p { margin: 0; font-size: 0.85rem; color: #444; line-height: 1.7; }
.flow-step {
    display: inline-block; background: #eef2ff; border-radius: 8px; padding: 0.5rem 0.9rem;
    margin: 0.2rem; font-size: 0.82rem; font-weight: 600; color: #4338ca;
}
.flow-arrow { display: inline-block; margin: 0 0.15rem; color: #a5b4fc; font-weight: 700; }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown('<p class="hero-title">🐋 Whaleforce AI 程式開發測驗</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="hero-sub">SEC 10-K 混合抽取管線 + LLM 瀏覽器自動化代理<br>'
    "Streamlit · Playwright · Gemini · SQLite</p>",
    unsafe_allow_html=True,
)

st.divider()

# ── Architecture Cards ──────────────────────────────────
st.subheader("系統架構")
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(
        '<div class="arch-card">'
        "<h3>📄 Task 2 — SEC 10-K 管線</h3>"
        "<p>Tier0（BS4/正則）→ 可選 Tier1（fallback / 分類）→ 可選 Tier2（邊界仲裁）<br>"
        "合併引用偵測 · K-xx / Pages 交叉引用 · span 完整性</p>"
        "</div>",
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        '<div class="arch-card">'
        "<h3>🤖 Task 1 — 瀏覽器代理</h3>"
        "<p>Plan → Act → Observe → Verify<br>"
        "Playwright + LLM 規劃 · 失敗時分類式 Recovery<br>"
        "PDF 偵測 · 關鍵字驗證 · 成本熔斷</p>"
        "</div>",
        unsafe_allow_html=True,
    )
with col3:
    st.markdown(
        '<div class="arch-card">'
        "<h3>📊 駕馭層 (Harness)</h3>"
        "<p>Contract-Driven Evaluation（span / token 契約）<br>"
        "LLM Router · Cost Tracker · Job Store<br>"
        "L1 單元 / L2 整合 / L3 端對端</p>"
        "</div>",
        unsafe_allow_html=True,
    )

st.divider()

# ── Core Design Decisions ───────────────────────────────
st.subheader("核心設計決策")

st.markdown(
    '<div class="design-card">'
    "<h4>1. 為什麼不用純 LLM 抽取 SEC 報表？</h4>"
    "<p>Train KPI 刻意走 <b>Tier0-only（$0/filing）</b>，確定性 span 抽取零幻覺。"
    "LLM 為 opt-in 手術刀：<b>Tier2</b> 邊界仲裁（SEC 頁 checkbox）；"
    "<b>Tier1</b> chunk fallback 僅 CLI（<code>--with-llm</code>）。"
    "預設 Eval 路徑不呼叫 LLM。</p>"
    "</div>",
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="design-card">'
    "<h4>2. Contract-Driven Evaluation — 不需人工標注的品質驗證</h4>"
    "<p><b>Span Integrity</b>：body[start:end] == text → 零幻覺。"
    "<b>Token Ratio ≥ 0.85</b> → 零摘要（保證原文）。"
    "<b>Header Retention</b> → 邊界精度。"
    "三個指標結合，可對任意 held-out 10-K 自動驗證；"
    "<code>eval/gold/</code> 為 Tier0 regression baseline（非人工標注）。</p>"
    "</div>",
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="design-card">'
    "<h4>3. 將 LLM 視為不穩定推理引擎</h4>"
    "<p>LLM Router 提供重試、fallback、budget 熔斷。"
    "每次 LLM 呼叫都有 cost tracking（per-token 計費），超預算自動停機。"
    "Agent 架構中，每一步都存入 SQLite，可完全審計。失敗時分類恢復而非盲目重試。</p>"
    "</div>",
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="design-card">'
    "<h4>4. 泛化而非過擬合</h4>"
    "<p>開發用 **3 份 train filing** + **8 份 held-out**（SEC 頁「泛化驗證」）與 "
    "**10 個 agent 任務**（5 train + 5 held-out）做 sanity check。"
    "管線不含任何 filing-specific hardcode（如 CIK 白名單、公司名特判）。"
    "EDGAR API 搜尋 + CIK 自動解析，讓使用者可以自由輸入任意 10-K accession。</p>"
    "</div>",
    unsafe_allow_html=True,
)

st.divider()

# ── SEC Pipeline Flow ───────────────────────────────────
st.subheader("SEC 10-K 抽取流程")
st.markdown(
    '<span class="flow-step">HTML 快取</span>'
    '<span class="flow-arrow">→</span>'
    '<span class="flow-step">Normalize</span>'
    '<span class="flow-arrow">→</span>'
    '<span class="flow-step">Tier0 分段</span>'
    '<span class="flow-arrow">→</span>'
    '<span class="flow-step">合併偵測</span>'
    '<span class="flow-arrow">→</span>'
    '<span class="flow-step">驗證</span>'
    '<span class="flow-arrow">→</span>'
    '<span class="flow-step">可選 Tier2 仲裁</span>'
    '<span class="flow-arrow">→</span>'
    '<span class="flow-step">可選 Tier1 Fallback</span>'
    '<span class="flow-arrow">→</span>'
    '<span class="flow-step">輸出</span>',
    unsafe_allow_html=True,
)
st.caption(
    "預設 Eval / UI 走 Tier0-only（$0）；Tier2 仲裁與 Tier1 fallback 皆 opt-in，"
    "覆蓋率正常時不觸發。"
)

st.divider()

# ── Agent Loop Flow ─────────────────────────────────────
st.subheader("瀏覽器代理迴圈")
st.markdown(
    '<span class="flow-step">Navigate</span>'
    '<span class="flow-arrow">→</span>'
    '<span class="flow-step">Plan (LLM)</span>'
    '<span class="flow-arrow">→</span>'
    '<span class="flow-step">Act (Playwright)</span>'
    '<span class="flow-arrow">→</span>'
    '<span class="flow-step">Observe</span>'
    '<span class="flow-arrow">→</span>'
    '<span class="flow-step">Verify</span>'
    '<span class="flow-arrow">→</span>'
    '<span class="flow-step">Recovery</span>'
    '<span class="flow-arrow">→</span>'
    '<span class="flow-step">Extract</span>',
    unsafe_allow_html=True,
)
st.caption("失敗時觸發分類式恢復（element_not_found → 捲動重試, timeout → 延長等待）")

st.divider()

# ── Tech Stack Table ────────────────────────────────────
with st.expander("技術堆疊"):
    st.markdown("""
| 層級 | 技術 | 用途 |
|------|------|------|
| 前端 | Streamlit | 多頁面即時狀態應用 |
| 瀏覽器 | Playwright | 無頭 Chrome 自動化 |
| LLM | Gemini Flash/Pro | 規劃、驗證、仲裁 |
| 儲存 | SQLite WAL | 任務紀錄、步驟、成本事件 |
| 解析 | BeautifulSoup4 | SEC HTML 正規化 |
| 部署 | Zeabur + Docker | 從 GitHub 自動部署 |
| 測試 | pytest (~173) | 單元 / 整合 / eval |
""")

with st.expander("評估層級說明"):
    st.markdown("""
| 層級 | 名稱 | 驗證範圍 | 需要 LLM？ |
|------|------|----------|-----------|
| L0 | Heuristic Verify | 關鍵字匹配、URL domain 驗證 | 否 |
| L1 | Unit Tests | 單一模組 in / out | 否 |
| L2 | Integration Tests | 端對端管線 + gold 比對 | 否 |
| L3 | Contract Evaluation | span integrity + token ratio + header retention | 否 |
| L4 | Blind Critic (可選) | LLM 審查結果品質 | 是 |
""")

with st.expander("系統架構圖（文字版）"):
    st.code(
        """Streamlit 多頁面應用程式
├─ 頁面 1：SEC 10-K 抽取
├─ 頁面 2：瀏覽器自動化代理
└─ 頁面 3：評估儀表板
        │
        ▼
shared_harness/
├─ llm_router · cost_tracker · job_store · edgar_client
└─ llm_parse · prompt_loader · schemas · eval_runner
        │
        ▼
LLM：Gemini Flash / Pro
預算：$20 全域 · $0.50/代理 · $0.30/filing · 熔斷器""",
        language=None,
    )
