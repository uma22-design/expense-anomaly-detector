import streamlit as st
import pandas as pd
import numpy as np
import os
import sys
import plotly.express as px
import plotly.graph_objects as go

# ── path setup so src/ modules are importable ──────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from data_loader      import load_data, load_sample_data
from preprocessing    import preprocess
from anomaly_detection import detect_anomalies
from explainability   import assign_reasons, assign_risk_level
from utils            import fmt_inr, to_csv_bytes, to_excel_bytes, risk_badge

# ── page config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Expense Anomaly Detector",
    page_icon="🔍",
    layout="wide",
)

# ── session state defaults ─────────────────────────────────────────────────
for key in ("raw_df", "df_result"):
    if key not in st.session_state:
        st.session_state[key] = None

# ══════════════════════════════════════════════════════════════════════════
# HERO SECTION
# ══════════════════════════════════════════════════════════════════════════
st.markdown("""
<h1 style='text-align:center;color:#4F8BF9;'>🔍 Expense Anomaly Detector</h1>
<p style='text-align:center;color:#888;font-size:16px;'>
    AI-powered finance monitoring · flags suspicious transactions instantly
</p>
""", unsafe_allow_html=True)
st.markdown("---")

col_up, col_sample = st.columns([2, 1])
with col_up:
    uploaded = st.file_uploader("Upload your expense CSV or Excel file", type=["csv","xlsx","xls"])
with col_sample:
    st.markdown("<br>", unsafe_allow_html=True)
    use_sample = st.button("📂 Use Sample Dataset", use_container_width=True)

# ── load data ──────────────────────────────────────────────────────────────
if uploaded:
    raw = load_data(uploaded)
    if raw is not None:
        st.session_state.raw_df    = raw
        st.session_state.df_result = None

if use_sample:
    raw = load_sample_data()
    if raw is not None:
        st.session_state.raw_df    = raw
        st.session_state.df_result = None

# ── stop here if no data ──────────────────────────────────────────────────
if st.session_state.raw_df is None:
    st.info("Upload a file or click **Use Sample Dataset** to get started.")
    st.markdown("---")
    st.markdown("<p style='text-align:center;color:#555;'>Built by Uma Bhargavi, CMA · Portfolio 2025</p>",
                unsafe_allow_html=True)
    st.stop()

# ── run pipeline if needed ────────────────────────────────────────────────
if st.session_state.df_result is None:
    with st.spinner("Analysing transactions …"):
        df_clean = preprocess(st.session_state.raw_df.copy())
        df_scored = detect_anomalies(df_clean)
        df_scored = assign_reasons(df_scored)
        df_scored = assign_risk_level(df_scored)
        st.session_state.df_result = df_scored

df = st.session_state.df_result

# ══════════════════════════════════════════════════════════════════════════
# KPI CARDS
# ══════════════════════════════════════════════════════════════════════════
st.markdown("## 📊 Summary")
flagged = df[df["anomaly_flag"] == 1]
total_txn   = len(df)
total_spend = df["amount"].sum()
anom_count  = len(flagged)
anom_rate   = anom_count / total_txn * 100 if total_txn else 0
at_risk     = flagged["amount"].sum()

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Transactions", f"{total_txn:,}")
k2.metric("Total Spend",        fmt_inr(total_spend))
k3.metric("Anomalies Flagged",  f"{anom_count:,}")
k4.metric("Anomaly Rate",       f"{anom_rate:.1f}%")
k5.metric("At-Risk Spend",      fmt_inr(at_risk))

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════
# CHARTS
# ══════════════════════════════════════════════════════════════════════════
st.markdown("## 📈 Spend Analysis")

c1, c2 = st.columns(2)

with c1:
    cat_spend = df.groupby("category")["amount"].sum().reset_index().sort_values("amount", ascending=False)
    fig1 = px.bar(cat_spend, x="category", y="amount",
                  title="Total Spend by Category",
                  labels={"amount":"Amount (₹)","category":"Category"},
                  color="amount", color_continuous_scale="Blues")
    fig1.update_layout(showlegend=False)
    st.plotly_chart(fig1, use_container_width=True)

with c2:
    if not flagged.empty:
        vend_risk = flagged.groupby("vendor")["amount"].sum().reset_index().sort_values("amount", ascending=False).head(10)
        fig2 = px.bar(vend_risk, x="amount", y="vendor", orientation="h",
                      title="Top 10 Vendors by Suspicious Spend",
                      labels={"amount":"Amount (₹)","vendor":"Vendor"},
                      color="amount", color_continuous_scale="Reds")
        fig2.update_layout(showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No anomalies detected.")

c3, c4 = st.columns(2)

with c3:
    if "date" in df.columns:
        df["month"] = pd.to_datetime(df["date"], errors="coerce").dt.to_period("M").astype(str)
        monthly = df.groupby("month")["amount"].sum().reset_index()
        fig3 = px.line(monthly, x="month", y="amount",
                       title="Monthly Spend Trend",
                       labels={"amount":"Amount (₹)","month":"Month"},
                       markers=True)
        st.plotly_chart(fig3, use_container_width=True)

with c4:
    risk_counts = df[df["anomaly_flag"]==1]["risk_level"].value_counts().reset_index()
    risk_counts.columns = ["risk_level","count"]
    if not risk_counts.empty:
        fig4 = px.pie(risk_counts, names="risk_level", values="count",
                      title="Anomalies by Risk Level",
                      color="risk_level",
                      color_discrete_map={"HIGH":"#e74c3c","MEDIUM":"#f39c12","LOW":"#2ecc71"})
        st.plotly_chart(fig4, use_container_width=True)

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════
# FLAGGED TRANSACTIONS TABLE
# ══════════════════════════════════════════════════════════════════════════
st.markdown("## 🚨 Flagged Transactions")

f1, f2 = st.columns(2)
with f1:
    risk_filter = st.multiselect("Filter by Risk Level",
                                 options=["HIGH","MEDIUM","LOW"],
                                 default=["HIGH","MEDIUM","LOW"])
with f2:
    cat_options = sorted(df["category"].dropna().unique().tolist())
    cat_filter  = st.multiselect("Filter by Category", options=cat_options, default=cat_options)

view = flagged[
    flagged["risk_level"].isin(risk_filter) &
    flagged["category"].isin(cat_filter)
].copy()

display_cols = [c for c in
    ["transaction_id","date","vendor","category","amount","anomaly_score","risk_level","reason","action"]
    if c in view.columns]

if not view.empty:
    view["amount"] = view["amount"].apply(fmt_inr)
    st.dataframe(view[display_cols].reset_index(drop=True), use_container_width=True)
else:
    st.success("No flagged transactions match the selected filters.")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════
# EXPORT
# ══════════════════════════════════════════════════════════════════════════
st.markdown("## 📥 Export Report")

e1, e2 = st.columns(2)
with e1:
    st.download_button("⬇️ Download CSV",
                       data=to_csv_bytes(flagged),
                       file_name="anomaly_report.csv",
                       mime="text/csv",
                       use_container_width=True)
with e2:
    st.download_button("⬇️ Download Excel",
                       data=to_excel_bytes(df, flagged),
                       file_name="anomaly_report.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       use_container_width=True)

st.markdown("---")
st.markdown("<p style='text-align:center;color:#555;'>Built by Uma Bhargavi, CMA · Portfolio 2025</p>",
            unsafe_allow_html=True)
