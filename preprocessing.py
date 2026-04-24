"""
preprocessing.py
Cleans data, parses dates, normalizes vendors, creates engineered features.
"""

import pandas as pd
import numpy as np
from scipy import stats


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    """Main preprocessing pipeline."""
    df = df.copy()

    # 1. Drop fully blank rows
    df.dropna(how="all", inplace=True)

    # 2. Parse amount
    if df["amount"].dtype == object:
        df["amount"] = (
            df["amount"]
            .astype(str)
            .str.replace(r"[₹$,\s]", "", regex=True)
            .str.strip()
        )
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")
    df.dropna(subset=["amount"], inplace=True)
    df = df[df["amount"] > 0]

    # 3. Parse date
    df["date"] = pd.to_datetime(df["date"], errors="coerce", dayfirst=False)
    df.dropna(subset=["date"], inplace=True)
    df["month"] = df["date"].dt.to_period("M").astype(str)
    df["day_of_week"] = df["date"].dt.day_name()

    # 4. Normalize vendor names
    df["vendor"] = (
        df["vendor"]
        .astype(str)
        .str.strip()
        .str.title()
    )
    df["category"] = (
        df["category"]
        .astype(str)
        .str.strip()
        .str.title()
    )

    # 5. Feature engineering
    df = _add_features(df)

    return df.reset_index(drop=True)


def _add_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create statistical and behavioural features for anomaly detection."""

    # Vendor frequency (how often each vendor appears)
    vendor_freq = df["vendor"].value_counts().to_dict()
    df["vendor_frequency"] = df["vendor"].map(vendor_freq)

    # Category-level stats
    cat_stats = df.groupby("category")["amount"].agg(["mean", "std", "median"])
    cat_stats.columns = ["cat_mean", "cat_std", "cat_median"]
    df = df.join(cat_stats, on="category")

    # Ratio of transaction amount to category mean
    df["amount_to_cat_ratio"] = df["amount"] / df["cat_mean"].replace(0, np.nan)

    # Global z-score of amount
    df["amount_zscore"] = np.abs(stats.zscore(df["amount"].fillna(0)))

    # Percentile rank
    df["amount_percentile"] = df["amount"].rank(pct=True) * 100

    # Duplicate detection: same vendor + amount + category on same/close date
    df_sorted = df.sort_values("date")
    df["duplicate_key"] = (
        df["vendor"].astype(str) + "_" +
        df["amount"].astype(str) + "_" +
        df["category"].astype(str)
    )
    dup_counts = df["duplicate_key"].value_counts().to_dict()
    df["duplicate_count"] = df["duplicate_key"].map(dup_counts)

    # Weekend / off-hours flag
    df["is_weekend"] = df["date"].dt.dayofweek >= 5

    return df
