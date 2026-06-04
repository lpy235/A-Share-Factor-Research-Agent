import pandas as pd

from app.factor.operators import winsorize, zscore


def clean_factor_values(values: pd.Series) -> pd.Series:
    values = values.replace([float("inf"), float("-inf")], pd.NA)
    values = winsorize(values)
    return zscore(values)

