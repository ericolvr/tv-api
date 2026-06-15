"""Unit tests for the preprocessing pipeline."""

import pandas as pd
import pytest

from preprocessing.preprocess import build_processed, compute_predicted_audience


def make_audience(rows: list[dict]) -> pd.DataFrame:
    """Build an audience DataFrame from a list of dicts."""
    df = pd.DataFrame(rows)
    df["exhibition_date"] = pd.to_datetime(df["exhibition_date"])
    return df


def make_inventory(rows: list[dict]) -> pd.DataFrame:
    """Build an inventory DataFrame from a list of dicts."""
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df


class TestComputePredictedAudience:
    """Tests for compute_predicted_audience."""

    def test_mediana_das_4_ultimas(self):
        """With 6 exhibitions, uses only the 4 most recent."""
        aud = make_audience(
            [
                {
                    "signal": "SP1",
                    "program_code": "HUCK",
                    "exhibition_date": "2020-07-04",
                    "average_audience": 1_000_000,
                },
                {
                    "signal": "SP1",
                    "program_code": "HUCK",
                    "exhibition_date": "2020-07-11",
                    "average_audience": 2_000_000,
                },
                {
                    "signal": "SP1",
                    "program_code": "HUCK",
                    "exhibition_date": "2020-07-18",
                    "average_audience": 3_000_000,
                },
                {
                    "signal": "SP1",
                    "program_code": "HUCK",
                    "exhibition_date": "2020-07-25",
                    "average_audience": 4_000_000,
                },
                {
                    "signal": "SP1",
                    "program_code": "HUCK",
                    "exhibition_date": "2020-08-01",
                    "average_audience": 5_000_000,
                },
                {
                    "signal": "SP1",
                    "program_code": "HUCK",
                    "exhibition_date": "2020-08-08",
                    "average_audience": 6_000_000,
                },
            ]
        )
        result = compute_predicted_audience(aud)
        row = result[(result["signal"] == "SP1") & (result["program_code"] == "HUCK")]
        # 4 últimas: 3M, 4M, 5M, 6M → mediana = (4M+5M)/2 = 4.5M
        assert row["predicted_audience"].values[0] == pytest.approx(4_500_000)

    def test_menos_de_4_exibicoes_usa_todas(self):
        """With 2 exhibitions, uses both to calculate the median."""
        aud = make_audience(
            [
                {
                    "signal": "BH",
                    "program_code": "BIGB",
                    "exhibition_date": "2020-07-06",
                    "average_audience": 100_000,
                },
                {
                    "signal": "BH",
                    "program_code": "BIGB",
                    "exhibition_date": "2020-07-13",
                    "average_audience": 200_000,
                },
            ]
        )
        result = compute_predicted_audience(aud)
        row = result[(result["signal"] == "BH") & (result["program_code"] == "BIGB")]
        assert row["predicted_audience"].values[0] == pytest.approx(150_000)

    def test_uma_exibicao_mediana_e_ela_mesma(self):
        """With a single exhibition, median equals that value."""
        aud = make_audience(
            [
                {
                    "signal": "RJ",
                    "program_code": "VALE",
                    "exhibition_date": "2020-07-08",
                    "average_audience": 500_000,
                },
            ]
        )
        result = compute_predicted_audience(aud)
        row = result[(result["signal"] == "RJ") & (result["program_code"] == "VALE")]
        assert row["predicted_audience"].values[0] == pytest.approx(500_000)

    def test_separa_por_dia_da_semana(self):
        """Same program/signal on different weekdays produces independent medians."""
        aud = make_audience(
            [
                {
                    "signal": "SP1",
                    "program_code": "PTV1",
                    "exhibition_date": "2020-07-06",
                    "average_audience": 1_000_000,
                },
                {
                    "signal": "SP1",
                    "program_code": "PTV1",
                    "exhibition_date": "2020-07-07",
                    "average_audience": 9_000_000,
                },
            ]
        )
        result = compute_predicted_audience(aud)
        seg = result[
            (result["signal"] == "SP1")
            & (result["program_code"] == "PTV1")
            & (result["weekday"] == 0)
        ]
        ter = result[
            (result["signal"] == "SP1")
            & (result["program_code"] == "PTV1")
            & (result["weekday"] == 1)
        ]
        assert seg["predicted_audience"].values[0] == pytest.approx(1_000_000)
        assert ter["predicted_audience"].values[0] == pytest.approx(9_000_000)

    def test_separa_por_sinal(self):
        """Same program on different signals produces independent medians."""
        aud = make_audience(
            [
                {
                    "signal": "SP1",
                    "program_code": "HUCK",
                    "exhibition_date": "2020-07-04",
                    "average_audience": 2_000_000,
                },
                {
                    "signal": "BH",
                    "program_code": "HUCK",
                    "exhibition_date": "2020-07-04",
                    "average_audience": 500_000,
                },
            ]
        )
        result = compute_predicted_audience(aud)
        sp1 = result[(result["signal"] == "SP1") & (result["program_code"] == "HUCK")]
        bh = result[(result["signal"] == "BH") & (result["program_code"] == "HUCK")]
        assert sp1["predicted_audience"].values[0] == pytest.approx(2_000_000)
        assert bh["predicted_audience"].values[0] == pytest.approx(500_000)


class TestBuildProcessed:
    """Tests for build_processed."""

    def test_sem_historico_gera_nulo(self):
        """Program in inventory with no audience history → null predicted_audience."""
        inventory = make_inventory(
            [
                {
                    "signal": "SP1",
                    "program_code": "NOVO",
                    "date": "2020-08-01",
                    "available_time": 300,
                },
            ]
        )
        predicted = pd.DataFrame(
            columns=["signal", "program_code", "weekday", "predicted_audience"]
        )
        result = build_processed(inventory, predicted)
        assert result["predicted_audience"].isna().all()

    def test_join_correto(self):
        """Inventory and audience are joined on the correct weekday."""
        inventory = make_inventory(
            [
                {
                    "signal": "SP1",
                    "program_code": "HUCK",
                    "date": "2020-08-01",
                    "available_time": 300,
                },  # sábado=5
            ]
        )
        predicted = pd.DataFrame(
            [
                {
                    "signal": "SP1",
                    "program_code": "HUCK",
                    "weekday": 5,
                    "predicted_audience": 1_000_000,
                },
                {
                    "signal": "SP1",
                    "program_code": "HUCK",
                    "weekday": 6,
                    "predicted_audience": 9_999_999,
                },
            ]
        )
        result = build_processed(inventory, predicted)
        assert result["predicted_audience"].values[0] == pytest.approx(1_000_000)
