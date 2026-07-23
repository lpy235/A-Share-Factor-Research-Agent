import pandas as pd


def walk_forward_ic(rank_ic_series: pd.Series, n_windows: int = 5) -> dict:
    """Walk-forward stability analysis over a daily Rank IC series.

    Splits the IC series into ``n_windows`` non-overlapping chunks and reports
    per-window mean IC / ICIR plus cross-window stability statistics such as
    the share of windows with positive IC and whether the IC sign is
    consistent across windows.
    """
    clean = rank_ic_series.dropna()
    if len(clean) < n_windows * 2:
        return {
            "windows": [],
            "stability": {"insufficient_data": True, "window_count": 0},
        }

    window_size = len(clean) // n_windows
    windows: list[dict] = []
    ic_values: list[float] = []
    for i in range(n_windows):
        start = i * window_size
        end = (i + 1) * window_size if i < n_windows - 1 else len(clean)
        chunk = clean.iloc[start:end]
        if chunk.empty:
            continue
        mean_ic = float(chunk.mean())
        ic_std = float(chunk.std()) if len(chunk) > 1 else 0.0
        icir = mean_ic / ic_std if ic_std != 0 else 0.0
        windows.append(
            {
                "window_index": i,
                "start_date": _date_str(chunk.index[0]),
                "end_date": _date_str(chunk.index[-1]),
                "mean_ic": round(mean_ic, 6),
                "ic_std": round(ic_std, 6),
                "icir": round(icir, 6),
                "observation_count": int(len(chunk)),
            }
        )
        ic_values.append(mean_ic)

    ic_series = pd.Series(ic_values)
    window_count = len(windows)
    positive_count = int((ic_series > 0).sum()) if len(ic_series) else 0
    stability = {
        "window_count": window_count,
        "positive_ic_windows": positive_count,
        "positive_ratio": round(positive_count / window_count, 4) if window_count else 0.0,
        "mean_ic": round(float(ic_series.mean()), 6) if len(ic_series) else 0.0,
        "ic_std_across_windows": round(float(ic_series.std()), 6) if len(ic_series) > 1 else 0.0,
        "sign_consistent": bool(
            window_count > 0 and (positive_count == 0 or positive_count == window_count)
        ),
        "ic_range": round(float(ic_series.max() - ic_series.min()), 6) if len(ic_series) else 0.0,
    }
    return {"windows": windows, "stability": stability}


def _date_str(value) -> str:
    if hasattr(value, "date"):
        return str(value.date())
    return str(value)
