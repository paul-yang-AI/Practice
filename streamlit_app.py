"""Whaleforce Streamlit multi-page app."""

from shared_harness.env import load_env

load_env()

import os

import streamlit as st

st.set_page_config(page_title="Whaleforce", page_icon="🐋", layout="wide")

# Global sidebar
with st.sidebar:
    st.markdown(
        '<p style="font-size:1.6rem; font-weight:800; margin:0;">🐋 Whaleforce</p>'
        '<p style="font-size:0.9rem; color:#666; margin:0;">AI Coding Test</p>',
        unsafe_allow_html=True,
    )
    st.divider()

    st.markdown("**Environment Status**")
    _checks = {
        "GEMINI_API_KEY": bool(os.environ.get("GEMINI_API_KEY")),
        "OPENROUTER_API_KEY": bool(os.environ.get("OPENROUTER_API_KEY")),
        "SEC_USER_AGENT": bool(os.environ.get("SEC_USER_AGENT")),
    }
    for key, ok in _checks.items():
        icon = "✅" if ok else "❌"
        st.markdown(f"{icon} `{key}`")

    fallback_on = os.environ.get("LLM_FALLBACK_ENABLED", "true").lower() in ("1", "true")
    st.markdown(f"{'🔄' if fallback_on else '⏸️'} Fallback: {'ON' if fallback_on else 'OFF'}")

    st.divider()
    st.caption("Built with Streamlit · Playwright · Gemini")

home = st.Page("pages/0_Home.py", title="Home", icon="🏠", default=True)
sec = st.Page("pages/1_SEC_10K.py", title="SEC 10-K", icon="📄")
agent = st.Page("pages/2_Browser_Agent.py", title="Browser Agent", icon="🤖")
eval_page = st.Page("pages/3_Eval.py", title="Eval", icon="📊")

pg = st.navigation([home, sec, agent, eval_page])
pg.run()
