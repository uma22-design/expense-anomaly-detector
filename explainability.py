"""
explainability.py
Human-readable reason labels and suggested actions for every flagged transaction.
"""

import pandas as pd
import numpy as np


# ──────────────────────────────────────────────
# Reason generation
# ──────────────────────────────────────────────

def assign_reasons(df: pd.DataFrame) -> pd.DataFrame:
    """Generate a plain-English reason string for each anomaly."""
    df = df.copy()
    df["anomaly_reasons"] = ""
    df["suggested_action"] = ""

    mask = df["is_anomaly"] == 1

    def build_reason(row):
        reasons = []

        p97 = df["amount"].quantile(0.97)
        if row["amount"] >= p97:
            reasons.append(f"High amount (₹{row['amount']:,.0f} > 97th pctile ₹{p97:,.0f})")

        if row["vendor_frequency"] <= 2:
            reasons.append(f"Rare vendor (appeared only {int(row['vendor_frequency'])}x)")

        if row["amount_to_cat_ratio"] > 3:
            reasons.append(
                f"Amount {row['amount_to_cat_ratio']:.1f}× above {row['category']} average "
                f"(₹{row['cat_mean']:,.0f})"
            )

        if row["duplicate_count"] > 1:
            reasons.append(
                f"Possible duplicate — {int(row['duplicate_count'])} identical entries found"
            )

        if str(row.get("payment_mode", "")).lower() == "cash" and row["amount"] > 10000:
            reasons.append(f"Cash payment above ₹10,000 threshold")

        if row.get("is_weekend") and row["amount"] > df["amount"].quantile(0.90):
            reasons.append("High-value transaction on weekend")

        if row["ml_flag"] == 1 and not reasons:
            reasons.append(
                f"ML model flagged as anomalous (score: {row['if_score_norm']:.0f}/100)"
            )

        return "; ".join(reasons) if reasons else "ML-detected pattern deviation"

    def build_action(row):
        reasons = row["anomaly_reasons"].lower()
        if "duplicate" in reasons:
            return "Review for duplicate payment"
        if "cash" in reasons:
            return "Verify cash receipt and approval"
        if "rare vendor" in reasons:
            return "Verify vendor legitimacy and PO"
        if "high amount" in reasons or "above" in reasons:
            return "Verify invoice and match with PO"
        if "weekend" in reasons:
            return "Check approver authorisation"
        return "Review transaction and check approval"

    df.loc[mask, "anomaly_reasons"] = df[mask].apply(build_reason, axis=1)
    df.loc[mask, "suggested_action"] = df[mask].apply(build_action, axis=1)

    return df


# ──────────────────────────────────────────────
# Risk level
# ──────────────────────────────────────────────

def assign_risk_level(df: pd.DataFrame) -> pd.DataFrame:
    """Add a HIGH / MEDIUM / LOW risk label based on anomaly score."""
    df = df.copy()
    df["risk_level"] = "Normal"
    df.loc[(df["is_anomaly"] == 1) & (df["anomaly_score"] >= 70), "risk_level"] = "HIGH"
    df.loc[
        (df["is_anomaly"] == 1) & (df["anomaly_score"] >= 40) & (df["anomaly_score"] < 70),
        "risk_level"
    ] = "MEDIUM"
    df.loc[(df["is_anomaly"] == 1) & (df["anomaly_score"] < 40), "risk_level"] = "LOW"
    return df
