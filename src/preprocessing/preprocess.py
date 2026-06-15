"""
Pré-processamento dos dados de audiência e disponibilidade de inventário.

Lê os dois CSVs brutos, normaliza datas, calcula a mediana das 4 últimas
exibições por (program_code, signal, weekday) e salva o resultado em
data/processed/processed_data.parquet (e .csv para inspeção).
"""

from pathlib import Path

import pandas as pd

RAW_DIR = Path(__file__).parents[2] / "data" / "raw"
PROCESSED_DIR = Path(__file__).parents[2] / "data" / "processed"

INVENTORY_FILE = RAW_DIR / "tvaberta_inventory_availability.csv"
AUDIENCE_FILE = RAW_DIR / "tvaberta_program_audience.csv"


def load_inventory() -> pd.DataFrame:
    """Load and normalise the inventory CSV."""
    df = pd.read_csv(INVENTORY_FILE, sep=";", encoding="utf-8-sig")
    df["date"] = pd.to_datetime(df["date"], dayfirst=True)
    return df[["signal", "program_code", "date", "available_time"]]


def load_audience() -> pd.DataFrame:
    """Load and normalise the audience CSV."""
    df = pd.read_csv(AUDIENCE_FILE, sep=",", encoding="utf-8-sig")
    df["exhibition_date"] = pd.to_datetime(df["exhibition_date"])
    return df[["signal", "program_code", "exhibition_date", "average_audience"]]


def compute_predicted_audience(audience: pd.DataFrame) -> pd.DataFrame:
    """
    For each (program_code, signal, weekday), sort by date,
    take the 4 most recent exhibitions and return the median audience.
    Groups with fewer than 4 exhibitions use all available records.
    """
    audience = audience.copy()
    audience["weekday"] = audience["exhibition_date"].dt.dayofweek

    def last4_median(group: pd.DataFrame) -> float:
        sorted_group = group.sort_values("exhibition_date")
        return sorted_group["average_audience"].iloc[-4:].median()

    predicted = (
        audience
        .groupby(["signal", "program_code", "weekday"], as_index=False)
        .apply(last4_median, include_groups=False)
        .rename(columns={None: "predicted_audience"})
    )
    return predicted


def build_processed(
    inventory: pd.DataFrame,
    predicted: pd.DataFrame,
) -> pd.DataFrame:
    """Join inventory with predicted audience on (signal, program_code, weekday)."""
    inventory = inventory.copy()
    inventory["weekday"] = inventory["date"].dt.dayofweek
    result = inventory.merge(predicted, on=["signal", "program_code", "weekday"], how="left")
    cols = ["signal", "program_code", "date", "weekday", "available_time", "predicted_audience"]
    return result[cols]


def run():
    """Execute the full preprocessing pipeline."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    inventory = load_inventory()
    audience = load_audience()
    predicted = compute_predicted_audience(audience)
    result = build_processed(inventory, predicted)

    result.to_parquet(PROCESSED_DIR / "processed_data.parquet", index=False)
    result.to_csv(PROCESSED_DIR / "processed_data.csv", index=False)

    print(f"Processado: {len(result)} linhas salvas em {PROCESSED_DIR}")
    print(result.head(10).to_string())


if __name__ == "__main__":
    run()
