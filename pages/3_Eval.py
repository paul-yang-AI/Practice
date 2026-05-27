from pathlib import Path

import pandas as pd
import streamlit as st

st.title("Eval Dashboard")
reports = Path(__file__).resolve().parent.parent / "reports"
csv_files = sorted(reports.glob("eval*.csv"), reverse=True) if reports.exists() else []
if not csv_files and reports.exists():
    csv_files = sorted(reports.glob("latest.csv"), reverse=True)

summary_path = reports / "eval_summary.json"
if summary_path.exists():
    st.subheader("Summary")
    st.json(summary_path.read_text(encoding="utf-8"))

if csv_files:
    df = pd.read_csv(csv_files[0])
    st.caption(f"Showing `{csv_files[0].name}` — {len(df)} rows")

    task_filter = st.radio("Filter", ["All", "SEC 10-K", "Browser Agent"], horizontal=True)
    if task_filter == "SEC 10-K":
        df = df[df["task"] == "sec_10k"]
    elif task_filter == "Browser Agent":
        df = df[df["task"] == "agent"]

    st.dataframe(df, use_container_width=True)

    if "extracted_result" in df.columns:
        agent_rows = df[df["task"] == "agent"]
        if not agent_rows.empty:
            with st.expander("Agent extracted results"):
                for _, row in agent_rows.iterrows():
                    if pd.notna(row.get("extracted_result")) and str(row["extracted_result"]).strip():
                        st.markdown(f"**{row['record_id']}** ({row['status']})")
                        st.code(str(row["extracted_result"]))
else:
    st.warning(
        "No eval CSV yet. Run:\n"
        "`python scripts/run_eval.py --split train`\n"
        "`python scripts/run_agent_eval.py`"
    )
