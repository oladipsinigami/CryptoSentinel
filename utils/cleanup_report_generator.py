# Cleanup Report Generator
"""
Utility functions to post-process generated Excel/CSV reports ensuring
consistent formatting, removing empty rows, and applying a standard
header style. These helpers are used by the server when serving downloadable
reports.
"""
import logging

try:
    import pandas as pd
    _PANDAS_AVAILABLE = True
except ImportError:
    _PANDAS_AVAILABLE = False
    pd = None


def clean_dataframe(df):
    """Standard cleaning steps for a report DataFrame.
    - Drop completely empty rows/columns
    - Reset index
    """
    if not _PANDAS_AVAILABLE or df is None:
        logging.warning("[cleanup_report] pandas not available; skipping clean.")
        return df
    if df.empty:
        logging.warning("[cleanup_report] Received empty DataFrame to clean.")
        return df
    df = df.dropna(how="all")
    df = df.dropna(axis=1, how="all")
    df = df.reset_index(drop=True)
    return df


def dataframe_to_excel(df, path: str) -> None:
    """Write a cleaned DataFrame to an Excel file."""
    if not _PANDAS_AVAILABLE:
        logging.error("[cleanup_report] pandas not installed — cannot write Excel.")
        return
    cleaned = clean_dataframe(df)
    cleaned.to_excel(path, index=False)
    logging.info(f"[cleanup_report] Saved cleaned report to {path}")


def dataframe_to_csv(df, path: str) -> None:
    """Write a cleaned DataFrame to a CSV file."""
    if not _PANDAS_AVAILABLE:
        logging.error("[cleanup_report] pandas not installed — cannot write CSV.")
        return
    cleaned = clean_dataframe(df)
    cleaned.to_csv(path, index=False)
    logging.info(f"[cleanup_report] Saved cleaned CSV report to {path}")
