"""
app.py — Expense Anomaly Detector
CMA Portfolio Project | Uma Bhargavi
"""

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from data_loader import load_data, load_sample_data
from preprocessing import preprocess
from anomaly_detection import detect_anomalies
from explainability import assign_reasons, assign_risk_level
from utils import (
    fmt_inr, fmt_pct, to_csv_bytes, to_excel_bytes,
    RISK_BADGE_HTML, score_bar_html, RISK_COLORS
)

# ─────────────────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Expense Anomaly Detector",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────
# Custom CSS
# ─────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

/* KPI Cards */
.kpi-card {
    background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
    border: 1px solid rgba(99,102,241,0.3);
    border-radius: 14px;
    padding: 20px 24px;
    text-align: center;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
}
.kpi-label { color: #94A3B8; font-size: 12px; font-weight: 500; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 6px; }
.kpi-value { color: #F1F5F9; font-size: 28px; font-weight: 700; font-family: 'DM Mono', monospace; }
.kpi-sub   { color: #64748B; font-size: 12px; margin-top: 4px; }

/* Section headers */
.section-title {
    font-size: 18px; font-weight: 700; color: #1E293B;
    border-left: 4px solid #6366F1; padding-left: 12px;
    margin: 24px 0 16px 0;
}

/* Anomaly table */
.anom-table td { vertical-align: middle !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔍 Expense Anomaly Detector")
    st.markdown("*Finance monitoring tool for auditors and FP&A teams.*")
    st.divider()

    st.markdown("### 1 · Load Data")
    use_sample = st.button("📦 Use Sample Dataset", use_container_width=True)
    uploaded = st.file_uploader("Or upload your own CSV / Excel", type=["csv", "xlsx", "xls"])

    st.divider()
    st.markdown("### 2 · Detection Settings")
    contamination = st.slider(
        "Expected anomaly rate (%)",
        min_value=2, max_value=25, value=10, step=1,
        help="Approximate % of transactions expected to be anomalous. Adjusts Isolation Forest sensitivity."
    ) / 100

    st.divider()
    st.markdown("### 3 · Filters")
    category_filter = st.multiselect("Filter by Category", options=[], key="cat_filter")
    dept_filter = st.multiselect("Filter by Department", options=[], key="dept_filter")

    st.divider()
    st.caption("Built by Uma Bhargavi · CMA Portfolio 2025")


# ─────────────────────────────────────────────────────────
# State & data loading
# ─────────────────────────────────────────────────────────
if "df_result" not in st.session_state:
    st.session_state.df_result = None

if use_sample:
    raw = load_sample_data()
    if raw is not None:
        st.session_state.raw_df = raw
        st.session_state.df_result = None  # force reprocess

if uploaded:
    raw = load_data(uploaded)
    if raw is not None:
        st.session_state.raw_df = raw
        st.session_state.df_result = None

if "raw_df" in st.session_state and st.session_state.df_result is None:
    with st.spinner("Processing transactions…"):
        clean = preprocess(st.session_state.raw_df)
        df_flagged, model, scaler = detect_anomalies(clean, contamination)
        df_flagged = assign_reasons(df_flagged)
        df_flagged = assign_risk_level(df_flagged)
        st.session_state.df_result = df_flagged

        # Update sidebar filters
        cats = sorted(df_flagged["category"].unique().tolist())
        depts = sorted(df_flagged["department"].unique().tolist())
        st.session_state.all_cats = cats
        st.session_state.all_depts = depts


# ─────────────────────────────────────────────────────────
# Screen 1 — Hero / Home
# ─────────────────────────────────────────────────────────
if st.session_state.df_result is None:
    st.markdown("""
    <div style='text-align:center;padding:60px 0 20px 0'>
        <div style='font-size:56px;margin-bottom:8px'>🔍</div>
        <h1 style='font-size:36px;font-weight:800;color:#1E293B;margin:0'>
            Expense Anomaly Detector
        </h1>
        <p style='font-size:16px;color:#64748B;margin-top:10px;max-width:560px;margin-left:auto;margin-right:auto'>
            AI-powered transaction monitoring for finance teams. Flags high-risk expenses
            using rule-based checks and Isolation Forest, with plain-English explanations
            for every anomaly.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        <div class='kpi-card'>
            <div class='kpi-label'>Detection Method</div>
            <div class='kpi-value' style='font-size:18px'>Hybrid AI + Rules</div>
        </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class='kpi-card'>
            <div class='kpi-label'>Explanation</div>
            <div class='kpi-value' style='font-size:18px'>Plain-English Reasons</div>
        </div>""", unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class='kpi-card'>
            <div class='kpi-label'>Export</div>
            <div class='kpi-value' style='font-size:18px'>CSV + Excel Report</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.info("👈 Click **Use Sample Dataset** in the sidebar to get started instantly, or upload your own file.")
    st.stop()


# ─────────────────────────────────────────────────────────
# Apply filters
# ─────────────────────────────────────────────────────────
df = st.session_state.df_result.copy()

# Update sidebar filter options dynamically
with st.sidebar:
    if "all_cats" in st.session_state:
        cat_filter = st.multiselect(
            "Filter by Category",
            options=st.session_state.all_cats,
            default=st.session_state.all_cats,
            key="cat_filter_live"
        )
        dept_filter = st.multiselect(
            "Filter by Department",
            options=st.session_state.all_depts,
            default=st.session_state.all_depts,
            key="dept_filter_live"
        )
    else:
        cat_filter = []
        dept_filter = []

if cat_filter:
    df = df[df["category"].isin(cat_filter)]
if dept_filter:
    df = df[df["department"].isin(dept_filter)]

anomalies = df[df["is_anomaly"] == 1].copy()
anomaly_rate = len(anomalies) / len(df) * 100 if len(df) > 0 else 0


# ─────────────────────────────────────────────────────────
# Screen 2 — KPI Cards
# ─────────────────────────────────────────────────────────
st.markdown("<div class='section-title'>📊 Overview</div>", unsafe_allow_html=True)

k1, k2, k3, k4, k5 = st.columns(5)

with k1:
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-label'>Total Transactions</div>
        <div class='kpi-value'>{len(df):,}</div>
    </div>""", unsafe_allow_html=True)
with k2:
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-label'>Total Spend</div>
        <div class='kpi-value' style='font-size:22px'>{fmt_inr(df['amount'].sum())}</div>
    </div>""", unsafe_allow_html=True)
with k3:
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-label'>Anomalies Flagged</div>
        <div class='kpi-value' style='color:#EF4444'>{len(anomalies)}</div>
    </div>""", unsafe_allow_html=True)
with k4:
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-label'>Anomaly Rate</div>
        <div class='kpi-value' style='color:#F59E0B'>{fmt_pct(anomaly_rate)}</div>
    </div>""", unsafe_allow_html=True)
with k5:
    high_risk = len(anomalies[anomalies["risk_level"] == "HIGH"])
    at_risk_spend = anomalies["amount"].sum()
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-label'>At-Risk Spend</div>
        <div class='kpi-value' style='font-size:22px;color:#EF4444'>{fmt_inr(at_risk_spend)}</div>
        <div class='kpi-sub'>{high_risk} HIGH risk</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────
# Screen 3 — Charts
# ─────────────────────────────────────────────────────────
st.markdown("<div class='section-title'>📈 Spend Analysis</div>", unsafe_allow_html=True)

c1, c2 = st.columns(2)

with c1:
    # Spend by category
    cat_spend = df.groupby("category")["amount"].sum().sort_values(ascending=False).reset_index()
    fig_cat = px.bar(
        cat_spend, x="category", y="amount",
        title="Total Spend by Category",
        color="amount",
        color_continuous_scale=["#C7D2FE", "#6366F1", "#312E81"],
        labels={"amount": "Amount (₹)", "category": "Category"},
    )
    fig_cat.update_layout(
        showlegend=False, coloraxis_showscale=False,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans"), margin=dict(t=40, b=20),
        yaxis_tickformat=","
    )
    st.plotly_chart(fig_cat, use_container_width=True)

with c2:
    # Anomalies by category
    anom_cat = anomalies.groupby("category").size().reset_index(name="count")
    fig_anom = px.bar(
        anom_cat, x="count", y="category", orientation="h",
        title="Anomalies by Category",
        color="count",
        color_continuous_scale=["#FEE2E2", "#EF4444", "#7F1D1D"],
        labels={"count": "# Anomalies", "category": ""},
    )
    fig_anom.update_layout(
        showlegend=False, coloraxis_showscale=False,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans"), margin=dict(t=40, b=20),
    )
    st.plotly_chart(fig_anom, use_container_width=True)


c3, c4 = st.columns(2)

with c3:
    # Monthly spend trend
    monthly = df.groupby("month").agg(
        total=("amount", "sum"),
        anomaly_spend=("amount", lambda x: x[df.loc[x.index, "is_anomaly"] == 1].sum())
    ).reset_index()
    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        x=monthly["month"], y=monthly["total"],
        name="Total Spend", mode="lines+markers",
        line=dict(color="#6366F1", width=3),
        marker=dict(size=8)
    ))
    fig_trend.add_trace(go.Scatter(
        x=monthly["month"], y=monthly["anomaly_spend"],
        name="At-Risk Spend", mode="lines+markers",
        line=dict(color="#EF4444", width=2, dash="dot"),
        marker=dict(size=7)
    ))
    fig_trend.update_layout(
        title="Monthly Spend Trend",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans"), margin=dict(t=40, b=20),
        legend=dict(orientation="h", y=1.12),
        yaxis_tickformat=","
    )
    st.plotly_chart(fig_trend, use_container_width=True)

with c4:
    # Risk level breakdown donut
    risk_counts = anomalies["risk_level"].value_counts().reset_index()
    risk_counts.columns = ["risk_level", "count"]
    colors = [RISK_COLORS.get(r, "#6B7280") for r in risk_counts["risk_level"]]
    fig_donut = go.Figure(go.Pie(
        labels=risk_counts["risk_level"],
        values=risk_counts["count"],
        hole=0.55,
        marker=dict(colors=colors),
        textinfo="label+percent",
        textfont=dict(family="DM Sans")
    ))
    fig_donut.update_layout(
        title="Anomalies by Risk Level",
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans"), margin=dict(t=40, b=10),
        annotations=[dict(text=f"{len(anomalies)}<br>flagged", x=0.5, y=0.5,
                          font_size=14, showarrow=False, font_family="DM Sans")]
    )
    st.plotly_chart(fig_donut, use_container_width=True)


# ─────────────────────────────────────────────────────────
# Screen 4 — Flagged Transactions Table
# ─────────────────────────────────────────────────────────
st.markdown("<div class='section-title'>🚨 Flagged Transactions</div>", unsafe_allow_html=True)

risk_choice = st.radio(
    "Show risk level:",
    ["All Anomalies", "HIGH only", "MEDIUM only", "LOW only"],
    horizontal=True
)

display_df = anomalies.copy()
if risk_choice == "HIGH only":
    display_df = display_df[display_df["risk_level"] == "HIGH"]
elif risk_choice == "MEDIUM only":
    display_df = display_df[display_df["risk_level"] == "MEDIUM"]
elif risk_choice == "LOW only":
    display_df = display_df[display_df["risk_level"] == "LOW"]

display_df = display_df.sort_values("anomaly_score", ascending=False)

# Render interactive table
cols_to_show = [
    "transaction_id", "date", "vendor", "category", "department",
    "amount", "payment_mode", "anomaly_score", "risk_level",
    "anomaly_reasons", "suggested_action"
]
cols_available = [c for c in cols_to_show if c in display_df.columns]

table_df = display_df[cols_available].copy()
table_df["date"] = table_df["date"].dt.strftime("%d %b %Y")
table_df["amount"] = table_df["amount"].apply(fmt_inr)
table_df["anomaly_score"] = table_df["anomaly_score"].apply(lambda x: f"{x:.0f}/100")
table_df.columns = [c.replace("_", " ").title() for c in table_df.columns]

st.dataframe(table_df, use_container_width=True, height=400)

st.markdown(f"*Showing **{len(display_df)}** flagged transactions.*")


# ─────────────────────────────────────────────────────────
# Screen 5 — Export
# ─────────────────────────────────────────────────────────
st.markdown("<div class='section-title'>📥 Export Report</div>", unsafe_allow_html=True)

ex1, ex2 = st.columns(2)

with ex1:
    csv_bytes = to_csv_bytes(anomalies[cols_available])
    st.download_button(
        label="⬇️ Download Flagged Transactions (CSV)",
        data=csv_bytes,
        file_name="anomaly_report.csv",
        mime="text/csv",
        use_container_width=True,
    )

with ex2:
    excel_bytes = to_excel_bytes(df, anomalies)
    st.download_button(
        label="📊 Download Full Report (Excel)",
        data=excel_bytes,
        file_name="expense_anomaly_full_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

st.divider()
st.caption("Expense Anomaly Detector · Built by Uma Bhargavi, CMA · Portfolio 2025")
