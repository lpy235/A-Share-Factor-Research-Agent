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


def excess_return(portfolio: pd.Series, benchmark: pd.Series) -> pd.Series:
    """Daily excess return of portfolio over benchmark, aligned by date."""
    aligned = pd.DataFrame({"portfolio": portfolio, "benchmark": benchmark}).dropna()
    if aligned.empty:
        return pd.Series(dtype=float)
    return aligned["portfolio"] - aligned["benchmark"]


def beta(portfolio: pd.Series, benchmark: pd.Series) -> float:
    """Portfolio beta relative to benchmark."""
    aligned = pd.DataFrame({"portfolio": portfolio, "benchmark": benchmark}).dropna()
    if aligned.empty:
        return 0.0
    var = float(aligned["benchmark"].var())
    if var == 0 or np.isnan(var):
        return 0.0
    return float(aligned["portfolio"].cov(aligned["benchmark"]) / var)


def tracking_error(excess: pd.Series, periods_per_year: int = 252) -> float:
    """Annualized tracking error of excess returns."""
    clean = excess.dropna()
    if clean.empty:
        return 0.0
    std = clean.std()
    if std == 0 or np.isnan(std):
        return 0.0
    return float(std * np.sqrt(periods_per_year))


def information_ratio(excess: pd.Series, periods_per_year: int = 252) -> float:
    """Annualized information ratio of excess returns."""
    clean = excess.dropna()
    if clean.empty:
        return 0.0
    std = clean.std()
    if std == 0 or np.isnan(std):
        return 0.0
    return float(clean.mean() / std * np.sqrt(periods_per_year))

