"""
Versão GCP do pipeline de pré-processamento.

Lê os CSVs do Cloud Storage, executa o mesmo cálculo de mediana da versão
local, grava o resultado no BigQuery e registra o checkpoint no Firestore
para permitir retomada em caso de falha.

Variáveis de ambiente necessárias:
  GCS_BUCKET   — nome do bucket (ex: tv-api-raw-data)
  BQ_PROJECT   — project ID do GCP (ex: tv-api-2026)
  BQ_DATASET   — dataset do BigQuery (ex: tv_api)
  BQ_TABLE     — tabela de destino (ex: processed_data)
"""

import io
import os

import pandas as pd
from google.cloud import bigquery, firestore, storage

GCS_BUCKET = os.environ["GCS_BUCKET"]
BQ_PROJECT = os.environ["BQ_PROJECT"]
BQ_DATASET = os.environ["BQ_DATASET"]
BQ_TABLE = os.environ["BQ_TABLE"]

INVENTORY_BLOB = "tvaberta_inventory_availability.csv"
AUDIENCE_BLOB = "tvaberta_program_audience.csv"

_firestore = firestore.Client()
_job_doc = _firestore.collection("jobs").document("preprocess_daily")


# ---------------------------------------------------------------------------
# Checkpoint
# ---------------------------------------------------------------------------

def read_checkpoint() -> dict:
    """Lê o estado do job anterior no Firestore."""
    doc = _job_doc.get()
    return doc.to_dict() if doc.exists else {}


def write_checkpoint(stage: str, **kwargs) -> None:
    """Grava o estado atual no Firestore."""
    _job_doc.set({"stage": stage, "updated_at": firestore.SERVER_TIMESTAMP, **kwargs})


# ---------------------------------------------------------------------------
# I/O — Cloud Storage
# ---------------------------------------------------------------------------

def _read_gcs_csv(blob_name: str, **kwargs) -> pd.DataFrame:
    """Baixa um CSV do GCS e retorna como DataFrame."""
    client = storage.Client()
    blob = client.bucket(GCS_BUCKET).blob(blob_name)
    content = blob.download_as_bytes()
    return pd.read_csv(io.BytesIO(content), **kwargs)


def load_inventory() -> pd.DataFrame:
    """Lê e normaliza o CSV de inventário a partir do GCS."""
    df = _read_gcs_csv(INVENTORY_BLOB, sep=";", encoding="utf-8-sig")
    df["date"] = pd.to_datetime(df["date"], dayfirst=True)
    return df[["signal", "program_code", "date", "available_time"]]


def load_audience() -> pd.DataFrame:
    """Lê e normaliza o CSV de audiência a partir do GCS."""
    df = _read_gcs_csv(AUDIENCE_BLOB, sep=",", encoding="utf-8-sig")
    df["exhibition_date"] = pd.to_datetime(df["exhibition_date"])
    return df[["signal", "program_code", "exhibition_date", "average_audience"]]


# ---------------------------------------------------------------------------
# Cálculo — idêntico à versão local
# ---------------------------------------------------------------------------

def compute_predicted_audience(audience: pd.DataFrame) -> pd.DataFrame:
    """Mediana das 4 últimas exibições por (program_code, signal, weekday)."""
    audience = audience.copy()
    audience["weekday"] = audience["exhibition_date"].dt.dayofweek

    def last4_median(group: pd.DataFrame) -> float:
        return group.sort_values("exhibition_date")["average_audience"].iloc[-4:].median()

    return (
        audience.groupby(["signal", "program_code", "weekday"], as_index=False)
        .apply(last4_median, include_groups=False)
        .rename(columns={None: "predicted_audience"})
    )


def build_processed(inventory: pd.DataFrame, predicted: pd.DataFrame) -> pd.DataFrame:
    """Join do inventário com a audiência prevista."""
    inventory = inventory.copy()
    inventory["weekday"] = inventory["date"].dt.dayofweek
    result = inventory.merge(predicted, on=["signal", "program_code", "weekday"], how="left")
    return result[["signal", "program_code", "date", "weekday", "available_time", "predicted_audience"]]


# ---------------------------------------------------------------------------
# I/O — BigQuery
# ---------------------------------------------------------------------------

def write_to_bigquery(df: pd.DataFrame) -> None:
    """Grava o DataFrame no BigQuery (WRITE_TRUNCATE — recria a tabela a cada execução)."""
    client = bigquery.Client(project=BQ_PROJECT)
    table_ref = f"{BQ_PROJECT}.{BQ_DATASET}.{BQ_TABLE}"
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")
    job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
    job.result()  # bloqueia até confirmação de escrita


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------

def run() -> None:
    """Executa o pipeline completo com checkpoint no Firestore."""
    checkpoint = read_checkpoint()
    print(f"Checkpoint anterior: {checkpoint.get('stage', 'nenhum')}")

    if checkpoint.get("stage") not in ("csvs_loaded", "computed", "done"):
        print("Carregando CSVs do GCS...")
        inventory = load_inventory()
        audience = load_audience()
        write_checkpoint("csvs_loaded", rows_inventory=len(inventory), rows_audience=len(audience))
    else:
        print("CSVs já carregados, pulando...")
        inventory = load_inventory()
        audience = load_audience()

    if checkpoint.get("stage") not in ("computed", "done"):
        print("Calculando audiência prevista...")
        predicted = compute_predicted_audience(audience)
        result = build_processed(inventory, predicted)
        write_checkpoint("computed", rows_processed=len(result))
    else:
        print("Cálculo já concluído, pulando...")
        predicted = compute_predicted_audience(audience)
        result = build_processed(inventory, predicted)

    if checkpoint.get("stage") != "done":
        print(f"Gravando {len(result)} linhas no BigQuery...")
        write_to_bigquery(result)
        write_checkpoint("done", rows_written=len(result))
        print("Pipeline concluído com sucesso.")
    else:
        print("Job já concluído hoje, nada a fazer.")


if __name__ == "__main__":
    run()
