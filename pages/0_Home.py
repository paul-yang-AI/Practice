"""Home page — project overview with architecture and live health metrics."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

_REPORTS = Path(__file__).resolve().parent.parent / "reports"


def _load_summary() -> dict | None:
    p = _REPORTS / "eval_summary.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return None


st.markdown(
    """
<style>
.hero-title { font-size: 2.8rem; font-weight: 800; margin-bottom: 0; }
.hero-sub { font-size: 1.1rem; color: #666; margin-top: 0.2rem; }
.arch-card {
    border: 1px solid #e0e0e0; border-radius: 12px; padding: 1.2rem;
    text-align: center; background: linear-gradient(135deg, #f8fafc 0%, #eef2ff 100%);
}
.arch-card h3 { margin: 0.5rem 0 0.3rem; font-size: 1.1rem; }
.arch-card p { margin: 0; font-size: 0.85rem; color: #555; }
.metric-row { display: flex; gap: 1rem; margin: 1rem 0; }
</style>
""",
    unsafe_allow_html=True,
)

st.markdown('<p class="hero-title">🐋 Whaleforce AI Coding Test</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="hero-sub">SEC 10-K Hybrid Extraction + LLM Browser Agent &nbsp;|&nbsp; '
    "Streamlit · Playwright · Gemini · SQLite</p>",
    unsafe_allow_html=True,
)

st.divider()

# Architecture cards
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown(
        '<div class="arch-card">'
        "<h3>📄 SEC 10-K Pipeline</h3>"
        "<p>Hybrid Tier0 (BS4/regex) + LLM arbiter<br>"
        "22 items × 3 filings, incorporated detection</p>"
        "</div>",
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        '<div class="arch-card">'
        "<h3>🤖 Browser Agent</h3>"
        "<p>Plan→Act→Observe→Verify→Reflect<br>"
        "Playwright + LLM planning + classified recovery</p>"
        "</div>",
        unsafe_allow_html=True,
    )
with col3:
    st.markdown(
        '<div class="arch-card">'
        "<h3>📊 Eval Harness</h3>"
        "<p>L1 Unit / L2 Integration / L3 Eval<br>"
        "CSV reports · cost tracking · circuit breaker</p>"
        "</div>",
        unsafe_allow_html=True,
    )

st.divider()

# Live health metrics
summary = _load_summary()
if summary:
    st.subheader("Evaluation Health")
    m1, m2, m3, m4 = st.columns(4)

    sec_pass = summary.get("sec_ok", 0)
    sec_total = summary.get("sec_total", 0)
    agent_pass = summary.get("agent_success", 0)
    agent_total = summary.get("agent_total", 0)

    m1.metric("SEC 10-K", f"{sec_pass}/{sec_total}", delta="pass" if sec_pass == sec_total else None)
    m2.metric("Browser Agent", f"{agent_pass}/{agent_total}")
    m3.metric("P50 Latency", f"{summary.get('agent_p50_latency_s', 'N/A')}s")
    m4.metric("P50 Cost", f"${summary.get('agent_p50_cost_usd', 0):.4f}")

    st.progress(
        (sec_pass + agent_pass) / max(sec_total + agent_total, 1),
        text=f"Overall: {sec_pass + agent_pass}/{sec_total + agent_total} tasks pass",
    )
else:
    st.info("No eval summary yet. Run `python scripts/run_eval.py` and `python scripts/run_agent_eval.py`.")

st.divider()

# Architecture diagram
with st.expander("Architecture Overview", expanded=True):
    st.markdown("""
```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Multi-Page App                   │
├──────────────┬──────────────────┬───────────────────────────┤
│  SEC 10-K    │  Browser Agent   │  Eval Dashboard           │
│  (Page 1)    │  (Page 2)        │  (Page 3)                 │
├──────────────┴──────────────────┴───────────────────────────┤
│                     shared_harness/                           │
│  llm_router · cost_tracker · job_store · edgar_client        │
│  llm_parse · prompt_loader · schemas                         │
├─────────────────────────────────────────────────────────────┤
│  LLM Layer: Gemini (primary) → OpenRouter (fallback)         │
│  Budget: $20 global · $0.50/agent run · Circuit breaker      │
└─────────────────────────────────────────────────────────────┘
```
""")

with st.expander("Tech Stack"):
    st.markdown("""
| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Streamlit | Multi-page app with real-time status |
| Browser | Playwright | Headless Chrome automation |
| LLM | Gemini Flash/Pro | Planning, verification, arbiter |
| Fallback | OpenRouter | DeepSeek/Qwen when Gemini unavailable |
| Storage | SQLite WAL | Job runs, steps, cost events |
| Parsing | BeautifulSoup4 | SEC HTML normalization |
| Deploy | Zeabur + Docker | Auto-deploy from GitHub |
| Tests | pytest (65+) | Unit / Integration / Eval layers |
""")

with st.expander("Design Decisions (Interview Talking Points)"):
    st.markdown("""
**Why Hybrid Tier0 + LLM instead of pure LLM?**
- Cost: Tier0 (BS4/regex) handles 90%+ of items at $0 cost
- Reliability: Deterministic extraction doesn't hallucinate section boundaries
- LLM arbiter only activates for disputed boundaries (< 5% of cases)

**Why Plan-Act-Observe-Verify-Reflect loop?**
- Structured agent architecture prevents infinite loops
- Classified recovery (element_not_found → retry_after_scroll, timeout → extend_wait)
- Each step is auditable — full SQLite trace for debugging

**Why Gemini + OpenRouter fallback?**
- Gemini Flash: fastest, cheapest for Tier1 planning (~0.5ms/token)
- OpenRouter: model diversity without vendor lock-in
- Budget circuit breaker prevents runaway costs

**Why Streamlit over React?**
- Rapid iteration for a coding test (2-day timeline)
- Built-in widgets for file upload, progress, metrics
- Easy deployment (single Docker container)
""")
