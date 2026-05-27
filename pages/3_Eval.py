from pathlib import Path

import streamlit as st

st.title("Eval Dashboard")
reports = Path(__file__).resolve().parent.parent / "reports"
csv_files = sorted(reports.glob("eval*.csv"), reverse=True) if reports.exists() else []
if csv_files:
    st.dataframe(csv_files[0].read_text(encoding="utf-8"))
else:
    st.warning("No eval CSV yet. Run `python scripts/run_eval.py --split train` after Phase 1.")
