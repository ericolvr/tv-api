VENV = .venv
PYTHON = $(VENV)/bin/python3
PIP = $(VENV)/bin/pip

.PHONY: install preprocess run test client

install:
	python3 -m venv $(VENV)
	$(PIP) install -r requirements-dev.txt

preprocess:
	$(PYTHON) src/preprocessing/preprocess.py

run:
	$(PYTHON) -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

test:
	$(PYTHON) -m pytest tests/ -v

client:
	$(PYTHON) src/client/client.py
