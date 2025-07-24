
import streamlit as st
import pandas as pd
import os

st.set_page_config(layout="wide")
st.title("Herfy - Audit Dashboard")

# File uploader for Completed Audits
uploaded_completed_file = st.file_uploader("Upload Completed Audits File", type=["csv", "xlsx"])

if uploaded_completed_file:
    if uploaded_completed_file.name.endswith(".csv"):
        completed_audits_df = pd.read_csv(uploaded_completed_file)
    else:
        completed_audits_df = pd.read_excel(uploaded_completed_file)

    st.subheader("Completed Audit Data")
    st.dataframe(completed_audits_df, use_container_width=True)

    st.markdown("---")
    st.header("📊 Analysis by Store")

    store_group = completed_audits_df.groupby("Store Name")["Completion %"].mean().reset_index()
    store_group.columns = ["Store Name", "Average Completion %"]
    st.dataframe(store_group, use_container_width=True)

    st.markdown("---")
    st.header("🕵️‍♂️ Analysis by Auditor")

    auditor_group = completed_audits_df.groupby("Auditor Name")["Completion %"].mean().reset_index()
    auditor_group.columns = ["Auditor Name", "Average Completion %"]
    st.dataframe(auditor_group, use_container_width=True)

# =================== FINAL SUMMARY BLOCK =====================

st.markdown("---")
st.header("🔎 Summary Metrics (Aggregated)")

if uploaded_completed_file:
    if "Completion %" in completed_audits_df.columns:
        avg_completion = completed_audits_df["Completion %"].mean()
        st.metric("Average Completion %", f"{avg_completion:.2f}%")

    for col in ["QUALITY", "SERVICE", "CLEANLINESS"]:
        if col in completed_audits_df.columns:
            compliance = completed_audits_df[col].mean()
            st.metric(f"{col.capitalize()} Compliance", f"{compliance:.2f}%")
else:
    st.info("No completed audit data available for summary.")
