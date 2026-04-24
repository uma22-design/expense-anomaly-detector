"""
utils.py
Helper functions: formatting, export, KPI cards.
"""

import pandas as pd
import io


# ──────────────────────────────────────────────
# Formatting
# ──────────────────────────────────────────────

def fmt_inr(value: float) -> str:
    """Format number in Indian Rupee style (e.g., ₹1,23,456)."""
    try:
        value = int(round(value))
        s = str(abs(value))
        if len(s) <= 3:
            result = s
        else:
            last3 = s[-3:]
            rest = s[:-3]
            groups = []
            while len(rest) > 2:
                groups.append(rest[-2:])
                rest = rest[:-2]
            if rest:
                groups.append(rest)
            result = ",".join(reversed(groups)) + "," + last3
        return f"₹{'-' if value < 0 else ''}{result}"
    except Exception:
        return f"₹{value:,.0f}"


def fmt_pct(value: float, decimals: int = 1) -> str:
    return f"{value:.{decimals}f}%"


# ──────────────────────────────────────────────
# Export
# ──────────────────────────────────────────────

def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def to_excel_bytes(df: pd.DataFrame, anomaly_df: pd.DataFrame) -> bytes:
    """Create a multi-sheet Excel report."""
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="All Transactions", index=False)
        anomaly_df.to_excel(writer, sheet_name="Flagged Transactions", index=False)

        # Summary sheet
        summary_data = {
            "Metric": [
                "Total Transactions",
                "Total Spend",
                "Anomaly Count",
                "Anomaly Rate (%)",
                "HIGH Risk Count",
                "MEDIUM Risk Count",
                "LOW Risk Count",
            ],
            "Value": [
                len(df),
                df["amount"].sum(),
                anomaly_df["is_anomaly"].sum(),
                round(len(anomaly_df) / len(df) * 100, 1),
                len(anomaly_df[anomaly_df["risk_level"] == "HIGH"]),
                len(anomaly_df[anomaly_df["risk_level"] == "MEDIUM"]),
                len(anomaly_df[anomaly_df["risk_level"] == "LOW"]),
            ],
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name="Summary", index=False)

    return buffer.getvalue()


# ──────────────────────────────────────────────
# Display helpers
# ──────────────────────────────────────────────

RISK_COLORS = {
    "HIGH": "#EF4444",
    "MEDIUM": "#F59E0B",
    "LOW": "#3B82F6",
    "Normal": "#6B7280",
}

RISK_BADGE_HTML = {
    "HIGH": '<span style="background:#EF4444;color:#fff;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:700;">HIGH</span>',
    "MEDIUM": '<span style="background:#F59E0B;color:#fff;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:700;">MEDIUM</span>',
    "LOW": '<span style="background:#3B82F6;color:#fff;padding:2px 8px;border-radius:4px;font-size:12px;font-weight:700;">LOW</span>',
    "Normal": '<span style="background:#D1FAE5;color:#065F46;padding:2px 8px;border-radius:4px;font-size:12px;">Normal</span>',
}


def score_bar_html(score: float) -> str:
    """Render a small inline score bar."""
    color = "#EF4444" if score >= 70 else "#F59E0B" if score >= 40 else "#3B82F6"
    return (
        f'<div style="display:flex;align-items:center;gap:6px;">'
        f'<div style="background:#E5E7EB;border-radius:4px;width:80px;height:10px;">'
        f'<div style="background:{color};border-radius:4px;width:{score}%;height:10px;"></div>'
        f'</div>'
        f'<span style="font-size:12px;font-weight:600;">{score:.0f}</span>'
        f'</div>'
    )
