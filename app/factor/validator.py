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

        allowed_nodes = (
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
        for node in ast.walk(tree):
            if not isinstance(node, allowed_nodes):
                errors.append(f"unsupported_ast:{type(node).__name__}")
                continue
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

        deduped = sorted(set(errors))
        return FactorDslValidationResult(valid=not deduped, errors=deduped)

