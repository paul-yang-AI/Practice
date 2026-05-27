from pathlib import Path

import pandas as pd
import streamlit as st

st.title("Eval Dashboard")
reports = Path(__file__).resolve().parent.parent / "reports"
csv_files = sorted(reports.glob("eval*.csv"), reverse=True) if reports.exists() else []
if not csv_files and reports.exists():
    csv_files = sorted(reports.glob("latest.csv"), reverse=True)

if csv_files:
    st.caption(f"Showing `{csv_files[0].name}`")
    st.dataframe(pd.read_csv(csv_files[0]))
else:
    st.warning("No eval CSV yet. Run `python scripts/run_eval.py --split train`.")
