"""Unit tests for the FastAPI endpoints."""

from unittest.mock import patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

MOCK_ROWS = [
    {
        "signal": "SP1",
        "program_code": "HUCK",
        "date": pd.Timestamp("2020-08-01"),
        "weekday": 5,
        "available_time": 300,
        "predicted_audience": 1_106_054.0,
    },
    {
        "signal": "BH",
        "program_code": "HUCK",
        "date": pd.Timestamp("2020-08-01"),
        "weekday": 5,
        "available_time": 120,
        "predicted_audience": 250_000.0,
    },
]

MOCK_PERIOD_ROWS = MOCK_ROWS + [
    {
        "signal": "SP1",
        "program_code": "VALE",
        "date": pd.Timestamp("2020-08-03"),
        "weekday": 0,
        "available_time": 180,
        "predicted_audience": 1_800_000.0,
    },
]


class TestProgramEndpoint:
    """Tests for GET /program."""

    def test_retorna_dados_validos(self):
        """Returns correct fields and values for a known program."""
        with patch("api.main.get_by_program", return_value=MOCK_ROWS):
            resp = client.get(
                "/program", params={"program_code": "HUCK", "date": "2020-08-01"}
            )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        assert data[0]["program_code"] == "HUCK"
        assert data[0]["available_time"] == 300
        assert data[0]["predicted_audience"] == pytest.approx(1_106_054)

    def test_404_programa_inexistente(self):
        """Returns 404 when program is not found."""
        with patch("api.main.get_by_program", return_value=[]):
            resp = client.get(
                "/program", params={"program_code": "XXX", "date": "2020-08-01"}
            )
        assert resp.status_code == 404

    def test_422_parametros_faltando(self):
        """Returns 422 when required query params are missing."""
        resp = client.get("/program", params={"program_code": "HUCK"})
        assert resp.status_code == 422

    def test_422_data_invalida(self):
        """Returns 422 when date format is invalid."""
        resp = client.get(
            "/program", params={"program_code": "HUCK", "date": "not-a-date"}
        )
        assert resp.status_code == 422

    def test_predicted_audience_pode_ser_nulo(self):
        """Returns null predicted_audience when no historical data exists."""
        row_sem_historico = [{**MOCK_ROWS[0], "predicted_audience": None}]
        with patch("api.main.get_by_program", return_value=row_sem_historico):
            resp = client.get(
                "/program",
                params={"program_code": "HUCK", "date": "2020-08-01"},
            )
        assert resp.status_code == 200
        assert resp.json()[0]["predicted_audience"] is None


class TestPeriodEndpoint:
    """Tests for GET /period."""

    def test_retorna_total_correto(self):
        """Returns correct total count and items."""
        with patch("api.main.get_by_period", return_value=MOCK_PERIOD_ROWS):
            resp = client.get(
                "/period", params={"start": "2020-08-01", "end": "2020-08-07"}
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert len(data["items"]) == 3

    def test_periodo_vazio(self):
        """Returns empty list and total=0 when no records exist."""
        with patch("api.main.get_by_period", return_value=[]):
            resp = client.get(
                "/period", params={"start": "2020-01-01", "end": "2020-01-01"}
            )
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    def test_422_start_depois_de_end(self):
        """Returns 422 when start date is after end date."""
        resp = client.get(
            "/period", params={"start": "2020-09-01", "end": "2020-08-01"}
        )
        assert resp.status_code == 422

    def test_422_parametros_faltando(self):
        """Returns 422 when required query params are missing."""
        resp = client.get("/period", params={"start": "2020-08-01"})
        assert resp.status_code == 422

    def test_422_data_invalida(self):
        """Returns 422 when date format is invalid."""
        resp = client.get("/period", params={"start": "abc", "end": "2020-08-07"})
        assert resp.status_code == 422
