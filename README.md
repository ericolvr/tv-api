# TV Aberta Audience API

REST API para fornecimento de dados ao algoritmo de otimização da agenda de anúncios da TV Globo.

---

## Estrutura do projeto

```
tv-api/
├── data/
│   ├── raw/                  # CSVs originais (não versionados)
│   └── processed/            # Saída do pré-processamento (não versionada)
├── docs/
│   ├── arquitetura.png       # Diagrama da arquitetura GCP
│   └── arquitetura_gcp.md   # Justificativa dos serviços escolhidos
├── src/
│   ├── preprocessing/
│   │   └── preprocess.py     # Script de pré-processamento dos CSVs
│   ├── api/
│   │   ├── main.py           # Endpoints FastAPI
│   │   ├── repository.py     # Acesso aos dados processados
│   │   └── schemas.py        # Modelos Pydantic de resposta
│   └── client/
│       └── client.py         # Cliente REST para teste dos endpoints
├── tests/
│   ├── test_process.py       # Testes unitários do pré-processamento
│   └── test_api.py           # Testes unitários da API
├── conftest.py
├── Makefile
├── requirements.txt
└── requirements-dev.txt
```

---

## Como rodar

### 1. Instalar dependências

```bash
make install
```

### 2. Adicionar os CSVs

Copie os arquivos de dados para `data/raw/`:

```
data/raw/tvaberta_inventory_availability.csv
data/raw/tvaberta_program_audience.csv
```

### 3. Rodar o pré-processamento

```bash
make preprocess
```

Gera `data/processed/processed_data.parquet` com os dados agregados e a audiência prevista calculada.

### 4. Subir a API

```bash
make run
```

API disponível em `http://localhost:8000`.
Documentação interativa em `http://localhost:8000/docs`.

### 5. Rodar os testes

```bash
make test
```

### 6. Testar com o cliente REST

Com a API rodando em outro terminal:

```bash
make client
```

---

## Endpoints

### `GET /program`

Retorna os segundos disponíveis para anúncios e a audiência prevista para um programa em uma data específica.

**Parâmetros:**

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `program_code` | string | Código do programa (ex: `HUCK`) |
| `date` | date | Data de exibição (`YYYY-MM-DD`) |

**Exemplo:**

```
GET /program?program_code=HUCK&date=2020-08-01
```

```json
[
  {
    "signal": "SP1",
    "program_code": "HUCK",
    "date": "2020-08-01",
    "weekday": 5,
    "available_time": 300,
    "predicted_audience": 1106054
  }
]
```

---

### `GET /period`

Retorna todos os programas exibidos em um período com segundos disponíveis e audiência prevista.

**Parâmetros:**

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `start` | date | Data de início (`YYYY-MM-DD`) |
| `end` | date | Data de fim (`YYYY-MM-DD`) |

**Exemplo:**

```
GET /period?start=2020-08-01&end=2020-08-07
```

```json
{
  "total": 436,
  "items": [...]
}
```

---

## Decisões de design

### Mediana das últimas 4 exibições

A audiência prevista (`predicted_audience`) é calculada como a mediana das 4 exibições mais recentes do mesmo programa, no mesmo sinal e no mesmo dia da semana.

Grupos com menos de 4 exibições históricas usam todas as disponíveis. Programas sem nenhuma exibição histórica retornam `null` em `predicted_audience`.

### Separação entre pré-processamento e API

O `preprocess.py` é executado como um job separado e independente da API. A API lê apenas dados já processados, sem recalcular a mediana por request. Em produção, esse job é executado diariamente via Cloud Scheduler + Cloud Run Job (ver `docs/arquitetura_gcp.md`).

### Armazenamento em Parquet

O resultado do pré-processamento é salvo em formato Parquet — mais eficiente que CSV para leitura pela API, com tipos de dados preservados (datas como datetime, números como float).

---

## Arquitetura em nuvem (Tarefa 2)

Ver [`docs/arquitetura_gcp.md`](docs/arquitetura_gcp.md) para a descrição completa da arquitetura proposta no GCP.

---

## Comandos disponíveis

```bash
make help        # Lista todos os comandos
make install     # Cria o venv e instala dependências
make preprocess  # Processa os CSVs
make run         # Sobe a API
make test        # Roda os testes unitários
make lint        # Verifica qualidade do código (pylint)
make format      # Formata o código (black)
make client      # Dispara o cliente REST
```
