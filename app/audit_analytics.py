import streamlit as st
import pandas as pd
import plotly.express as px
import re

st.set_page_config(layout="wide", page_title="Audit Dashboard", page_icon="📋")
st.markdown("## 📋 Audit Completion Dashboard")
st.markdown("Visualize completed vs missed audits and manage performance by submitter or primary assignee.")

def read_file(uploaded_file):
    if uploaded_file.name.endswith(".csv"):
        return pd.read_csv(uploaded_file)
    elif uploaded_file.name.endswith(".xlsx"):
        return pd.read_excel(uploaded_file)
    return None

def map_column(possible_names, df_columns):
    for name in possible_names:
        if name in df_columns:
            return name
    return None

def highlight_completion(val):
    try:
        val = float(val)
        color = (
            'red' if val < 50
            else 'orange' if val < 90
            else 'green'
        )
        return f'background-color: {color}'
    except:
        return ''

def extract_name(raw):
    if pd.isna(raw): return raw
    match = re.match(r"(.+?)\s?\(", raw)
    return match.group(1).strip() if match else raw

# Uploads
st.sidebar.header("📂 Upload Files")
completed_file = st.sidebar.file_uploader("✅ Completed Audits", type=["csv", "xlsx"])
missed_file = st.sidebar.file_uploader("❌ Missed Audits", type=["csv", "xlsx"])
assignee_file = st.sidebar.file_uploader("📌 Upload Target Assignee Sheet (optional)", type=["csv", "xlsx"])

toggle = st.sidebar.checkbox("🔁 Use Primary Assignee Analytics")

if completed_file and missed_file:
    df_completed = read_file(completed_file)
    df_missed = read_file(missed_file)

    df_completed.columns = df_completed.columns.str.strip()
    df_missed.columns = df_missed.columns.str.strip()

    store_col = map_column(["Store Code", "Store", "Entity Id"], df_completed.columns)
    submitter_col = map_column(["Submitted by", "Submitted By", "Auditor", "Responsible"], df_completed.columns)
    region_col = map_column(["Region"], df_completed.columns)
    pc_col = map_column(["Profit Center", "Profit-Center"], df_completed.columns)
    leader_col = map_column(["Leader", "Leader_profit_Center"], df_completed.columns)

    if not store_col:
        st.error("Required column like 'Store Code' is missing.")
    else:
        df_completed["Type"] = "Completed"
        df_missed["Type"] = "Missed"
        df_missed = df_missed[df_missed[store_col].notna()]

        st.markdown("### 🔁 Stores Audited Multiple Times")
        duplicates = df_completed[df_completed.duplicated(subset=[store_col], keep=False)]
        if duplicates.empty:
            st.success("No stores have been audited multiple times.")
        else:
            st.warning(f"{duplicates[store_col].nunique()} stores have duplicate audits.")
            st.dataframe(duplicates[[store_col, submitter_col]].sort_values(by=store_col))

        use_unique = st.checkbox("✅ Use only one audit per store in analytics", value=True)

        df_completed_clean = df_completed.drop_duplicates(subset=[store_col]) if use_unique else df_completed
        df_missed_clean = df_missed.drop_duplicates(subset=[store_col]) if use_unique else df_missed

        missed_store_ids = set(df_missed_clean[store_col]) - set(df_completed_clean[store_col])
        df_missed_clean = df_missed_clean[df_missed_clean[store_col].isin(missed_store_ids)]

        if toggle and assignee_file:
            df_assignees = read_file(assignee_file)
            df_assignees.columns = df_assignees.columns.str.strip()
            df_assignees["Primary Assignee"] = df_assignees["Primary Assignee"].apply(extract_name)
            df_assignees.rename(columns={"StoreName": store_col}, inplace=True)

            assignee_map = df_assignees.set_index(store_col)["Primary Assignee"].to_dict()
            all_stores = list(assignee_map.keys())
            audited_stores = df_completed_clean[store_col].unique().tolist()

            df_primary = pd.DataFrame([
                {
                    store_col: store,
                    "Primary Assignee": assignee_map[store],
                    "Completed": 1 if store in audited_stores else 0
                } for store in all_stores if store in assignee_map
            ])
            summary = df_primary.groupby("Primary Assignee")["Completed"].agg(["sum", "count"]).rename(columns={"sum": "Actual", "count": "Target"})
            summary["Missed"] = summary["Target"] - summary["Actual"]
            summary["Completion %"] = (summary["Actual"] / summary["Target"] * 100).round(0)
            audited = summary["Actual"].sum()
            missed = summary["Missed"].sum()
            total_target = summary["Target"].sum()
            completion_pct = round((audited / total_target) * 100, 2)
            summary = summary.reset_index()
        else:
            combined_df = pd.concat([df_completed_clean, df_missed_clean], ignore_index=True)

            with st.expander("🔍 Filter Options", expanded=False):
                cols = st.columns(5)
                with cols[0]:
                    store_filter = st.selectbox("Store", ["All"] + sorted(combined_df[store_col].dropna().unique().tolist()))
                with cols[1]:
                    submitter_filter = st.selectbox("Submitter", ["All"] + sorted(combined_df.get(submitter_col, pd.Series(dtype=str)).dropna().unique().tolist()))
                with cols[2]:
                    region_filter = st.selectbox("Region", ["All"] + sorted(combined_df.get(region_col, pd.Series(dtype=str)).dropna().unique().tolist()))
                with cols[3]:
                    pc_filter = st.selectbox("Profit Center", ["All"] + sorted(combined_df.get(pc_col, pd.Series(dtype=str)).dropna().unique().tolist()))
                with cols[4]:
                    leader_filter = st.selectbox("Leader", ["All"] + sorted(combined_df.get(leader_col, pd.Series(dtype=str)).dropna().unique().tolist()))

            def apply_filters(df):
                if store_filter != "All":
                    df = df[df[store_col] == store_filter]
                if submitter_filter != "All" and submitter_col:
                    df = df[df[submitter_col] == submitter_filter]
                if region_col and region_filter != "All":
                    df = df[df[region_col] == region_filter]
                if pc_col and pc_filter != "All":
                    df = df[df[pc_col] == pc_filter]
                if leader_col and leader_filter != "All":
                    df = df[df[leader_col] == leader_filter]
                return df

            df_completed_filtered = apply_filters(df_completed_clean)
            df_missed_filtered = apply_filters(df_missed_clean)

            audited = df_completed_filtered[store_col].nunique()
            missed = df_missed_filtered[store_col].nunique()
            total_target = audited + missed
            completion_pct = round((audited / total_target) * 100, 2) if total_target else 0

            # ✅ Updated Summary with Leader column
            if leader_col:
                df_completed_filtered["Leader"] = df_completed_filtered[leader_col]
                df_missed_filtered["Leader"] = df_missed_filtered[leader_col] if leader_col in df_missed_filtered.columns else None

                summary = df_completed_filtered.groupby([submitter_col, "Leader"])[store_col].nunique().rename("Actual").to_frame()
                missed_summary = df_missed_filtered.groupby([submitter_col, "Leader"])[store_col].nunique().rename("Missed")
                summary = summary.join(missed_summary, how='outer').fillna(0)
                summary["Target"] = summary["Actual"] + summary["Missed"]
                summary["Completion %"] = (summary["Actual"] / summary["Target"] * 100).round(0)
                summary = summary.reset_index()
            else:
                summary = df_completed_filtered.groupby(submitter_col)[store_col].nunique().rename("Actual").to_frame()
                missed_summary = df_missed_filtered.groupby(submitter_col)[store_col].nunique().rename("Missed")
                summary = summary.join(missed_summary, how='outer').fillna(0)
                summary["Target"] = summary["Actual"] + summary["Missed"]
                summary["Completion %"] = (summary["Actual"] / summary["Target"] * 100).round(0)
                summary = summary.reset_index()

        # Add total row
        total_row = pd.DataFrame({
            submitter_col: ["Total"],
            "Leader": ["-"] if leader_col else None,
            "Actual": [summary["Actual"].sum()],
            "Missed": [summary["Missed"].sum()],
            "Target": [summary["Target"].sum()],
            "Completion %": [round((summary["Actual"].sum() / summary["Target"].sum() * 100), 0)]
        })
        summary = pd.concat([summary, total_row], ignore_index=True)

        st.markdown("### 📌 Summary Metrics")
        sm = st.columns(5)
        sm[0].metric("🧾 Total Stores", int(total_target))
        sm[1].metric("🎯 Target", int(total_target))
        sm[2].metric("✅ Audited", int(audited))
        sm[3].metric("❌ Missed", int(missed))
        emoji = "🟥" if completion_pct < 50 else "🟧" if completion_pct < 90 else "🟩"
        sm[4].metric(f"{emoji} Completion %", f"{completion_pct:.2f}%")

        st.markdown("### 📊 Target vs Actual")
        fig = px.bar(summary.drop(summary.index[-1]), y=["Target", "Actual"], barmode="group", text_auto=True,
                     title="Target vs Actual Audits", labels={"value": "Stores", "index": "Submitter"})
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("### 📋 Summary Table")
        styled_summary = summary.style.applymap(highlight_completion, subset=["Completion %"]).format(precision=0)
        st.dataframe(styled_summary, use_container_width=True)

        # Download CSV button
        csv = summary.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Summary CSV", csv, "summary_table.csv", "text/csv")

        # Compliance block
        st.markdown("### 🧪 Aggregated Compliance Summary")
        compliance_cols = ["QUALITY", "SERVICE", "CLEANLINESS"]
        if all(col in df_completed_filtered.columns for col in compliance_cols):
            compliance_means = df_completed_filtered[compliance_cols].mean().round(1)
            cc = st.columns(len(compliance_cols))
            for i, col in enumerate(compliance_cols):
                cc[i].metric(f"{col} Compliance %", f"{compliance_means[col]}%")
        else:
            st.info("Compliance columns (QUALITY, SERVICE, CLEANLINESS) not found in uploaded completed audits.")

        # Show final drilldown if not using assignee logic
        if not toggle:
            st.markdown("### 🔍 Drilldown: Missed Stores")
            df_missed_filtered = df_missed_filtered.reset_index(drop=True)
            df_missed_filtered.index += 1
            df_missed_filtered.index.name = "S.No"
            st.dataframe(df_missed_filtered)

