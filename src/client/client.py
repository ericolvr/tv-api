"""
Cliente REST para testar os endpoints da TV Aberta Audience API.
Uso: python src/client/client.py
A API deve estar rodando em http://localhost:8000
"""

import httpx

BASE_URL = "http://localhost:8000"


def get_program(program_code: str, date: str) -> None:
    url = f"{BASE_URL}/program"
    resp = httpx.get(url, params={"program_code": program_code, "date": date})
    print(f"\nGET /program?program_code={program_code}&date={date}")
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        for row in resp.json():
            print(
                f"  sinal={row['signal']}  available_time={row['available_time']}s  predicted_audience={row['predicted_audience']:.0f}"
            )
    else:
        print(f"  {resp.json()}")


def get_period(start: str, end: str) -> None:
    url = f"{BASE_URL}/period"
    resp = httpx.get(url, params={"start": start, "end": end})
    print(f"\nGET /period?start={start}&end={end}")
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"  Total de registros: {data['total']}")
        for row in data["items"][:5]:
            print(
                f"  {row['program_code']} ({row['signal']}) {row['date']}  {row['available_time']}s  audiência≈{row['predicted_audience']}"
            )
        if data["total"] > 5:
            print(f"  ... ({data['total'] - 5} registros omitidos)")
    else:
        print(f"  {resp.json()}")


if __name__ == "__main__":
    # endpoint por programa
    get_program("HUCK", "2020-08-01")
    get_program("VALE", "2020-08-17")
    get_program("XXX", "2020-08-01")  # deve retornar 404

    # endpoint por período
    get_period("2020-08-01", "2020-08-07")
    get_period("2020-09-01", "2020-08-01")  # deve retornar 422
