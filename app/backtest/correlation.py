"""Factor correlation matrix and cross-sectional correlation computation."""

import pandas as pd


def compute_factor_correlation_matrix(
    factor_values: dict[str, pd.Series],
) -> pd.DataFrame:
    """Compute cross-sectional Spearman rank correlation matrix between factors.

    For each date, compute the rank correlation between every pair of factors,
    then average across all dates. Returns a square DataFrame.

    Args:
        factor_values: dict of {factor_name: pd.Series with MultiIndex (symbol, date)}

    Returns:
        DataFrame with factor names as both index and columns.
    """
    factor_names = list(factor_values.keys())
    if len(factor_names) < 2:
        return pd.DataFrame()

    aligned = pd.DataFrame({name: fv for name, fv in factor_values.items()}).dropna(how="all")

    if aligned.empty:
        return pd.DataFrame(index=factor_names, columns=factor_names, dtype=float)

    total = pd.DataFrame(0.0, index=factor_names, columns=factor_names)
    count = pd.DataFrame(0, index=factor_names, columns=factor_names)

    for _, date_frame in aligned.groupby(level="date", sort=True):
        corr_matrix = date_frame.rank().corr(method="spearman")
        if corr_matrix.empty:
            continue
        for row_name in corr_matrix.index:
            for col_name in corr_matrix.columns:
                value = corr_matrix.loc[row_name, col_name]
                if pd.notna(value):
                    total.loc[row_name, col_name] += float(value)
                    count.loc[row_name, col_name] += 1

    result = total.where(count.eq(0), total / count.replace(0, pd.NA))
    result = result.mask(count.eq(0))
    for factor_name in factor_names:
        result.loc[factor_name, factor_name] = 1.0
    return result


def deduplicate_by_correlation(
    factor_values: dict[str, pd.Series],
    corr_threshold: float = 0.7,
    keep_best: bool = True,
    quality_scores: dict[str, float] | None = None,
) -> tuple[list[str], dict[str, str]]:
    """Remove highly correlated factors, keeping the one with better quality.

    Args:
        factor_values: dict of {factor_name: pd.Series}
        corr_threshold: absolute correlation above which to deduplicate
        keep_best: if True, keep the factor with higher quality_score
        quality_scores: optional dict of {factor_name: quality} used for tie-breaking.

    Returns:
        (kept_factor_names, removed_reasons_map)
    """
    corr = compute_factor_correlation_matrix(factor_values)
    if corr.empty:
        return list(factor_values.keys()), {}

    quality_scores = quality_scores or {name: 0.0 for name in factor_values}
    kept = list(factor_values.keys())
    removed_reasons: dict[str, str] = {}

    # Greedy removal: iterate all pairs, remove the lower-quality one
    for i in range(len(kept)):
        for j in range(i + 1, len(kept)):
            a, b = kept[i], kept[j]
            if a not in corr.index or b not in corr.columns:
                continue
            pair_corr = corr.loc[a, b]
            if pd.isna(pair_corr) or abs(pair_corr) < corr_threshold:
                continue

            # Determine which to remove
            score_a = quality_scores.get(a, -1e9)
            score_b = quality_scores.get(b, -1e9)
            if score_a >= score_b:
                to_remove = b
                keeper = a
            else:
                to_remove = a
                keeper = b

            if to_remove in kept:
                kept.remove(to_remove)
                removed_reasons[to_remove] = (
                    f"ρ={pair_corr:.3f} with {keeper} (score: {score_a:.4f} vs {score_b:.4f})"
                )

    return kept, removed_reasons
