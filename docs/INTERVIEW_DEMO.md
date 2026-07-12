# Interview Demo Guide

## 30-Second Summary

This project is an A-share factor research workflow. It turns research notes or public materials into factor hypotheses, validates the generated factor formulas with a restricted DSL, runs deterministic single-factor backtests, and produces a traceable report with IS/OOS metrics, IC decay, factor-correlation diagnostics, charts, and downloadable JSON artifacts.

## 5-Minute Walkthrough

1. Start the app:

```bash
pip install -e ".[dev]"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

2. Open the dashboard:

```text
http://127.0.0.1:8000/
```

3. Run the default topic `A股量价类动量因子`.

4. Explain the workflow:

```text
source material
-> retrieval
-> factor hypothesis extraction
-> restricted Factor DSL
-> market data loading
-> single-factor backtest
-> factor selection
-> report and artifacts
```

5. Show the result:

- `metrics`: IS Rank IC, OOS Rank IC, ICIR, coverage, missing ratio, Sharpe, IC decay.
- `backtest_assumptions`: universe, date range, provider, transaction cost, and IS/OOS split.
- `artifacts`: Markdown report, metrics JSON, factor JSON, backtest series JSON, factor-correlation JSON, and charts.
- `audit_trail`: why sources, formulas, and factors were accepted or rejected.

## What To Emphasize

- I did not let LLM output execute arbitrary Python. The model can only produce a schema-validated factor spec and a whitelisted DSL formula.
- I separated sample-in and sample-out metrics, because a factor that only works in-sample is usually not useful.
- I added IC decay and factor-correlation diagnostics to catch overfitting and redundant factors.
- I kept the default demo deterministic: no API key, no live data, and no web fetch are required.
- The system is an engineering prototype for research workflow automation, not an auto-trading system.

## Honest Limitations

- Fixture data is for reproducible demonstration, not real trading validation.
- AKShare mode depends on public data availability and still needs stronger production data cleaning.
- The backtest does not yet model slippage, liquidity constraints, limit-up/limit-down execution, ST filters, or survivorship-bias-free universes.
- Factor selection thresholds are intentionally simple and should be calibrated on a larger research set.

## Good Interview Answers

If asked why this is useful:

> It standardizes the first pass of factor research. Instead of manually copying ideas from research notes, writing formulas, running one-off scripts, and losing the audit trail, this workflow keeps the hypothesis, formula, validation, backtest, charts, and report in one reproducible run.

If asked what you would improve next:

> I would add a production-grade A-share data layer, stricter universe construction, transaction-cost and liquidity modeling, then run a larger factor library with rolling OOS validation.

If asked where AI is used:

> AI is used for extraction and structuring, not for uncontrolled execution. The deterministic fallback and DSL validator make the system runnable and inspectable even without an LLM call.
