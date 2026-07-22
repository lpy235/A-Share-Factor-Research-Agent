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

    def __init__(
        self,
        fields: dict[str, Any],
        functions: dict[str, Callable[..., Any]],
    ) -> None:
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
