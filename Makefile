PYTHON ?= .venv/bin/python
UVICORN ?= .venv/bin/uvicorn
HOST ?= 127.0.0.1
PORT ?= 8000

.PHONY: install test eval compile check run smoke clean-local backfill-raw-ashare resume-raw-ashare

install:
	$(PYTHON) -m pip install -U pip
	$(PYTHON) -m pip install -e .

test:
	$(PYTHON) -m pytest -v

eval:
	$(PYTHON) evals/run_eval.py

compile:
	$(PYTHON) -m compileall app

check: test eval compile
	git diff --check

run:
	$(UVICORN) app.main:app --host $(HOST) --port $(PORT)

smoke:
	curl -s -X POST http://$(HOST):$(PORT)/research/runs \
		-H 'Content-Type: application/json' \
		-d '{"research_topic":"A股量价类动量因子","source_mode":"auto","data_provider":"fixture","cache_enabled":true}'

clean-local:
	rm -rf .pytest_cache
	find app tests -type d -name __pycache__ -prune -exec rm -rf {} +

backfill-raw-ashare:
	$(PYTHON) scripts/backfill_raw_ashare.py --start $(START) --end $(END)

resume-raw-ashare:
	$(PYTHON) -c 'from app.market_data.catalog import DataCatalog; from app.market_data.ingestion import BackfillService; from app.market_data.sources.akshare_raw import AkshareRawDataSource; from app.market_data.store import MarketDataStore; c = DataCatalog(); r = BackfillService(c, MarketDataStore(), AkshareRawDataSource()).resume("$(RUN_ID)"); print(r)'
