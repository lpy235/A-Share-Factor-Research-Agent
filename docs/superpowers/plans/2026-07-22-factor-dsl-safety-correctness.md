# Factor DSL Safety and Correctness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Prevent unsafe or forward-looking Factor DSL formulas from reaching execution, derive and validate formula metadata, and replace direct `eval` with a controlled AST interpreter without changing valid demo-factor results.

**Architecture:** Keep `FactorDslValidator` as the public validation boundary, add explicit operator signatures and derived formula metadata, and isolate AST evaluation in a small interpreter module. `FactorExecutor` will validate once, evaluate only approved AST nodes and registry entries, and verify that the result is a Pandas Series aligned to the market-data index. Existing workflow fallback behavior remains unchanged.

**Tech Stack:** Python 3.11+, `ast`, `dataclasses`, Pandas, Pydantic, pytest.

---

### Task 1: Add strict formula validation tests

**Files:**
- Modify: `tests/test_factor_dsl.py`
- Test: `tests/test_factor_dsl.py`

- [x] **Step 1: Extend the test helper to vary metadata**

Change `_spec` so tests can provide `required_fields` and `lookback` while keeping the current defaults:

~~~python
def _spec(
    formula: str,
    name: str = "momentum_20",
    *,
    required_fields: list[str] | None = None,
    lookback: int = 20,
) -> FactorSpec:
    return FactorSpec(
        factor_name=name,
        hypothesis="过去20日收益率较高的股票可能延续上涨。",
        formula=formula,
        required_fields=["close"] if required_fields is None else required_fields,
        direction="positive",
        category="momentum",
        frequency="daily",
        lookback=lookback,
        source_title="example report",
        source_url="https://example.com/report.pdf",
        source_excerpt="过去20日收益率可衡量短期动量。",
        confidence=0.8,
    )
~~~

- [x] **Step 2: Add failing tests for window semantics and metadata**

Append these tests to `tests/test_factor_dsl.py`:

~~~python
import pytest


@pytest.mark.parametrize(
    ("formula", "error_code"),
    [
        ("returns(close, 0)", "invalid_window:returns"),
        ("returns(close, -1)", "invalid_window:returns"),
        ("returns(close, 1.5)", "invalid_window:returns"),
        ("returns(close, 2521)", "window_exceeds_max:returns"),
    ],
)
def test_invalid_window_is_rejected(formula, error_code):
    result = FactorDslValidator().validate(_spec(formula, lookback=2521))
    assert result.valid is False
    assert error_code in result.errors


def test_formula_fields_must_match_declared_required_fields():
    result = FactorDslValidator().validate(
        _spec(
            "rank(returns(close, 20))",
            required_fields=["volume"],
        )
    )
    assert result.valid is False
    assert "required_fields_mismatch" in result.errors


def test_lookback_must_cover_formula_window():
    result = FactorDslValidator().validate(
        _spec("rank(returns(close, 60))", lookback=20)
    )
    assert result.valid is False
    assert "lookback_too_small" in result.errors


def test_volume_price_formula_derives_both_fields_and_window():
    formula = "rank(returns(close, 20) * ts_mean(volume, 20) / ts_mean(volume, 60))"
    result = FactorDslValidator().validate(
        _spec(formula, required_fields=["close", "volume"], lookback=60)
    )
    assert result.valid is True
    assert result.errors == []


@pytest.mark.parametrize(
    "formula",
    [
        "returns(close)",
        "rank(close, 20)",
        "winsorize(close, 0.9, 0.1)",
    ],
)
def test_invalid_operator_signature_is_rejected(formula):
    result = FactorDslValidator().validate(_spec(formula))
    assert result.valid is False
    assert any(error.startswith("invalid_signature:") for error in result.errors)


def test_formula_complexity_limit_is_rejected():
    formula = "close" + " + close" * 70
    result = FactorDslValidator().validate(_spec(formula))
    assert result.valid is False
    assert "ast_too_complex" in result.errors


def test_formula_length_limit_is_rejected():
    formula = " " * 513 + "close"
    result = FactorDslValidator().validate(_spec(formula))
    assert result.valid is False
    assert "formula_too_long" in result.errors


def test_call_depth_limit_is_rejected():
    formula = "rank(" * 17 + "close" + ")" * 17
    result = FactorDslValidator().validate(_spec(formula))
    assert result.valid is False
    assert "call_depth_exceeded" in result.errors
~~~

- [x] **Step 3: Run the focused tests and confirm they fail before implementation**

Run:

~~~bash
pytest tests/test_factor_dsl.py -q
~~~

Expected: the original tests pass, and the new strict-validation tests fail because the validator currently accepts invalid windows, does not derive metadata, and does not enforce signatures or complexity limits.

- [x] **Step 4: Commit the failing tests**

~~~bash
git add tests/test_factor_dsl.py
git commit -m "test: specify strict factor DSL validation"
~~~

### Task 2: Implement AST metadata and strict validation

**Files:**
- Modify: `app/factor/validator.py`
- Test: `tests/test_factor_dsl.py`

- [x] **Step 1: Add validator limits and explicit operator signatures**

Add these module-level declarations to `app/factor/validator.py`:

~~~python
MAX_FORMULA_LENGTH = 512
MAX_AST_NODES = 64
MAX_CALL_DEPTH = 16
MAX_WINDOW = 2520

WINDOWED_OPERATORS = {
    "returns",
    "delay",
    "ts_mean",
    "ts_std",
    "ts_min",
    "ts_max",
}

OPERATOR_ARITIES = {
    "returns": {2},
    "delay": {2},
    "ts_mean": {2},
    "ts_std": {2},
    "ts_min": {2},
    "ts_max": {2},
    "rank": {1},
    "zscore": {1},
    "winsorize": {1, 2, 3},
    "neutralize": {2},
}
~~~

- [x] **Step 2: Add a derived metadata value object**

Define a frozen dataclass in `app/factor/validator.py`:

~~~python
@dataclass(frozen=True)
class FormulaMetadata:
    fields: frozenset[str]
    max_window: int
~~~

Add a private recursive collector that walks the validated AST, records `allowed_fields`, records the second argument of each `WINDOWED_OPERATOR`, and returns `FormulaMetadata`. Pass a call-depth counter through recursive call nodes and emit `call_depth_exceeded` above `MAX_CALL_DEPTH`. It must also emit stable errors for missing or invalid windows, non-name call targets, unknown names, and unknown operators. A boolean constant must not count as an integer window.

- [x] **Step 3: Enforce source, AST, name, signature, window, and metadata rules**

Update `FactorDslValidator.validate` to:

~~~python
if len(spec.formula) > MAX_FORMULA_LENGTH:
    errors.append("formula_too_long")

tree = ast.parse(spec.formula, mode="eval")
nodes = list(ast.walk(tree))
if len(nodes) > MAX_AST_NODES:
    errors.append("ast_too_complex")
~~~

Then recursively validate each call. For a windowed operator, require exactly two positional arguments and require the second argument to be an `ast.Constant` containing an `int` but not a `bool`, with `1 <= window <= MAX_WINDOW`. For `winsorize`, allow one to three positional arguments and require supplied lower and upper arguments to be numeric constants in `[0, 1]`, with lower less than upper when both are supplied. Reject all keyword arguments for the current DSL surface.

After collecting metadata, compare:

~~~python
declared_fields = frozenset(spec.required_fields)
if declared_fields != metadata.fields:
    errors.append("required_fields_mismatch")
if spec.lookback < metadata.max_window:
    errors.append("lookback_too_small")
~~~

Keep the existing `unsafe_token`, `unknown_name`, `unknown_operator`, `unsafe_call`, and `unsupported_ast:*` error families so existing diagnostics remain recognizable.

- [x] **Step 4: Run the focused validator tests**

Run:

~~~bash
pytest tests/test_factor_dsl.py -q
~~~

Expected: all validator tests pass. If a valid generated formula fails, update the generator metadata rather than weakening validation.

- [x] **Step 5: Commit the validator implementation**

~~~bash
git add app/factor/validator.py tests/test_factor_dsl.py
git commit -m "feat: enforce factor DSL windows and metadata"
~~~

### Task 3: Add a controlled AST interpreter

**Files:**
- Create: `app/factor/interpreter.py`
- Modify: `app/factor/executor.py`
- Test: `tests/test_factor_dsl.py`

- [x] **Step 1: Add failing execution regression tests**

Append these tests to `tests/test_factor_dsl.py`:

~~~python
from app.factor.operators import returns


def test_executor_matches_operator_result_for_valid_formula():
    idx = pd.MultiIndex.from_product(
        [["000001", "000002"], pd.date_range("2024-01-01", periods=25)],
        names=["symbol", "date"],
    )
    data = pd.DataFrame({"close": list(range(1, 26)) + list(range(2, 27))}, index=idx)
    result = FactorExecutor().execute(_spec("returns(close, 20)"), data)
    expected = returns(data["close"], 20)
    pd.testing.assert_series_equal(result.values, expected.rename("momentum_20"))


def test_executor_rejects_formula_that_would_use_forward_data():
    with pytest.raises(ValueError, match="Invalid factor formula"):
        FactorExecutor().execute(_spec("delay(close, -1)"), _market_data())


def test_executor_rejects_non_series_expression():
    with pytest.raises(TypeError, match="Factor formula must return a pandas Series"):
        FactorExecutor().execute(_spec("1 + 2", required_fields=[]), _market_data())
~~~

Add a small `_market_data()` fixture helper in the test module that returns a valid `(symbol, date)` DataFrame with `close` and `volume` columns. Keep the existing numerical fixture unchanged.

- [x] **Step 2: Run the focused execution tests and confirm the new interpreter tests fail**

Run:

~~~bash
pytest tests/test_factor_dsl.py -q
~~~

Expected: the existing executor test passes, while the new tests fail until the interpreter is added and `FactorExecutor` is switched away from `eval`.

- [x] **Step 3: Implement the interpreter**

Create `app/factor/interpreter.py` with this public interface:

~~~python
import ast
import operator
from collections.abc import Callable
from typing import Any


class FormulaInterpreter:
    binary_operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
    }

    def __init__(self, fields: dict[str, Any], functions: dict[str, Callable[..., Any]]) -> None:
        self.fields = fields
        self.functions = functions

    def evaluate(self, tree: ast.Expression) -> Any:
        return self._evaluate(tree.body)

    def _evaluate(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
                raise ValueError("unsupported_constant")
            return node.value
        if isinstance(node, ast.Name):
            if node.id in self.fields:
                return self.fields[node.id]
            if node.id in self.functions:
                return self.functions[node.id]
            raise ValueError(f"unknown_name:{node.id}")
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return operator.neg(self._evaluate(node.operand))
        if isinstance(node, ast.BinOp):
            operation = self.binary_operators.get(type(node.op))
            if operation is None:
                raise ValueError(f"unsupported_ast:{type(node.op).__name__}")
            return operation(self._evaluate(node.left), self._evaluate(node.right))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.keywords:
                raise ValueError("keyword_arguments_not_allowed")
            function = self.functions.get(node.func.id)
            if function is None:
                raise ValueError(f"unknown_operator:{node.func.id}")
            return function(*(self._evaluate(argument) for argument in node.args))
        raise ValueError(f"unsupported_ast:{type(node).__name__}")
~~~

Implement only these cases:

~~~text
Expression → evaluate body
Constant → int/float only
Name → fields or functions lookup
UnaryOp(USub) → operator.neg
BinOp(Add/Sub/Mult/Div/Pow) → corresponding operator function
Call(Name) → resolve function and evaluate positional args
~~~

Raise `ValueError("unsupported_ast:<NodeName>")` for every other node, reject keyword arguments, and never call `eval`, `exec`, `getattr`, or dynamic imports. The validator remains responsible for detailed formula errors; the interpreter remains a small execution-only component.

- [x] **Step 4: Switch FactorExecutor to the interpreter**

In `app/factor/executor.py`:

1. Parse the formula once with `ast.parse(spec.formula, mode="eval")` after validation.
2. Build the existing function registry and field series registry.
3. Evaluate with `FormulaInterpreter(fields, functions).evaluate(tree)`.
4. Require the result to be a Pandas `Series`.
5. Require `values.index.equals(data.index)` and raise a clear `ValueError` if alignment is wrong.
6. Set `values.name = spec.factor_name` and return `FactorExecutionResult`.

Do not alter operator implementations or the valid formula strings produced by `FactorDslGenerationService`.

- [x] **Step 5: Run DSL and operator tests**

Run:

~~~bash
pytest tests/test_factor_dsl.py tests/test_factor_operators.py -q
~~~

Expected: all tests pass, including numerical equality with the existing operator implementation.

- [x] **Step 6: Commit the interpreter change**

~~~bash
git add app/factor/interpreter.py app/factor/executor.py tests/test_factor_dsl.py
git commit -m "feat: execute factor DSL through controlled interpreter"
~~~

### Task 4: Verify generator and workflow compatibility

**Files:**
- Modify: `app/agents/dsl_generation.py` only if stricter metadata exposes a mismatch
- Modify: `tests/test_agent_nodes.py` only if a generator regression assertion is needed
- Modify: `tests/test_agent_graph.py` only if fallback coverage is missing
- Test: `tests/test_factor_dsl.py`, `tests/test_agent_nodes.py`, `tests/test_agent_graph.py`

- [x] **Step 1: Add a workflow test for invalid-spec fallback**

Add these imports and the direct validation-node test to tests/test_agent_nodes.py:

~~~python
from app.agents.graph_nodes import validate_dsl_node
from app.factor.dsl import FactorSpec


def test_validate_dsl_node_replaces_forward_looking_formula_with_safe_fallback():
    invalid_spec = FactorSpec(
        factor_name="forward_looking",
        hypothesis="invalid test hypothesis",
        formula="delay(close, -1)",
        required_fields=["close"],
        direction="positive",
        category="test",
        frequency="daily",
        lookback=1,
        source_title="test source",
        source_excerpt="test excerpt",
        confidence=0.5,
    )
    state = {
        "run_id": "invalid_dsl_fallback",
        "factor_specs": [invalid_spec.model_dump()],
        "warnings": [],
        "errors": [],
        "trace": [],
    }

    result = validate_dsl_node(state)
    assert result["factor_specs"][0]["factor_name"] == "volume_price_momentum"
    assert result["validation_results"][0]["valid"] is False
    assert "invalid_window:delay" in result["validation_results"][0]["errors"]
    assert result["validation_results"][-1]["valid"] is True
    assert any("Invalid Factor DSL excluded" in warning for warning in result["warnings"])
~~~

Use the existing `run_traced_node` contract and keep the fallback formula generated by `_demo_hypothesis()`.

- [x] **Step 2: Run all factor and workflow tests**

Run:

~~~bash
pytest tests/test_factor_dsl.py tests/test_factor_operators.py tests/test_agent_nodes.py tests/test_agent_graph.py -q
~~~

Expected: all tests pass and the deterministic demo still selects `volume_price_momentum`.

- [x] **Step 3: Run the complete verification suite**

Run:

~~~bash
pytest -q
python evals/run_eval.py
python -m compileall app
git diff --check
~~~

Expected: pytest and eval exit successfully, compileall reports no syntax errors, and `git diff --check` is clean.

- [x] **Step 4: Inspect the final diff and commit the compatibility changes**

Run:

~~~bash
git diff --stat HEAD~3
git status --short
~~~

Then commit any remaining generator, workflow, or test changes:

~~~bash
git add app tests
git commit -m "test: verify strict DSL workflow compatibility"
~~~

### Task 5: Document the new validation contract

**Files:**
- Modify: `docs/ARCHITECTURE.md`
- Modify: `README.md`
- Modify: `docs/API.md` only if API validation errors are exposed there

- [x] **Step 1: Document the accepted DSL contract**

Add a concise section explaining:

~~~text
window arguments are positive integer constants;
maximum window is 2520;
required_fields must match formula fields;
lookback must cover the largest formula window;
formula execution uses a controlled AST interpreter;
invalid specs are excluded and reported in validation_results.
~~~

- [x] **Step 2: Document the remaining limitation**

State explicitly that this is an in-process controlled interpreter, not a separate-process resource sandbox. Keep the existing safety boundary and research-prototype disclaimers.

- [x] **Step 3: Run documentation and final checks**

Run:

~~~bash
git diff --check
pytest -q
~~~

Expected: both commands succeed.

- [x] **Step 4: Commit documentation**

~~~bash
git add README.md docs/ARCHITECTURE.md docs/API.md
git commit -m "docs: document strict factor DSL contract"
~~~

## Self-Review Checklist

- [x] Every task names exact files and test commands.
- [x] The plan preserves valid current formulas and deterministic fallback behavior.
- [x] Negative and zero windows are explicitly rejected before execution.
- [x] Metadata derivation and enforcement are covered by tests.
- [x] Direct `eval` removal is covered by execution regression tests.
- [x] Full pytest, eval, compileall, and diff checks are included.
- [x] Later backtest and factor-library work is explicitly out of scope.
