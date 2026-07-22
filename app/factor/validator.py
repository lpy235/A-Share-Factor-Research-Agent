"""Validation boundary for the small Factor DSL.

The validator deliberately treats formulas as data.  It checks the complete
expression tree and derives the fields and lookback used by the expression so
that callers cannot make an unsafe formula look safe by supplying metadata.
"""

import ast
import math
from dataclasses import dataclass
from numbers import Real
from typing import Any

from app.factor.dsl import FactorSpec


MAX_FORMULA_LENGTH = 512
MAX_AST_NODES = 64
MAX_CALL_DEPTH = 16
MAX_WINDOW = 2520

ALLOWED_FIELDS = frozenset({"open", "high", "low", "close", "volume", "amount"})
ALLOWED_OPERATORS = frozenset(
    {
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
)

WINDOWED_OPERATORS = frozenset(
    {"returns", "delay", "ts_mean", "ts_std", "ts_min", "ts_max"}
)

# Values are the accepted positional arities.  Keeping this table explicit
# prevents a newly added Python callable from becoming part of the DSL by
# accident.
OPERATOR_ARITIES = {
    "returns": frozenset({2}),
    "delay": frozenset({2}),
    "ts_mean": frozenset({2}),
    "ts_std": frozenset({2}),
    "ts_min": frozenset({2}),
    "ts_max": frozenset({2}),
    "rank": frozenset({1}),
    "zscore": frozenset({1}),
    "winsorize": frozenset({1, 2, 3}),
    "neutralize": frozenset({2}),
}

UNSAFE_TOKENS = frozenset(
    {"__", "import", "exec", "eval", "open(", "system", "subprocess"}
)

ALLOWED_NODES = (
    ast.Expression,
    ast.Call,
    ast.Name,
    ast.Load,
    ast.Constant,
    ast.BinOp,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.Pow,
    ast.USub,
    ast.UnaryOp,
)


@dataclass(frozen=True)
class FormulaMetadata:
    """Metadata derived from a parsed formula."""

    fields: frozenset[str]
    max_window: int


@dataclass(frozen=True)
class FactorDslValidationResult:
    valid: bool
    errors: list[str]
    metadata: FormulaMetadata | None = None


class FactorDslValidator:
    """Validate FactorSpec formulas without executing them."""

    # Preserve these class attributes for callers that use them to build the
    # execution environment.
    allowed_fields = ALLOWED_FIELDS
    allowed_operators = ALLOWED_OPERATORS
    unsafe_tokens = UNSAFE_TOKENS

    def validate(self, spec: FactorSpec) -> FactorDslValidationResult:
        errors: list[str] = []
        formula = spec.formula

        if any(token in formula for token in UNSAFE_TOKENS):
            errors.append("unsafe_token")
            return self._result(errors)

        if len(formula) > MAX_FORMULA_LENGTH:
            errors.append("formula_too_long")

        for field in spec.required_fields:
            if field not in ALLOWED_FIELDS:
                errors.append(f"unknown_field:{field}")

        try:
            tree = ast.parse(formula, mode="eval")
        except SyntaxError:
            errors.append("syntax_error")
            return self._result(errors)

        if sum(1 for _ in ast.walk(tree)) > MAX_AST_NODES:
            errors.append("ast_too_complex")

        self._validate_expression(tree.body, errors, call_depth=0)
        metadata = self._collect_metadata(tree.body, errors, call_depth=0)

        declared_fields = frozenset(spec.required_fields)
        if declared_fields != metadata.fields:
            errors.append("required_fields_mismatch")
        if spec.lookback < metadata.max_window:
            errors.append("lookback_too_small")

        return self._result(errors, metadata)

    @staticmethod
    def _result(
        errors: list[str], metadata: FormulaMetadata | None = None
    ) -> FactorDslValidationResult:
        # Stable ordering makes API responses, logs and tests deterministic.
        deduped = sorted(set(errors))
        return FactorDslValidationResult(
            valid=not deduped,
            errors=deduped,
            metadata=metadata,
        )

    def _validate_expression(
        self, node: ast.AST, errors: list[str], *, call_depth: int
    ) -> None:
        if not isinstance(node, ALLOWED_NODES):
            errors.append(f"unsupported_ast:{type(node).__name__}")
            return

        if isinstance(node, ast.Call):
            if call_depth >= MAX_CALL_DEPTH:
                errors.append("call_depth_exceeded")

            if not isinstance(node.func, ast.Name):
                errors.append("unsafe_call")
                # Still walk arguments to report unknown fields where possible.
                for arg in node.args:
                    self._validate_expression(arg, errors, call_depth=call_depth + 1)
                return

            operator = node.func.id
            if operator not in ALLOWED_OPERATORS:
                errors.append(f"unknown_operator:{operator}")
            else:
                expected_arities = OPERATOR_ARITIES[operator]
                if node.keywords or len(node.args) not in expected_arities:
                    errors.append(f"invalid_signature:{operator}")
                if operator in WINDOWED_OPERATORS and len(node.args) == 2:
                    self._validate_window(node.args[1], operator, errors)
                if operator == "winsorize":
                    self._validate_winsorize(node.args, errors)

            for arg in node.args:
                self._validate_expression(arg, errors, call_depth=call_depth + 1)
            # Keyword nodes are not part of the supported DSL surface.  The
            # call-level signature error above is sufficient and avoids
            # leaking Python's keyword AST detail into the public error code.
            return

        if isinstance(node, ast.Name):
            if node.id not in ALLOWED_FIELDS and node.id not in ALLOWED_OPERATORS:
                errors.append(f"unknown_name:{node.id}")
            return

        if isinstance(node, ast.Constant):
            if not _is_numeric_constant(node.value):
                errors.append("unsupported_constant")
            return

        for child in ast.iter_child_nodes(node):
            self._validate_expression(child, errors, call_depth=call_depth)

    def _collect_metadata(
        self, node: ast.AST, errors: list[str], *, call_depth: int
    ) -> FormulaMetadata:
        fields: set[str] = set()
        max_window = 0

        if isinstance(node, ast.Name):
            if node.id in ALLOWED_FIELDS:
                fields.add(node.id)
            return FormulaMetadata(frozenset(fields), max_window)

        if isinstance(node, ast.Call):
            if call_depth >= MAX_CALL_DEPTH:
                # The validation pass reports the public error.  Returning an
                # empty contribution here keeps metadata collection bounded.
                return FormulaMetadata(frozenset(), max_window)
            operator = node.func.id if isinstance(node.func, ast.Name) else None
            if operator in WINDOWED_OPERATORS and len(node.args) == 2:
                window = _constant_int(node.args[1])
                if window is not None and 1 <= window <= MAX_WINDOW:
                    max_window = window

            for arg in node.args:
                child = self._collect_metadata(
                    arg, errors, call_depth=call_depth + 1
                )
                fields.update(child.fields)
                max_window = max(max_window, child.max_window)
            return FormulaMetadata(frozenset(fields), max_window)

        for child_node in ast.iter_child_nodes(node):
            child = self._collect_metadata(
                child_node, errors, call_depth=call_depth
            )
            fields.update(child.fields)
            max_window = max(max_window, child.max_window)
        return FormulaMetadata(frozenset(fields), max_window)

    @staticmethod
    def _validate_window(node: ast.AST, operator: str, errors: list[str]) -> None:
        window = _constant_int(node)
        if window is None or window <= 0:
            errors.append(f"invalid_window:{operator}")
        elif window > MAX_WINDOW:
            errors.append(f"window_exceeds_max:{operator}")

    @staticmethod
    def _validate_winsorize(args: list[ast.AST], errors: list[str]) -> None:
        if len(args) < 2:
            return

        lower = _constant_real(args[1])
        upper = _constant_real(args[2]) if len(args) == 3 else 0.99
        if lower is None or not 0 <= lower <= 1:
            errors.append("invalid_parameter:winsorize")
            return
        if upper is None or not 0 <= upper <= 1 or lower >= upper:
            errors.append("invalid_parameter:winsorize")


def _is_numeric_constant(value: Any) -> bool:
    return isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(value)


def _constant_real(node: ast.AST) -> float | None:
    if not isinstance(node, ast.Constant) or not _is_numeric_constant(node.value):
        return None
    return float(node.value)


def _constant_int(node: ast.AST) -> int | None:
    if not isinstance(node, ast.Constant):
        return None
    value = node.value
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value
