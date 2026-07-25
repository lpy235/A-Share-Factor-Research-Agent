PYTHON ?= .venv/bin/python
UVICORN ?= .venv/bin/uvicorn
HOST ?= 127.0.0.1
PORT ?= 8000
SOURCE ?= snapshot_csv

.PHONY: install test eval compile check run smoke clean-local backfill-raw-ashare resume-raw-ashare update-raw-ashare

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
	$(PYTHON) scripts/backfill_raw_ashare.py --start $(START) --end $(END) --daily-bars-csv $(DAILY_BARS_CSV) --source $(SOURCE)

resume-raw-ashare:
	$(PYTHON) scripts/backfill_raw_ashare.py --resume-run-id $(RUN_ID) --daily-bars-csv $(DAILY_BARS_CSV) --source $(SOURCE)

update-raw-ashare:
	$(PYTHON) scripts/update_raw_ashare.py --trade-date $(TRADE_DATE) --parent-version $(PARENT_VERSION) --daily-bars-csv $(DAILY_BARS_CSV) --source $(SOURCE)
