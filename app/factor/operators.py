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
    df = pd.DataFrame({"x": x, "by": by})
    group_mean = df.groupby(["date", "by"])["x"].transform("mean")
    return df["x"] - group_mean

