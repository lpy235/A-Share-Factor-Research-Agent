"""Bounded transformations for already-valid Factor DSL specifications."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Iterable

from app.factor.dsl import FactorSpec
from app.factor.validator import FactorDslValidator, WINDOWED_OPERATORS


@dataclass(frozen=True)
class FactorVariation:
    spec: FactorSpec
    parent_factor_names: tuple[str, ...]
    reason: str
    round_number: int


class FactorVariationEngine:
    """Generate a finite, auditable family of safe DSL variations.

    The engine parses and rewrites only numeric window constants in operators
    already accepted by the DSL validator. It never evaluates or imports code.
    """

    def __init__(self, allowed_windows: Iterable[int] = (5, 10, 20, 60, 120, 252)) -> None:
        windows = tuple(sorted({int(value) for value in allowed_windows}))
        if not windows or any(value < 1 for value in windows):
            raise ValueError("allowed_windows must contain positive integers")
        self.allowed_windows = windows
        self.validator = FactorDslValidator()

    def generate(self, parent: FactorSpec, *, max_variants: int, round_number: int = 1) -> list[FactorVariation]:
        if max_variants < 0:
            raise ValueError("max_variants must not be negative")
        if not self.validator.validate(parent).valid:
            raise ValueError("parent factor must pass DSL validation")

        variations: list[FactorVariation] = []
        for old_window in _windows_in(parent.formula):
            for new_window in self.allowed_windows:
                if new_window == old_window:
                    continue
                formula = _replace_window(parent.formula, old_window, new_window)
                variation = self._build(
                    parent,
                    factor_name=f"{parent.factor_name}_w{old_window}to{new_window}",
                    formula=formula,
                    direction=parent.direction,
                    reason=f"白名单窗口从 {old_window} 调整为 {new_window}",
                    round_number=round_number,
                )
                if variation is not None:
                    variations.append(variation)
                if len(variations) >= max_variants:
                    return variations

        if parent.direction in {"positive", "negative"} and len(variations) < max_variants:
            opposite = "negative" if parent.direction == "positive" else "positive"
            variation = self._build(
                parent,
                factor_name=f"{parent.factor_name}_direction_{opposite}",
                formula=parent.formula,
                direction=opposite,
                reason="在保持公式不变的前提下反转排序方向",
                round_number=round_number,
            )
            if variation is not None:
                variations.append(variation)
        return variations[:max_variants]

    def combine(
        self, left: FactorSpec, right: FactorSpec, *, round_number: int = 1
    ) -> FactorVariation:
        """Create one explicit equal-weight score from two validated parents."""
        if not self.validator.validate(left).valid or not self.validator.validate(right).valid:
            raise ValueError("combined parents must pass DSL validation")
        direction = left.direction if left.direction == right.direction else "unknown"
        spec = left.model_copy(
            update={
                "factor_name": f"{left.factor_name}_plus_{right.factor_name}",
                "formula": f"rank({left.formula}) + rank({right.formula})",
                "required_fields": sorted(set(left.required_fields) | set(right.required_fields)),
                "direction": direction,
                "lookback": max(left.lookback, right.lookback),
                "hypothesis": f"{left.hypothesis}；与 {right.hypothesis} 的显式等权组合。",
            }
        )
        result = self.validator.validate(spec)
        if not result.valid:
            raise ValueError(f"combined factor failed DSL validation: {result.errors}")
        return FactorVariation(
            spec=spec,
            parent_factor_names=(left.factor_name, right.factor_name),
            reason="两个已验证因子的显式等权 rank 组合",
            round_number=round_number,
        )

    def _build(
        self,
        parent: FactorSpec,
        *,
        factor_name: str,
        formula: str,
        direction: str,
        reason: str,
        round_number: int,
    ) -> FactorVariation | None:
        spec = parent.model_copy(
            update={
                "factor_name": factor_name,
                "formula": formula,
                "direction": direction,
                "lookback": max(parent.lookback, max(_windows_in(formula), default=1)),
            }
        )
        result = self.validator.validate(spec)
        if not result.valid:
            return None
        return FactorVariation(
            spec=spec,
            parent_factor_names=(parent.factor_name,),
            reason=reason,
            round_number=round_number,
        )


def _windows_in(formula: str) -> list[int]:
    tree = ast.parse(formula, mode="eval")
    windows: list[int] = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in WINDOWED_OPERATORS
            and len(node.args) == 2
            and isinstance(node.args[1], ast.Constant)
            and isinstance(node.args[1].value, int)
        ):
            windows.append(node.args[1].value)
    return sorted(set(windows))


def _replace_window(formula: str, old_window: int, new_window: int) -> str:
    tree = ast.parse(formula, mode="eval")

    class WindowRewriter(ast.NodeTransformer):
        def visit_Call(self, node: ast.Call) -> ast.AST:
            self.generic_visit(node)
            if (
                isinstance(node.func, ast.Name)
                and node.func.id in WINDOWED_OPERATORS
                and len(node.args) == 2
                and isinstance(node.args[1], ast.Constant)
                and node.args[1].value == old_window
            ):
                node.args[1] = ast.Constant(value=new_window)
            return node

    rewritten = ast.fix_missing_locations(WindowRewriter().visit(tree))
    return ast.unparse(rewritten.body)
