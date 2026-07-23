import numpy as np
import pandas as pd


def combine_factor_values(
    factor_values: dict[str, pd.Series],
    selected_names: list[str],
    method: str = "equal_weight",
    ic_weights: dict[str, float] | None = None,
) -> pd.Series:
    """Combine multiple factor value series into a single composite factor.

    Each factor is cross-sectionally standardized (daily z-score) before
    weighting so that factors on different scales contribute comparably.

    Supported methods:
      - ``equal_weight``: simple average of standardized factors.
      - ``ic_weight``: weights proportional to each factor's IS mean Rank IC.
      - ``risk_parity``: weights proportional to the inverse of each factor's
        standardized variance.

    Returns a Series with the same MultiIndex (symbol, date) as the inputs.
    """
    available = [name for name in selected_names if name in factor_values]
    if not available:
        return pd.Series(dtype=float)

    aligned = pd.concat(
        {name: factor_values[name] for name in available}, axis=1
    )
    aligned = aligned.dropna(how="all")
    if aligned.empty:
        return pd.Series(dtype=float)

    standardized = aligned.groupby(level="date").transform(_zscore)

    if method == "ic_weight":
        weights = ic_weights or {}
        vals = np.array([float(weights.get(name, 0.0)) for name in available])
        total = np.abs(vals).sum()
        if total == 0:
            vals = np.ones(len(available))
            total = float(len(available))
        weight_series = pd.Series(vals / total, index=available)
        combined = (standardized * weight_series).sum(axis=1)
    elif method == "risk_parity":
        variances = standardized.var()
        inv_var = 1.0 / (variances + 1e-10)
        weight_series = inv_var / inv_var.sum()
        combined = (standardized * weight_series).sum(axis=1)
    else:  # equal_weight
        combined = standardized.mean(axis=1)

    combined.name = "combined"
    return combined


def _zscore(values: pd.Series) -> pd.Series:
    std = values.std()
    if std == 0 or pd.isna(std):
        return values - values.mean()
    return (values - values.mean()) / std
