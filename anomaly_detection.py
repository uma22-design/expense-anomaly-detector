"""
anomaly_detection.py
Hybrid rule-based + Isolation Forest anomaly detection.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


# ──────────────────────────────────────────────
# Rule-based flags
# ──────────────────────────────────────────────

def apply_rules(df: pd.DataFrame) -> pd.DataFrame:
    """Apply deterministic business rules and add a rule_flag column."""
    df = df.copy()
    df["rule_flag"] = 0

    p97 = df["amount"].quantile(0.97)

    # Rule 1: Very high amount (top 3%)
    df.loc[df["amount"] >= p97, "rule_flag"] = 1

    # Rule 2: Rare vendor (appears ≤ 2 times)
    df.loc[df["vendor_frequency"] <= 2, "rule_flag"] = 1

    # Rule 3: Amount > 3× category mean
    df.loc[df["amount_to_cat_ratio"] > 3, "rule_flag"] = 1

    # Rule 4: Duplicate transactions
    df.loc[df["duplicate_count"] > 1, "rule_flag"] = 1

    # Rule 5: Cash payment + high amount (>10,000)
    df.loc[
        (df["payment_mode"].str.lower() == "cash") & (df["amount"] > 10000),
        "rule_flag"
    ] = 1

    # Rule 6: Weekend high-value transaction
    df.loc[df["is_weekend"] & (df["amount"] > df["amount"].quantile(0.90)), "rule_flag"] = 1

    return df


# ──────────────────────────────────────────────
# Isolation Forest
# ──────────────────────────────────────────────

FEATURE_COLS = [
    "amount",
    "vendor_frequency",
    "amount_to_cat_ratio",
    "amount_zscore",
    "amount_percentile",
    "duplicate_count",
]


def run_isolation_forest(df: pd.DataFrame, contamination: float = 0.1) -> pd.DataFrame:
    """Fit Isolation Forest and return anomaly scores + ml_flag."""
    df = df.copy()

    features = df[FEATURE_COLS].fillna(0)
    scaler = StandardScaler()
    X = scaler.fit_transform(features)

    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        random_state=42,
        max_samples="auto",
    )
    model.fit(X)

    scores = model.score_samples(X)          # raw anomaly score (lower = more anomalous)
    df["if_score"] = scores
    df["if_score_norm"] = _normalize_scores(scores)   # 0-100, higher = more anomalous
    df["ml_flag"] = (model.predict(X) == -1).astype(int)

    return df, model, scaler


def _normalize_scores(scores: np.ndarray) -> np.ndarray:
    """Invert and scale so higher value = more anomalous (0–100)."""
    inverted = -scores
    mn, mx = inverted.min(), inverted.max()
    if mx == mn:
        return np.zeros_like(scores)
    return ((inverted - mn) / (mx - mn)) * 100


# ──────────────────────────────────────────────
# Combined anomaly flag
# ──────────────────────────────────────────────

def detect_anomalies(df: pd.DataFrame, contamination: float = 0.1):
    """Full pipeline: rules + ML → combined anomaly flag + score."""
    df = apply_rules(df)
    df, model, scaler = run_isolation_forest(df, contamination)

    # Final flag: anomaly if EITHER rule OR ML flags it
    df["is_anomaly"] = ((df["rule_flag"] == 1) | (df["ml_flag"] == 1)).astype(int)

    # Composite anomaly score (weighted: 60% ML score, 40% rule-based boost)
    df["anomaly_score"] = (
        0.60 * df["if_score_norm"] +
        0.40 * df["rule_flag"] * 100
    ).clip(0, 100).round(1)

    return df, model, scaler
