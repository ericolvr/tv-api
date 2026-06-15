VENV = .venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip

.PHONY: install preprocess run test client lint format help

help:
	@echo "Comandos disponíveis:"
	@echo "  make install     Cria o venv e instala as dependências"
	@echo "  make preprocess  Processa os CSVs e gera o parquet"
	@echo "  make run         Sobe a API em localhost:8000"
	@echo "  make test        Roda os testes unitários"
	@echo "  make lint        Verifica qualidade do código com pylint"
	@echo "  make format      Formata o código com black"
	@echo "  make client      Dispara o cliente REST (API deve estar rodando)"

install:
	python3 -m venv $(VENV)
	$(PIP) install -r requirements-dev.txt

preprocess:
	$(PYTHON) src/preprocessing/preprocess.py

run:
	$(PYTHON) -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

test:
	$(PYTHON) -m pytest tests/ -v

lint:
	$(PYTHON) -m pylint src/ tests/ conftest.py

format:
	$(PYTHON) -m black src/ tests/ conftest.py

client:
	$(PYTHON) src/client/client.py
