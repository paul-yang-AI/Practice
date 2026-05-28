"""評估儀表板 — 即時執行 SEC 評估、顯示 KPI 與詳細結果。"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

_REPORTS = Path(__file__).resolve().parent.parent / "reports"


st.markdown(
    '<h1 style="margin-bottom:0;">📊 評估儀表板</h1>',
    unsafe_allow_html=True,
)
st.caption("SEC 10-K 管線與瀏覽器代理的自動化評估結果 — 點擊下方按鈕即時執行")

col_run_sec, col_run_agent = st.columns(2)
with col_run_sec:
    run_sec = st.button("📄 執行 SEC 10-K 評估", type="primary", use_container_width=True)
with col_run_agent:
    run_agent = st.button(
        "🤖 執行瀏覽器代理評估",
        type="secondary",
        use_container_width=True,
        help="需要 Playwright 與 LLM API Key，執行時間較長",
    )

if run_sec:
    with st.spinner("正在執行 SEC 10-K 管線評估…"):
        try:
            from shared_harness.eval_runner import run_sec_eval, summarize_eval, write_eval_csv

            sec_results = run_sec_eval(split="train", use_arbiter=True)
            summary = summarize_eval(sec_results)
            csv_path = _REPORTS / "eval_train.csv"
            write_eval_csv(sec_results, csv_path)
            write_eval_csv(sec_results, _REPORTS / "latest.csv")
            (_REPORTS / "eval_summary.json").write_text(
                json.dumps(summary, indent=2), encoding="utf-8"
            )
            st.session_state["eval_summary"] = summary
            st.session_state["eval_csv"] = str(csv_path)
            st.success("✅ SEC 評估完成！")
        except Exception as exc:
            st.error(f"❌ 評估失敗：{exc}")

if run_agent:
    with st.spinner("正在執行瀏覽器代理評估（可能需要數分鐘）…"):
        try:
            from shared_harness.eval_runner import (
                run_agent_eval,
                run_sec_eval,
                summarize_eval,
                write_eval_csv,
            )

            sec_results = run_sec_eval(split="train", use_arbiter=True)
            agent_results = run_agent_eval(split="train")
            all_results = [*sec_results, *agent_results]
            summary = summarize_eval(all_results)
            csv_path = _REPORTS / "eval_train.csv"
            write_eval_csv(all_results, csv_path)
            write_eval_csv(all_results, _REPORTS / "latest.csv")
            (_REPORTS / "eval_summary.json").write_text(
                json.dumps(summary, indent=2), encoding="utf-8"
            )
            st.session_state["eval_summary"] = summary
            st.session_state["eval_csv"] = str(csv_path)
            st.success("✅ 完整評估完成！")
        except Exception as exc:
            st.error(f"❌ 評估失敗：{exc}")

st.divider()

summary = st.session_state.get("eval_summary")
csv_file = st.session_state.get("eval_csv")

if summary:
    st.markdown("### 關鍵指標")
    k1, k2, k3, k4 = st.columns(4)

    sec_ok = summary.get("sec_ok", 0)
    sec_total = summary.get("sec_filings", summary.get("sec_total", 0))
    agent_total = summary.get("agent_tasks", summary.get("agent_total", 0))
    agent_rate = summary.get("agent_success_rate", 0)
    agent_ok = int(agent_rate * agent_total) if agent_rate <= 1 else int(agent_rate)

    k1.metric(
        "SEC 10-K",
        f"{sec_ok}/{sec_total}",
        delta="全部通過" if sec_ok == sec_total else f"{sec_total - sec_ok} 項失敗",
        delta_color="normal" if sec_ok == sec_total else "inverse",
    )
    if agent_total:
        k2.metric(
            "瀏覽器代理",
            f"{agent_ok}/{agent_total}",
            delta=f"{agent_ok/max(agent_total,1):.0%} 成功",
        )
        k3.metric(
            "P50 延遲",
            f"{summary.get('agent_latency_p50', 'N/A')}s",
            help="中位數任務完成時間",
        )
        k4.metric(
            "P50 成本",
            f"${summary.get('agent_usd_p50', 0):.4f}",
            help="中位數每任務 LLM 成本",
        )
    else:
        k2.metric("瀏覽器代理", "尚未執行", delta="點擊上方按鈕")

    total_tasks = sec_total + agent_total
    total_pass = sec_ok + agent_ok
    if total_tasks > 0:
        col_bar, col_pct = st.columns([4, 1])
        with col_bar:
            st.progress(min(max(total_pass / max(total_tasks, 1), 0.0), 1.0))
        with col_pct:
            st.markdown(f"**{total_pass}/{total_tasks}** 通過")

    st.divider()

    st.markdown("### 任務細項")
    col_sec, col_agent = st.columns(2)

    with col_sec:
        st.markdown("#### 📄 SEC 10-K 管線")
        if sec_ok == sec_total and sec_total > 0:
            st.success(f"全部 {sec_total} 份報表成功抽取")
        elif sec_total > 0:
            st.warning(f"{sec_ok}/{sec_total} 份報表通過")

    with col_agent:
        st.markdown("#### 🤖 瀏覽器代理")
        if agent_total == 0:
            st.info("尚未執行代理評估")
        elif agent_ok == agent_total:
            st.success(f"全部 {agent_total} 項任務完成")
        else:
            st.info(
                f"{agent_ok}/{agent_total} 項任務成功。"
                f"靜默失敗：{summary.get('agent_silent_failures', 0)}"
            )

if csv_file:
    st.divider()
    df = pd.read_csv(csv_file)
    st.markdown("### 詳細結果")
    st.caption(f"資料來源：即時評估 — {len(df)} 筆")

    task_filter = st.radio(
        "依任務類型篩選",
        ["全部", "SEC 10-K", "瀏覽器代理"],
        horizontal=True,
    )
    if task_filter == "SEC 10-K":
        df = df[df["task"] == "sec_10k"]
    elif task_filter == "瀏覽器代理":
        df = df[df["task"] == "agent"]

    def _highlight_status(row):
        if row.get("status") == "success" or row.get("status") == "ok":
            return ["background-color: #dcfce7"] * len(row)
        elif row.get("status") == "failed":
            return ["background-color: #fee2e2"] * len(row)
        return [""] * len(row)

    st.dataframe(
        df.style.apply(_highlight_status, axis=1),
        use_container_width=True,
        height=min(400, 35 * len(df) + 38),
    )

    if "extracted_result" in df.columns:
        agent_rows = df[df["task"] == "agent"]
        if not agent_rows.empty:
            st.markdown("### 🤖 代理抽取結果")
            for _, row in agent_rows.iterrows():
                result_text = str(row.get("extracted_result", ""))
                status = row.get("status", "")
                record = row.get("record_id", "")
                icon = "✅" if status == "success" else "❌"

                with st.expander(f"{icon} {record} — {status}", expanded=(status == "success")):
                    if result_text and result_text != "nan":
                        st.code(result_text, language=None)
                    else:
                        st.caption("未抽取到結果")
                    elapsed = row.get("elapsed_s", row.get("latency_s"))
                    if pd.notna(elapsed):
                        usd = row.get("usd_per_run", row.get("cost_usd", 0)) or 0
                        st.caption(f"⏱️ {float(elapsed):.1f}s | 💰 ${float(usd):.4f}")

if not summary and not csv_file:
    st.info("👆 點擊上方按鈕即時執行評估，結果將即時顯示於此。")

if summary:
    with st.expander("📋 原始摘要 JSON"):
        st.json(summary)
