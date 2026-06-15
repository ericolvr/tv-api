"""Data access layer — reads processed parquet and filters records."""

from datetime import date
from pathlib import Path

import pandas as pd

PROCESSED_FILE = Path(__file__).parents[2] / "data" / "processed" / "processed_data.parquet"


def _load() -> pd.DataFrame:
    return pd.read_parquet(PROCESSED_FILE)


def get_by_program(program_code: str, exhibition_date: date) -> list[dict]:
    """Return inventory rows for a program on a specific date."""
    df = _load()
    weekday = exhibition_date.weekday()
    mask = (
        (df["program_code"] == program_code) &
        (df["date"].dt.date == exhibition_date)
    )
    result = df[mask].copy()
    if result["predicted_audience"].isna().any():
        fallback_mask = (
            (df["program_code"] == program_code) &
            (df["weekday"] == weekday) &
            df["predicted_audience"].notna()
        )
        if fallback_mask.any():
            median_val = df.loc[fallback_mask, "predicted_audience"].iloc[0]
            result["predicted_audience"] = result["predicted_audience"].fillna(median_val)
    return result.to_dict(orient="records")


def get_by_period(start: date, end: date) -> list[dict]:
    """Return inventory rows for all programs within a date range."""
    df = _load()
    mask = (df["date"].dt.date >= start) & (df["date"].dt.date <= end)
    return df[mask].to_dict(orient="records")
