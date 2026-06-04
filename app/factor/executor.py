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

