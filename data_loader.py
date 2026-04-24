import pandas as pd
import streamlit as st
import os

REQUIRED_COLUMNS = {"date", "vendor", "category", "amount"}

OPTIONAL_COLUMNS = {
    "transaction_id": "TXN_AUTO",
    "department": "General",
    "payment_mode": "Unknown",
}

def load_data(file) -> pd.DataFrame:
    try:
        if file.name.endswith(".csv"):
            df = pd.read_csv(file)
        elif file.name.endswith((".xlsx", ".xls")):
            df = pd.read_excel(file)
        else:
            st.error("Unsupported file type.")
            return None
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
        return validate_columns(df)
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return None

def load_sample_data() -> pd.DataFrame:
    path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "data", "sample_expenses.csv"
    )
    path = os.path.normpath(path)
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    return validate_columns(df)

def validate_columns(df: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        st.error(f"Missing required columns: {', '.join(missing)}")
        return None
    for col, default in OPTIONAL_COLUMNS.items():
        if col not in df.columns:
            df[col] = default
    if "transaction_id" in df.columns and df["transaction_id"].iloc[0] == "TXN_AUTO":
        df["transaction_id"] = [f"TXN{str(i+1).zfill(3)}" for i in range(len(df))]
    return df
