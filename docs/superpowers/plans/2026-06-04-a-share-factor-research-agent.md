# A-Share Factor Research Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an A-share factor research agent that extracts factor ideas from public or uploaded research materials, converts them into a safe Factor DSL, validates them on A-share daily data, and produces traceable research reports.

**Architecture:** The system starts with deterministic, testable quant modules, then layers document/RAG extraction, then wraps the workflow in LangGraph and FastAPI. LLM outputs are constrained to structured schemas and a restricted Factor DSL; all calculations and backtests are executed by deterministic Python code.

**Tech Stack:** Python, FastAPI, Pydantic, Pandas, NumPy, AKShare, LangGraph, OpenAI-compatible LLM client, Chroma or FAISS, pytest, SQLite.

---

## File Structure

Create a new project directory at:

```text
/Users/brain6/Documents/document/A-Share Factor Research Agent
```

Target structure:

```text
./
  app/
    __init__.py
    main.py
    config.py
    api/
      __init__.py
      research.py
      documents.py
      runs.py
    agents/
      __init__.py
      graph.py
      state.py
      prompts.py
      schemas.py
    llm/
      __init__.py
      client.py
    sources/
      __init__.py
      parser.py
      source_policy.py
    rag/
      __init__.py
      chunker.py
      retriever.py
    factor/
      __init__.py
      dsl.py
      validator.py
      operators.py
      executor.py
      preprocessing.py
    data/
      __init__.py
      ashare_provider.py
      fixture_provider.py
    backtest/
      __init__.py
      metrics.py
      single_factor.py
      selector.py
    reports/
      __init__.py
      markdown_report.py
    storage/
      __init__.py
      db.py
      models.py
    evals/
      tasks.jsonl
      run_eval.py
    tests/
      test_factor_dsl.py
      test_factor_operators.py
      test_metrics.py
      test_selector.py
      test_source_policy.py
      test_report.py
    README.md
    REPORT.md
    pyproject.toml
    .env.example
```

## Task 1: Project Scaffold

**Files:**
- Create: `/Users/brain6/Documents/document/A-Share Factor Research Agent/pyproject.toml`
- Create: `/Users/brain6/Documents/document/A-Share Factor Research Agent/.env.example`
- Create: `/Users/brain6/Documents/document/A-Share Factor Research Agent/README.md`
- Create package `__init__.py` files listed above.

- [ ] **Step 1: Create project folders**

Run:

```bash
mkdir -p /Users/brain6/Documents/document/A-Share Factor Research Agent/app/{api,agents,llm,sources,rag,factor,data,backtest,reports,storage}
mkdir -p /Users/brain6/Documents/document/A-Share Factor Research Agent/{evals,tests}
```

Expected: folders exist.

- [ ] **Step 2: Add package markers**

Run:

```bash
touch /Users/brain6/Documents/document/A-Share Factor Research Agent/app/__init__.py
touch /Users/brain6/Documents/document/A-Share Factor Research Agent/app/api/__init__.py
touch /Users/brain6/Documents/document/A-Share Factor Research Agent/app/agents/__init__.py
touch /Users/brain6/Documents/document/A-Share Factor Research Agent/app/llm/__init__.py
touch /Users/brain6/Documents/document/A-Share Factor Research Agent/app/sources/__init__.py
touch /Users/brain6/Documents/document/A-Share Factor Research Agent/app/rag/__init__.py
touch /Users/brain6/Documents/document/A-Share Factor Research Agent/app/factor/__init__.py
touch /Users/brain6/Documents/document/A-Share Factor Research Agent/app/data/__init__.py
touch /Users/brain6/Documents/document/A-Share Factor Research Agent/app/backtest/__init__.py
touch /Users/brain6/Documents/document/A-Share Factor Research Agent/app/reports/__init__.py
touch /Users/brain6/Documents/document/A-Share Factor Research Agent/app/storage/__init__.py
```

Expected: Python packages import cleanly.

- [ ] **Step 3: Create `pyproject.toml`**

Write:

```toml
[project]
name = "A-Share Factor Research Agent"
version = "0.1.0"
description = "A-share factor research agent for extracting, validating, and backtesting factor hypotheses."
requires-python = ">=3.11"
dependencies = [
  "fastapi",
  "uvicorn",
  "pydantic",
  "pydantic-settings",
  "python-dotenv",
  "pandas",
  "numpy",
  "scipy",
  "akshare",
  "openai",
  "langgraph",
  "chromadb",
  "sentence-transformers",
  "pypdf",
  "markdown",
  "beautifulsoup4",
  "requests",
  "matplotlib",
]

[project.optional-dependencies]
dev = ["pytest", "pytest-cov", "ruff"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]

[tool.ruff]
line-length = 100
```

- [ ] **Step 4: Create `.env.example`**

Write:

```bash
OPENAI_API_KEY=
LLM_MODEL=gpt-5.2
DATA_PROVIDER=fixture
DATABASE_URL=sqlite:///./runs.db
```

- [ ] **Step 5: Create initial `README.md`**

Write:

```markdown
# A-Share Factor Research Agent

An A-share factor research agent for quant strategy research workflows.

The system extracts factor hypotheses from public research materials or uploaded documents,
converts them into a restricted Factor DSL, validates factors with A-share daily data,
and generates traceable research reports.

This project is a research assistant. It does not provide investment advice,
stock recommendations, or trading execution.

## MVP Scope

- A-share daily data
- CSI 300 or fixed sample universe
- Public or uploaded research materials
- Momentum, reversal, volatility, and volume-price factors
- IC, RankIC, ICIR, grouped returns, long-short backtest
- LangGraph workflow and FastAPI API
```

- [ ] **Step 6: Verify package imports**

Run:

```bash
cd /Users/brain6/Documents/document/A-Share Factor Research Agent
python - <<'PY'
import app
print("ok")
PY
```

Expected:

```text
ok
```

## Task 2: Configuration

**Files:**
- Create: `/Users/brain6/Documents/document/A-Share Factor Research Agent/app/config.py`
- Test manually with a one-line Python command.

- [ ] **Step 1: Implement settings**

Write `app/config.py`:

```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openai_api_key: str = ""
    llm_model: str = "gpt-5.2"
    data_provider: str = "fixture"
    database_url: str = "sqlite:///./runs.db"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 2: Verify default settings**

Run:

```bash
cd /Users/brain6/Documents/document/A-Share Factor Research Agent
python - <<'PY'
from app.config import get_settings
s = get_settings()
assert s.llm_model
assert s.data_provider == "fixture"
print(s.data_provider)
PY
```

Expected:

```text
fixture
```

## Task 3: Source Policy

**Files:**
- Create: `/Users/brain6/Documents/document/A-Share Factor Research Agent/app/sources/source_policy.py`
- Test: `/Users/brain6/Documents/document/A-Share Factor Research Agent/tests/test_source_policy.py`

- [ ] **Step 1: Write failing tests**

Write `tests/test_source_policy.py`:

```python
from app.sources.source_policy import SourcePolicy


def test_allows_public_pdf_url():
    policy = SourcePolicy()
    result = policy.check_url("https://example.com/reports/factor.pdf")
    assert result.allowed is True
    assert result.reason == "public_url_allowed"


def test_rejects_cnki_url():
    policy = SourcePolicy()
    result = policy.check_url("https://kns.cnki.net/kcms/detail/detail.aspx?id=123")
    assert result.allowed is False
    assert result.reason == "blocked_domain"


def test_rejects_login_required_hint():
    policy = SourcePolicy()
    result = policy.check_url("https://broker.example.com/login/report/123")
    assert result.allowed is False
    assert result.reason == "login_required_hint"
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
cd /Users/brain6/Documents/document/A-Share Factor Research Agent
pytest tests/test_source_policy.py -v
```

Expected: FAIL because `app.sources.source_policy` does not exist.

- [ ] **Step 3: Implement source policy**

Write `app/sources/source_policy.py`:

```python
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class SourcePolicyResult:
    allowed: bool
    reason: str


class SourcePolicy:
    blocked_domains = {
        "cnki.net",
        "kns.cnki.net",
        "wind.com.cn",
        "choice.eastmoney.com",
    }

    login_hints = ("/login", "login", "signin", "auth", "passport")

    def check_url(self, url: str) -> SourcePolicyResult:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        path = parsed.path.lower()
        normalized = f"{hostname}{path}".lower()

        if any(hostname.endswith(domain) for domain in self.blocked_domains):
            return SourcePolicyResult(False, "blocked_domain")

        if any(hint in normalized for hint in self.login_hints):
            return SourcePolicyResult(False, "login_required_hint")

        if parsed.scheme not in {"http", "https"}:
            return SourcePolicyResult(False, "unsupported_scheme")

        return SourcePolicyResult(True, "public_url_allowed")
```

- [ ] **Step 4: Run test to verify pass**

Run:

```bash
cd /Users/brain6/Documents/document/A-Share Factor Research Agent
pytest tests/test_source_policy.py -v
```

Expected: all tests PASS.

## Task 4: Factor DSL Models and Validator

**Files:**
- Create: `/Users/brain6/Documents/document/A-Share Factor Research Agent/app/factor/dsl.py`
- Create: `/Users/brain6/Documents/document/A-Share Factor Research Agent/app/factor/validator.py`
- Test: `/Users/brain6/Documents/document/A-Share Factor Research Agent/tests/test_factor_dsl.py`

- [ ] **Step 1: Write failing tests**

Write `tests/test_factor_dsl.py`:

```python
import pytest

from app.factor.dsl import FactorSpec
from app.factor.validator import FactorDslValidator


def test_valid_formula_passes():
    spec = FactorSpec(
        factor_name="momentum_20",
        hypothesis="过去20日收益率较高的股票可能延续上涨。",
        formula="rank(returns(close, 20))",
        required_fields=["close"],
        direction="positive",
        category="momentum",
        frequency="daily",
        lookback=20,
        source_title="example report",
        source_url="https://example.com/report.pdf",
        source_excerpt="过去20日收益率可衡量短期动量。",
        confidence=0.8,
    )
    result = FactorDslValidator().validate(spec)
    assert result.valid is True
    assert result.errors == []


def test_unknown_operator_fails():
    spec = FactorSpec(
        factor_name="bad_factor",
        hypothesis="bad",
        formula="evil(close, 20)",
        required_fields=["close"],
        direction="positive",
        category="momentum",
        frequency="daily",
        lookback=20,
        source_title="example report",
        source_url=None,
        source_excerpt="bad",
        confidence=0.1,
    )
    result = FactorDslValidator().validate(spec)
    assert result.valid is False
    assert "unknown_operator:evil" in result.errors


def test_malicious_formula_fails():
    spec = FactorSpec(
        factor_name="malicious",
        hypothesis="bad",
        formula="__import__('os').system('rm -rf /')",
        required_fields=["close"],
        direction="positive",
        category="momentum",
        frequency="daily",
        lookback=20,
        source_title="example report",
        source_url=None,
        source_excerpt="bad",
        confidence=0.1,
    )
    result = FactorDslValidator().validate(spec)
    assert result.valid is False
    assert "unsafe_token" in result.errors
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
cd /Users/brain6/Documents/document/A-Share Factor Research Agent
pytest tests/test_factor_dsl.py -v
```

Expected: FAIL because modules do not exist.

- [ ] **Step 3: Implement `FactorSpec`**

Write `app/factor/dsl.py`:

```python
from typing import Literal

from pydantic import BaseModel, Field


Direction = Literal["positive", "negative", "unknown"]


class FactorSpec(BaseModel):
    factor_name: str
    hypothesis: str
    formula: str
    required_fields: list[str]
    direction: Direction
    category: str
    frequency: Literal["daily"] = "daily"
    lookback: int = Field(ge=1)
    source_title: str
    source_url: str | None = None
    source_excerpt: str
    confidence: float = Field(ge=0.0, le=1.0)
```

- [ ] **Step 4: Implement validator**

Write `app/factor/validator.py`:

```python
import ast
from dataclasses import dataclass

from app.factor.dsl import FactorSpec


@dataclass(frozen=True)
class FactorDslValidationResult:
    valid: bool
    errors: list[str]


class FactorDslValidator:
    allowed_fields = {"open", "high", "low", "close", "volume", "amount"}
    allowed_operators = {
        "returns",
        "delay",
        "ts_mean",
        "ts_std",
        "ts_min",
        "ts_max",
        "rank",
        "zscore",
        "winsorize",
        "neutralize",
    }
    unsafe_tokens = {"__", "import", "exec", "eval", "open(", "system", "subprocess"}

    def validate(self, spec: FactorSpec) -> FactorDslValidationResult:
        errors: list[str] = []
        formula = spec.formula

        if any(token in formula for token in self.unsafe_tokens):
            errors.append("unsafe_token")
            return FactorDslValidationResult(False, errors)

        for field in spec.required_fields:
            if field not in self.allowed_fields:
                errors.append(f"unknown_field:{field}")

        try:
            tree = ast.parse(formula, mode="eval")
        except SyntaxError:
            errors.append("syntax_error")
            return FactorDslValidationResult(False, errors)

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if not isinstance(node.func, ast.Name):
                    errors.append("unsafe_call")
                    continue
                name = node.func.id
                if name not in self.allowed_operators:
                    errors.append(f"unknown_operator:{name}")
            elif isinstance(node, ast.Name):
                if node.id not in self.allowed_fields and node.id not in self.allowed_operators:
                    errors.append(f"unknown_name:{node.id}")
            elif isinstance(node, ast.Attribute):
                errors.append("attribute_access_forbidden")

        deduped = sorted(set(errors))
        return FactorDslValidationResult(valid=not deduped, errors=deduped)
```

- [ ] **Step 5: Run test to verify pass**

Run:

```bash
cd /Users/brain6/Documents/document/A-Share Factor Research Agent
pytest tests/test_factor_dsl.py -v
```

Expected: all tests PASS.

## Task 5: Factor Operators

**Files:**
- Create: `/Users/brain6/Documents/document/A-Share Factor Research Agent/app/factor/operators.py`
- Test: `/Users/brain6/Documents/document/A-Share Factor Research Agent/tests/test_factor_operators.py`

- [ ] **Step 1: Write failing tests**

Write `tests/test_factor_operators.py`:

```python
import pandas as pd

from app.factor.operators import returns, ts_mean, ts_std, rank, zscore


def test_returns_calculates_pct_change_by_symbol():
    idx = pd.MultiIndex.from_product(
        [["000001", "000002"], pd.date_range("2024-01-01", periods=3)],
        names=["symbol", "date"],
    )
    close = pd.Series([10, 11, 12, 20, 18, 22], index=idx, name="close")
    result = returns(close, 1)
    assert round(result.loc[("000001", pd.Timestamp("2024-01-02"))], 6) == 0.1
    assert round(result.loc[("000002", pd.Timestamp("2024-01-02"))], 6) == -0.1


def test_cross_sectional_rank_by_date():
    idx = pd.MultiIndex.from_tuples(
        [
            ("000001", pd.Timestamp("2024-01-01")),
            ("000002", pd.Timestamp("2024-01-01")),
            ("000003", pd.Timestamp("2024-01-01")),
        ],
        names=["symbol", "date"],
    )
    values = pd.Series([1.0, 3.0, 2.0], index=idx)
    result = rank(values)
    assert result.loc[("000001", pd.Timestamp("2024-01-01"))] == 1 / 3
    assert result.loc[("000003", pd.Timestamp("2024-01-01"))] == 2 / 3
    assert result.loc[("000002", pd.Timestamp("2024-01-01"))] == 1.0


def test_zscore_by_date_has_zero_mean():
    idx = pd.MultiIndex.from_tuples(
        [
            ("000001", pd.Timestamp("2024-01-01")),
            ("000002", pd.Timestamp("2024-01-01")),
            ("000003", pd.Timestamp("2024-01-01")),
        ],
        names=["symbol", "date"],
    )
    values = pd.Series([1.0, 2.0, 3.0], index=idx)
    result = zscore(values)
    assert round(result.groupby(level="date").mean().iloc[0], 8) == 0
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
cd /Users/brain6/Documents/document/A-Share Factor Research Agent
pytest tests/test_factor_operators.py -v
```

Expected: FAIL because operators do not exist.

- [ ] **Step 3: Implement operators**

Write `app/factor/operators.py`:

```python
import pandas as pd


def _by_symbol(series: pd.Series):
    return series.groupby(level="symbol", group_keys=False)


def _by_date(series: pd.Series):
    return series.groupby(level="date", group_keys=False)


def returns(x: pd.Series, window: int) -> pd.Series:
    return _by_symbol(x).pct_change(window)


def delay(x: pd.Series, window: int) -> pd.Series:
    return _by_symbol(x).shift(window)


def ts_mean(x: pd.Series, window: int) -> pd.Series:
    return _by_symbol(x).rolling(window).mean().droplevel(0)


def ts_std(x: pd.Series, window: int) -> pd.Series:
    return _by_symbol(x).rolling(window).std().droplevel(0)


def ts_min(x: pd.Series, window: int) -> pd.Series:
    return _by_symbol(x).rolling(window).min().droplevel(0)


def ts_max(x: pd.Series, window: int) -> pd.Series:
    return _by_symbol(x).rolling(window).max().droplevel(0)


def rank(x: pd.Series) -> pd.Series:
    return _by_date(x).rank(pct=True)


def zscore(x: pd.Series) -> pd.Series:
    mean = _by_date(x).transform("mean")
    std = _by_date(x).transform("std").replace(0, pd.NA)
    return (x - mean) / std


def winsorize(x: pd.Series, lower: float = 0.01, upper: float = 0.99) -> pd.Series:
    low = _by_date(x).transform(lambda s: s.quantile(lower))
    high = _by_date(x).transform(lambda s: s.quantile(upper))
    return x.clip(lower=low, upper=high)


def neutralize(x: pd.Series, by: pd.Series) -> pd.Series:
    # MVP neutralization: subtract each group's cross-sectional mean by date.
    df = pd.DataFrame({"x": x, "by": by})
    group_mean = df.groupby(["date", "by"])["x"].transform("mean")
    return df["x"] - group_mean
```

- [ ] **Step 4: Run test to verify pass**

Run:

```bash
cd /Users/brain6/Documents/document/A-Share Factor Research Agent
pytest tests/test_factor_operators.py -v
```

Expected: all tests PASS.

## Task 6: Factor Executor

**Files:**
- Create: `/Users/brain6/Documents/document/A-Share Factor Research Agent/app/factor/executor.py`
- Test: extend `/Users/brain6/Documents/document/A-Share Factor Research Agent/tests/test_factor_dsl.py`

- [ ] **Step 1: Add executor test**

Append to `tests/test_factor_dsl.py`:

```python
import pandas as pd

from app.factor.executor import FactorExecutor


def test_executor_computes_valid_formula():
    idx = pd.MultiIndex.from_product(
        [["000001", "000002"], pd.date_range("2024-01-01", periods=25)],
        names=["symbol", "date"],
    )
    data = pd.DataFrame(index=idx)
    data["close"] = list(range(1, 26)) + list(range(2, 27))

    spec = FactorSpec(
        factor_name="momentum_20",
        hypothesis="过去20日收益率较高的股票可能延续上涨。",
        formula="rank(returns(close, 20))",
        required_fields=["close"],
        direction="positive",
        category="momentum",
        frequency="daily",
        lookback=20,
        source_title="example report",
        source_url=None,
        source_excerpt="example",
        confidence=0.8,
    )

    result = FactorExecutor().execute(spec, data)
    assert result.name == "momentum_20"
    assert not result.values.dropna().empty
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
cd /Users/brain6/Documents/document/A-Share Factor Research Agent
pytest tests/test_factor_dsl.py::test_executor_computes_valid_formula -v
```

Expected: FAIL because `FactorExecutor` does not exist.

- [ ] **Step 3: Implement executor**

Write `app/factor/executor.py`:

```python
from dataclasses import dataclass

import pandas as pd

from app.factor import operators
from app.factor.dsl import FactorSpec
from app.factor.validator import FactorDslValidator


@dataclass(frozen=True)
class FactorExecutionResult:
    name: str
    values: pd.Series


class FactorExecutor:
    def __init__(self) -> None:
        self.validator = FactorDslValidator()

    def execute(self, spec: FactorSpec, data: pd.DataFrame) -> FactorExecutionResult:
        validation = self.validator.validate(spec)
        if not validation.valid:
            raise ValueError(f"Invalid factor formula: {validation.errors}")

        env = {
            "returns": operators.returns,
            "delay": operators.delay,
            "ts_mean": operators.ts_mean,
            "ts_std": operators.ts_std,
            "ts_min": operators.ts_min,
            "ts_max": operators.ts_max,
            "rank": operators.rank,
            "zscore": operators.zscore,
            "winsorize": operators.winsorize,
            "neutralize": operators.neutralize,
        }
        for field in FactorDslValidator.allowed_fields:
            if field in data.columns:
                env[field] = data[field]

        values = eval(spec.formula, {"__builtins__": {}}, env)
        if not isinstance(values, pd.Series):
            raise TypeError("Factor formula must return a pandas Series")
        values.name = spec.factor_name
        return FactorExecutionResult(spec.factor_name, values)
```

- [ ] **Step 4: Run test to verify pass**

Run:

```bash
cd /Users/brain6/Documents/document/A-Share Factor Research Agent
pytest tests/test_factor_dsl.py -v
```

Expected: all tests PASS.

## Task 7: Backtest Metrics

**Files:**
- Create: `/Users/brain6/Documents/document/A-Share Factor Research Agent/app/backtest/metrics.py`
- Test: `/Users/brain6/Documents/document/A-Share Factor Research Agent/tests/test_metrics.py`

- [ ] **Step 1: Write failing tests**

Write `tests/test_metrics.py`:

```python
import pandas as pd

from app.backtest.metrics import max_drawdown, sharpe_ratio, annualized_return


def test_annualized_return_positive_series():
    returns = pd.Series([0.01] * 252)
    result = annualized_return(returns)
    assert result > 0


def test_max_drawdown_detects_drop():
    returns = pd.Series([0.1, -0.5, 0.1])
    result = max_drawdown(returns)
    assert result < 0


def test_sharpe_ratio_zero_for_flat_returns():
    returns = pd.Series([0.0] * 252)
    result = sharpe_ratio(returns)
    assert result == 0.0
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
cd /Users/brain6/Documents/document/A-Share Factor Research Agent
pytest tests/test_metrics.py -v
```

Expected: FAIL because metrics module does not exist.

- [ ] **Step 3: Implement metrics**

Write `app/backtest/metrics.py`:

```python
import numpy as np
import pandas as pd


def annualized_return(returns: pd.Series, periods_per_year: int = 252) -> float:
    clean = returns.dropna()
    if clean.empty:
        return 0.0
    total = float((1 + clean).prod())
    years = len(clean) / periods_per_year
    if years <= 0:
        return 0.0
    return total ** (1 / years) - 1


def max_drawdown(returns: pd.Series) -> float:
    clean = returns.fillna(0)
    wealth = (1 + clean).cumprod()
    peak = wealth.cummax()
    drawdown = wealth / peak - 1
    return float(drawdown.min())


def sharpe_ratio(returns: pd.Series, periods_per_year: int = 252) -> float:
    clean = returns.dropna()
    if clean.empty:
        return 0.0
    std = clean.std()
    if std == 0 or np.isnan(std):
        return 0.0
    return float(clean.mean() / std * np.sqrt(periods_per_year))
```

- [ ] **Step 4: Run test to verify pass**

Run:

```bash
cd /Users/brain6/Documents/document/A-Share Factor Research Agent
pytest tests/test_metrics.py -v
```

Expected: all tests PASS.

## Task 8: Single-Factor Validation and Backtest

**Files:**
- Create: `/Users/brain6/Documents/document/A-Share Factor Research Agent/app/backtest/single_factor.py`
- Test: extend `/Users/brain6/Documents/document/A-Share Factor Research Agent/tests/test_metrics.py`

- [ ] **Step 1: Add validation tests**

Append to `tests/test_metrics.py`:

```python
import numpy as np

from app.backtest.single_factor import compute_rank_ic, grouped_forward_returns


def test_compute_rank_ic_returns_series_by_date():
    idx = pd.MultiIndex.from_product(
        [["000001", "000002", "000003"], pd.date_range("2024-01-01", periods=3)],
        names=["symbol", "date"],
    )
    factor = pd.Series(np.arange(len(idx)), index=idx)
    forward_returns = pd.Series(np.arange(len(idx)), index=idx)
    result = compute_rank_ic(factor, forward_returns)
    assert len(result) == 3
    assert result.dropna().iloc[0] == 1.0


def test_grouped_forward_returns_outputs_groups():
    idx = pd.MultiIndex.from_product(
        [["000001", "000002", "000003", "000004", "000005"], [pd.Timestamp("2024-01-01")]],
        names=["symbol", "date"],
    )
    factor = pd.Series([1, 2, 3, 4, 5], index=idx)
    forward_returns = pd.Series([0.01, 0.02, 0.03, 0.04, 0.05], index=idx)
    result = grouped_forward_returns(factor, forward_returns, groups=5)
    assert set(result.columns) == {1, 2, 3, 4, 5}
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
cd /Users/brain6/Documents/document/A-Share Factor Research Agent
pytest tests/test_metrics.py::test_compute_rank_ic_returns_series_by_date -v
```

Expected: FAIL because functions do not exist.

- [ ] **Step 3: Implement single-factor utilities**

Write `app/backtest/single_factor.py`:

```python
import pandas as pd


def compute_forward_returns(close: pd.Series, periods: int = 1) -> pd.Series:
    return close.groupby(level="symbol", group_keys=False).pct_change(periods).shift(-periods)


def compute_rank_ic(factor: pd.Series, forward_returns: pd.Series) -> pd.Series:
    df = pd.DataFrame({"factor": factor, "forward_returns": forward_returns}).dropna()
    return df.groupby(level="date").apply(
        lambda x: x["factor"].rank().corr(x["forward_returns"].rank())
    )


def compute_ic(factor: pd.Series, forward_returns: pd.Series) -> pd.Series:
    df = pd.DataFrame({"factor": factor, "forward_returns": forward_returns}).dropna()
    return df.groupby(level="date").apply(lambda x: x["factor"].corr(x["forward_returns"]))


def grouped_forward_returns(
    factor: pd.Series,
    forward_returns: pd.Series,
    groups: int = 5,
) -> pd.DataFrame:
    df = pd.DataFrame({"factor": factor, "forward_returns": forward_returns}).dropna()

    def assign_group(x: pd.Series) -> pd.Series:
        return pd.qcut(x.rank(method="first"), groups, labels=range(1, groups + 1)).astype(int)

    df["group"] = df.groupby(level="date")["factor"].transform(assign_group)
    grouped = df.groupby([df.index.get_level_values("date"), "group"])["forward_returns"].mean()
    return grouped.unstack("group")
```

- [ ] **Step 4: Run tests**

Run:

```bash
cd /Users/brain6/Documents/document/A-Share Factor Research Agent
pytest tests/test_metrics.py -v
```

Expected: all tests PASS.

## Task 9: Factor Selector

**Files:**
- Create: `/Users/brain6/Documents/document/A-Share Factor Research Agent/app/backtest/selector.py`
- Test: `/Users/brain6/Documents/document/A-Share Factor Research Agent/tests/test_selector.py`

- [ ] **Step 1: Write failing tests**

Write `tests/test_selector.py`:

```python
from app.backtest.selector import FactorScore, FactorSelector


def test_selector_accepts_stable_factor():
    scores = [
        FactorScore(
            factor_name="momentum_20",
            mean_rank_ic=0.04,
            icir=0.6,
            coverage_ratio=0.9,
            missing_ratio=0.1,
            max_drawdown=-0.12,
        )
    ]
    selected = FactorSelector().select(scores)
    assert [x.factor_name for x in selected] == ["momentum_20"]


def test_selector_rejects_low_coverage_factor():
    scores = [
        FactorScore(
            factor_name="bad_factor",
            mean_rank_ic=0.08,
            icir=1.0,
            coverage_ratio=0.5,
            missing_ratio=0.5,
            max_drawdown=-0.12,
        )
    ]
    selected = FactorSelector().select(scores)
    assert selected == []
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
cd /Users/brain6/Documents/document/A-Share Factor Research Agent
pytest tests/test_selector.py -v
```

Expected: FAIL because selector module does not exist.

- [ ] **Step 3: Implement selector**

Write `app/backtest/selector.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class FactorScore:
    factor_name: str
    mean_rank_ic: float
    icir: float
    coverage_ratio: float
    missing_ratio: float
    max_drawdown: float


class FactorSelector:
    def __init__(
        self,
        min_abs_rank_ic: float = 0.02,
        min_abs_icir: float = 0.3,
        min_coverage: float = 0.8,
        max_missing: float = 0.2,
        max_drawdown_limit: float = -0.5,
    ) -> None:
        self.min_abs_rank_ic = min_abs_rank_ic
        self.min_abs_icir = min_abs_icir
        self.min_coverage = min_coverage
        self.max_missing = max_missing
        self.max_drawdown_limit = max_drawdown_limit

    def select(self, scores: list[FactorScore]) -> list[FactorScore]:
        selected: list[FactorScore] = []
        for score in scores:
            if abs(score.mean_rank_ic) < self.min_abs_rank_ic:
                continue
            if abs(score.icir) < self.min_abs_icir:
                continue
            if score.coverage_ratio < self.min_coverage:
                continue
            if score.missing_ratio > self.max_missing:
                continue
            if score.max_drawdown < self.max_drawdown_limit:
                continue
            selected.append(score)
        return selected
```

- [ ] **Step 4: Run test to verify pass**

Run:

```bash
cd /Users/brain6/Documents/document/A-Share Factor Research Agent
pytest tests/test_selector.py -v
```

Expected: all tests PASS.

## Task 10: Fixture Data Provider

**Files:**
- Create: `/Users/brain6/Documents/document/A-Share Factor Research Agent/app/data/fixture_provider.py`
- Test manually with a Python command.

- [ ] **Step 1: Implement deterministic fixture provider**

Write `app/data/fixture_provider.py`:

```python
import numpy as np
import pandas as pd


class FixtureAshareDataProvider:
    def get_universe(self, universe_name: str, date: str) -> list[str]:
        return [f"{i:06d}" for i in range(1, 51)]

    def get_daily_bars(
        self,
        symbols: list[str],
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        dates = pd.date_range(start_date, end_date, freq="B")
        idx = pd.MultiIndex.from_product([symbols, dates], names=["symbol", "date"])
        rng = np.random.default_rng(42)
        df = pd.DataFrame(index=idx)
        base = rng.normal(0, 0.01, size=len(idx))
        df["close"] = 100 * (1 + pd.Series(base, index=idx).groupby(level="symbol").cumsum())
        df["open"] = df["close"] * (1 + rng.normal(0, 0.002, size=len(idx)))
        df["high"] = df[["open", "close"]].max(axis=1) * 1.01
        df["low"] = df[["open", "close"]].min(axis=1) * 0.99
        df["volume"] = rng.integers(100_000, 2_000_000, size=len(idx))
        df["amount"] = df["close"] * df["volume"]
        return df
```

- [ ] **Step 2: Verify provider**

Run:

```bash
cd /Users/brain6/Documents/document/A-Share Factor Research Agent
python - <<'PY'
from app.data.fixture_provider import FixtureAshareDataProvider
p = FixtureAshareDataProvider()
symbols = p.get_universe("CSI300", "2024-01-01")[:3]
df = p.get_daily_bars(symbols, "2024-01-01", "2024-01-10")
assert {"open", "high", "low", "close", "volume", "amount"}.issubset(df.columns)
print(df.shape)
PY
```

Expected: shape prints with rows > 0.

## Task 11: AKShare Provider Adapter

**Files:**
- Create: `/Users/brain6/Documents/document/A-Share Factor Research Agent/app/data/ashare_provider.py`

- [ ] **Step 1: Implement adapter skeleton**

Write `app/data/ashare_provider.py`:

```python
import pandas as pd


class AkshareAshareDataProvider:
    def get_universe(self, universe_name: str, date: str) -> list[str]:
        # MVP fallback: use a small fixed liquid stock sample.
        # Later this can be replaced by CSI 300 constituent data.
        return ["000001", "000002", "600000", "600519", "300750"]

    def get_daily_bars(
        self,
        symbols: list[str],
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        import akshare as ak

        frames = []
        for symbol in symbols:
            raw = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date.replace("-", ""),
                end_date=end_date.replace("-", ""),
                adjust="qfq",
            )
            if raw.empty:
                continue
            frame = raw.rename(
                columns={
                    "日期": "date",
                    "开盘": "open",
                    "收盘": "close",
                    "最高": "high",
                    "最低": "low",
                    "成交量": "volume",
                    "成交额": "amount",
                }
            )
            frame["symbol"] = symbol
            frame["date"] = pd.to_datetime(frame["date"])
            frames.append(frame[["symbol", "date", "open", "high", "low", "close", "volume", "amount"]])

        if not frames:
            return pd.DataFrame(
                columns=["open", "high", "low", "close", "volume", "amount"],
                index=pd.MultiIndex.from_arrays([[], []], names=["symbol", "date"]),
            )

        result = pd.concat(frames).set_index(["symbol", "date"]).sort_index()
        return result
```

- [ ] **Step 2: Do not require live AKShare in tests**

No pytest test is required for live AKShare because external data may be slow or unavailable. Use the fixture provider for deterministic tests.

## Task 12: Document Parser and Chunker

**Files:**
- Create: `/Users/brain6/Documents/document/A-Share Factor Research Agent/app/sources/parser.py`
- Create: `/Users/brain6/Documents/document/A-Share Factor Research Agent/app/rag/chunker.py`

- [ ] **Step 1: Implement parser**

Write `app/sources/parser.py`:

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ParsedDocument:
    source_title: str
    source_type: str
    text: str
    source_url: str | None = None


class DocumentParser:
    def parse_file(self, path: str) -> ParsedDocument:
        file_path = Path(path)
        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            return self._parse_pdf(file_path)
        if suffix in {".md", ".txt"}:
            return ParsedDocument(
                source_title=file_path.name,
                source_type="user_upload",
                text=file_path.read_text(encoding="utf-8"),
            )
        raise ValueError(f"Unsupported file type: {suffix}")

    def _parse_pdf(self, path: Path) -> ParsedDocument:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        return ParsedDocument(
            source_title=path.name,
            source_type="user_upload",
            text="\n".join(pages),
        )
```

- [ ] **Step 2: Implement chunker**

Write `app/rag/chunker.py`:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentChunk:
    chunk_id: str
    source_title: str
    source_type: str
    text: str
    source_url: str | None = None


class SimpleChunker:
    def __init__(self, chunk_size: int = 800, overlap: int = 120) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, source_title: str, source_type: str, text: str, source_url: str | None = None) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        start = 0
        index = 0
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            piece = text[start:end].strip()
            if piece:
                chunks.append(
                    DocumentChunk(
                        chunk_id=f"{source_title}:{index}",
                        source_title=source_title,
                        source_type=source_type,
                        source_url=source_url,
                        text=piece,
                    )
                )
            if end == len(text):
                break
            start = max(0, end - self.overlap)
            index += 1
        return chunks
```

- [ ] **Step 3: Verify parser and chunker manually**

Run:

```bash
cd /Users/brain6/Documents/document/A-Share Factor Research Agent
python - <<'PY'
from app.rag.chunker import SimpleChunker
chunks = SimpleChunker(chunk_size=20, overlap=5).chunk("demo.md", "user_upload", "A股量价因子研究。" * 10)
assert len(chunks) > 1
print(len(chunks))
PY
```

Expected: chunk count > 1.

## Task 13: LLM Client

**Files:**
- Create: `/Users/brain6/Documents/document/A-Share Factor Research Agent/app/llm/client.py`

- [ ] **Step 1: Implement minimal OpenAI-compatible client**

Write `app/llm/client.py`:

```python
import json
from typing import Any

from openai import OpenAI

from app.config import get_settings


class LlmClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.client = OpenAI(api_key=self.settings.openai_api_key or None)

    def text(self, prompt: str) -> str:
        response = self.client.responses.create(
            model=self.settings.llm_model,
            input=prompt,
        )
        return response.output_text

    def json(self, prompt: str) -> dict[str, Any]:
        response = self.client.responses.create(
            model=self.settings.llm_model,
            input=prompt,
        )
        text = response.output_text
        return json.loads(text)
```

- [ ] **Step 2: Keep live LLM calls out of unit tests**

Do not add pytest tests that require API keys. Integration tests can be added later behind an environment flag.

## Task 14: Agent Schemas and Prompts

**Files:**
- Create: `/Users/brain6/Documents/document/A-Share Factor Research Agent/app/agents/schemas.py`
- Create: `/Users/brain6/Documents/document/A-Share Factor Research Agent/app/agents/prompts.py`

- [ ] **Step 1: Implement schemas**

Write `app/agents/schemas.py`:

```python
from pydantic import BaseModel, Field


class FactorHypothesis(BaseModel):
    factor_name: str
    hypothesis: str
    evidence: str
    source_title: str
    source_url: str | None = None
    category: str
    required_fields: list[str]
    confidence: float = Field(ge=0.0, le=1.0)
```

- [ ] **Step 2: Implement prompts**

Write `app/agents/prompts.py`:

```python
FACTOR_EXTRACTION_PROMPT = """
You are a quant research assistant for A-share factor research.

Extract candidate factor hypotheses from the provided research chunks.
Only extract hypotheses that can be tested with daily OHLCV data:
open, high, low, close, volume, amount.

Return JSON only:
{
  "factors": [
    {
      "factor_name": "snake_case_name",
      "hypothesis": "Chinese hypothesis",
      "evidence": "short source excerpt",
      "source_title": "source title",
      "source_url": null,
      "category": "momentum | reversal | volatility | volume_price",
      "required_fields": ["close"],
      "confidence": 0.0
    }
  ]
}

Research topic:
{research_topic}

Chunks:
{chunks}
"""

FACTOR_DSL_PROMPT = """
Convert the factor hypothesis into the restricted Factor DSL.

Allowed fields:
open, high, low, close, volume, amount

Allowed operators:
returns(x, window), delay(x, window), ts_mean(x, window), ts_std(x, window),
ts_min(x, window), ts_max(x, window), rank(x), zscore(x), winsorize(x)

Return JSON only:
{
  "factor_name": "snake_case_name",
  "hypothesis": "...",
  "formula": "rank(returns(close, 20))",
  "required_fields": ["close"],
  "direction": "positive | negative | unknown",
  "category": "momentum",
  "frequency": "daily",
  "lookback": 20,
  "source_title": "...",
  "source_url": null,
  "source_excerpt": "...",
  "confidence": 0.8
}

Hypothesis:
{hypothesis}
"""
```

## Task 15: Report Generator

**Files:**
- Create: `/Users/brain6/Documents/document/A-Share Factor Research Agent/app/reports/markdown_report.py`
- Test: `/Users/brain6/Documents/document/A-Share Factor Research Agent/tests/test_report.py`

- [ ] **Step 1: Write failing test**

Write `tests/test_report.py`:

```python
from app.reports.markdown_report import render_report


def test_report_contains_disclaimer_and_sections():
    report = render_report(
        research_topic="A股量价类动量因子",
        sources=[{"source_title": "demo report", "source_url": "https://example.com"}],
        factors=[{"factor_name": "momentum_20", "formula": "rank(returns(close, 20))"}],
        metrics=[{"factor_name": "momentum_20", "mean_rank_ic": 0.04, "icir": 0.6}],
        limitations=["fixture data only"],
    )
    assert "A股量价类动量因子" in report
    assert "历史回测不构成投资建议" in report
    assert "momentum_20" in report
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
cd /Users/brain6/Documents/document/A-Share Factor Research Agent
pytest tests/test_report.py -v
```

Expected: FAIL because report module does not exist.

- [ ] **Step 3: Implement report renderer**

Write `app/reports/markdown_report.py`:

```python
from typing import Any


def render_report(
    research_topic: str,
    sources: list[dict[str, Any]],
    factors: list[dict[str, Any]],
    metrics: list[dict[str, Any]],
    limitations: list[str],
) -> str:
    lines = [
        f"# A 股因子研究报告：{research_topic}",
        "",
        "> 历史回测不构成投资建议。本报告仅用于量化研究流程展示。",
        "",
        "## 1. Source Summary",
    ]
    for source in sources:
        lines.append(f"- {source.get('source_title')} {source.get('source_url') or ''}".strip())

    lines.extend(["", "## 2. Extracted Factor Formulas"])
    for factor in factors:
        lines.append(f"- `{factor.get('factor_name')}`: `{factor.get('formula')}`")

    lines.extend(["", "## 3. Validation Metrics"])
    for metric in metrics:
        items = ", ".join(f"{k}={v}" for k, v in metric.items())
        lines.append(f"- {items}")

    lines.extend(["", "## 4. Limitations"])
    for item in limitations:
        lines.append(f"- {item}")

    return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify pass**

Run:

```bash
cd /Users/brain6/Documents/document/A-Share Factor Research Agent
pytest tests/test_report.py -v
```

Expected: all tests PASS.

## Task 16: LangGraph State Skeleton

**Files:**
- Create: `/Users/brain6/Documents/document/A-Share Factor Research Agent/app/agents/state.py`
- Create: `/Users/brain6/Documents/document/A-Share Factor Research Agent/app/agents/graph.py`

- [ ] **Step 1: Implement state**

Write `app/agents/state.py`:

```python
from typing import Literal, TypedDict


class ResearchState(TypedDict, total=False):
    run_id: str
    research_topic: str
    source_mode: Literal["auto", "upload", "hybrid"]
    universe: str
    start_date: str
    end_date: str
    document_paths: list[str]
    sources: list[dict]
    chunks: list[dict]
    factor_specs: list[dict]
    metrics: list[dict]
    report_markdown: str
    warnings: list[str]
```

- [ ] **Step 2: Implement a minimal graph placeholder**

Write `app/agents/graph.py`:

```python
from app.agents.state import ResearchState
from app.reports.markdown_report import render_report


def run_research_workflow(state: ResearchState) -> ResearchState:
    # MVP placeholder workflow. Later tasks replace this with LangGraph nodes.
    report = render_report(
        research_topic=state["research_topic"],
        sources=state.get("sources", []),
        factors=state.get("factor_specs", []),
        metrics=state.get("metrics", []),
        limitations=state.get("warnings", ["MVP workflow skeleton"]),
    )
    state["report_markdown"] = report
    return state
```

- [ ] **Step 3: Verify workflow skeleton**

Run:

```bash
cd /Users/brain6/Documents/document/A-Share Factor Research Agent
python - <<'PY'
from app.agents.graph import run_research_workflow
state = run_research_workflow({"research_topic": "A股动量因子", "source_mode": "upload"})
assert "report_markdown" in state
print("ok")
PY
```

Expected:

```text
ok
```

## Task 17: FastAPI API Skeleton

**Files:**
- Create: `/Users/brain6/Documents/document/A-Share Factor Research Agent/app/main.py`
- Create: `/Users/brain6/Documents/document/A-Share Factor Research Agent/app/api/research.py`

- [ ] **Step 1: Implement research router**

Write `app/api/research.py`:

```python
from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.graph import run_research_workflow

router = APIRouter(prefix="/research", tags=["research"])


class ResearchRunRequest(BaseModel):
    research_topic: str
    source_mode: str = "upload"
    universe: str = "CSI300"
    start_date: str = "2020-01-01"
    end_date: str = "2025-12-31"


@router.post("/runs")
def create_research_run(request: ResearchRunRequest):
    run_id = f"run_{uuid4().hex[:12]}"
    state = run_research_workflow(
        {
            "run_id": run_id,
            "research_topic": request.research_topic,
            "source_mode": request.source_mode,
            "universe": request.universe,
            "start_date": request.start_date,
            "end_date": request.end_date,
        }
    )
    return {
        "run_id": run_id,
        "status": "completed",
        "report_markdown": state["report_markdown"],
    }
```

- [ ] **Step 2: Implement app entry**

Write `app/main.py`:

```python
from fastapi import FastAPI

from app.api.research import router as research_router

app = FastAPI(title="A-Share Factor Research Agent")

app.include_router(research_router)


@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 3: Verify app imports**

Run:

```bash
cd /Users/brain6/Documents/document/A-Share Factor Research Agent
python - <<'PY'
from app.main import app
print(app.title)
PY
```

Expected:

```text
A-Share Factor Research Agent
```

## Task 18: Evaluation Fixtures

**Files:**
- Create: `/Users/brain6/Documents/document/A-Share Factor Research Agent/evals/tasks.jsonl`
- Create: `/Users/brain6/Documents/document/A-Share Factor Research Agent/evals/run_eval.py`

- [ ] **Step 1: Create eval task file**

Write `evals/tasks.jsonl`:

```jsonl
{"id":"dsl_valid_001","type":"dsl_validation","formula":"rank(returns(close, 20))","expected_valid":true}
{"id":"dsl_invalid_001","type":"dsl_validation","formula":"__import__('os').system('rm -rf /')","expected_valid":false}
{"id":"dsl_invalid_002","type":"dsl_validation","formula":"evil(close, 20)","expected_valid":false}
```

- [ ] **Step 2: Implement eval runner**

Write `evals/run_eval.py`:

```python
import json
from pathlib import Path

from app.factor.dsl import FactorSpec
from app.factor.validator import FactorDslValidator


def run() -> None:
    path = Path(__file__).with_name("tasks.jsonl")
    tasks = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    validator = FactorDslValidator()
    total = 0
    correct = 0
    for task in tasks:
        if task["type"] != "dsl_validation":
            continue
        spec = FactorSpec(
            factor_name=task["id"],
            hypothesis="eval",
            formula=task["formula"],
            required_fields=["close"],
            direction="unknown",
            category="eval",
            frequency="daily",
            lookback=20,
            source_title="eval",
            source_url=None,
            source_excerpt="eval",
            confidence=0.5,
        )
        result = validator.validate(spec)
        total += 1
        correct += int(result.valid == task["expected_valid"])
    print({"total": total, "correct": correct, "accuracy": correct / total if total else 0})


if __name__ == "__main__":
    run()
```

- [ ] **Step 3: Run eval**

Run:

```bash
cd /Users/brain6/Documents/document/A-Share Factor Research Agent
python evals/run_eval.py
```

Expected:

```text
{'total': 3, 'correct': 3, 'accuracy': 1.0}
```

## Task 19: Final Verification

**Files:**
- No new files.

- [ ] **Step 1: Run full unit test suite**

Run:

```bash
cd /Users/brain6/Documents/document/A-Share Factor Research Agent
pytest -v
```

Expected: all tests PASS.

- [ ] **Step 2: Run eval**

Run:

```bash
cd /Users/brain6/Documents/document/A-Share Factor Research Agent
python evals/run_eval.py
```

Expected: accuracy 1.0 for current DSL validation evals.

- [ ] **Step 3: Run API server**

Run:

```bash
cd /Users/brain6/Documents/document/A-Share Factor Research Agent
uvicorn app.main:app --reload --port 8000
```

Expected: server starts at `http://127.0.0.1:8000`.

- [ ] **Step 4: Test research endpoint**

Run in another terminal:

```bash
curl -X POST http://127.0.0.1:8000/research/runs \
  -H 'Content-Type: application/json' \
  -d '{"research_topic":"A股量价类动量因子","source_mode":"upload"}'
```

Expected: JSON response includes `run_id`, `status`, and `report_markdown`.

## Self-Review

Spec coverage:

- A-share-only positioning: covered by project scope and API defaults.
- Public and upload source modes: source policy and API skeleton included.
- Restricted Factor DSL: validator and executor tasks included.
- Deterministic factor execution: operators and executor included.
- Validation and backtesting: metrics, single-factor utilities, and selector included.
- Trace and evaluation: JSONL logging is not fully implemented in this first plan; this is a gap for the next plan.
- LangGraph: current plan adds a workflow skeleton, but not full LangGraph nodes; this is intentionally deferred until the deterministic pipeline is stable.
- Report generation: included.

Follow-up plan needed:

- Full LangGraph node implementation.
- LLM-based factor extraction.
- RAG retriever implementation with embeddings.
- SQLite persistence.
- SSE event streaming.
- Source auto-search and public document fetching.
- Charts.
- Complete trace logging.

