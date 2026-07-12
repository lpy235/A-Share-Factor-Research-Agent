import pandas as pd
import numpy as np


def _pyplot():
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    return plt


def save_equity_curve(returns: pd.Series, output_path: str, title: str) -> None:
    plt = _pyplot()

    equity = (1 + returns.fillna(0)).cumprod()
    fig, ax = plt.subplots(figsize=(8, 4))
    equity.plot(ax=ax)
    ax.set_title(title)
    ax.set_xlabel("Date")
    ax.set_ylabel("Equity")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def save_metric_overview_chart(metrics: list[dict], output_path: str) -> None:
    plt = _pyplot()

    frame = pd.DataFrame(metrics)
    fig, ax = plt.subplots(figsize=(8, 4))
    if frame.empty:
        ax.text(0.5, 0.5, "No metrics", ha="center", va="center")
    else:
        plot_frame = frame.set_index("factor_name")[["mean_rank_ic", "icir", "sharpe"]].astype(float)
        plot_frame.plot(kind="bar", ax=ax)
        ax.axhline(0, color="#667085", linewidth=0.8)
        ax.set_xlabel("Factor")
        ax.set_ylabel("Value")
    ax.set_title("Factor Metric Overview")
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def save_factor_quality_chart(metrics: list[dict], output_path: str) -> None:
    plt = _pyplot()

    frame = pd.DataFrame(metrics)
    fig, ax = plt.subplots(figsize=(8, 4))
    if frame.empty:
        ax.text(0.5, 0.5, "No metrics", ha="center", va="center")
    else:
        frame = frame.set_index("factor_name")
        coverage = frame["coverage_ratio"].astype(float)
        missing = frame["missing_ratio"].astype(float)
        quality = pd.DataFrame({"coverage": coverage, "missing": missing})
        quality.plot(kind="bar", stacked=False, ax=ax, color=["#0b766e", "#a73737"])
        ax.set_ylim(0, 1)
        ax.set_xlabel("Factor")
        ax.set_ylabel("Ratio")
    ax.set_title("Factor Coverage Quality")
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def save_rank_ic_chart(backtest_series: dict, output_path: str) -> None:
    _save_series_chart(
        backtest_series,
        output_path,
        series_key="rank_ic",
        title="Rank IC Time Series",
        ylabel="Rank IC",
        baseline=True,
    )


def save_cumulative_ic_chart(backtest_series: dict, output_path: str) -> None:
    _save_series_chart(
        backtest_series,
        output_path,
        series_key="cumulative_rank_ic",
        title="Cumulative Rank IC",
        ylabel="Cumulative IC",
        baseline=True,
    )


def save_equity_curve_chart(backtest_series: dict, output_path: str) -> None:
    """Equity curve with drawdown shadow overlay (BOAT-FX style)."""
    plt = _pyplot()

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(10, 6), gridspec_kw={"height_ratios": [3, 1]}, sharex=True
    )
    plotted = False
    for factor_name, payload in backtest_series.items():
        eq_points = payload.get("equity_curve", [])
        dd_points = payload.get("drawdown", [])
        if not eq_points:
            continue
        eq_frame = _points_to_frame(eq_points)
        dd_frame = _points_to_frame(dd_points)

        ax1.plot(eq_frame.index, eq_frame["value"], label=factor_name, linewidth=1.2)
        ax1.fill_between(
            eq_frame.index,
            eq_frame["value"],
            alpha=0.08,
            color="#e74c3c",
        )
        if not dd_frame.empty:
            ax2.fill_between(
                dd_frame.index,
                0,
                dd_frame["value"],
                alpha=0.35,
                color="#e74c3c",
                label=f"{factor_name} drawdown",
            )
        plotted = True

    if not plotted:
        ax1.text(0.5, 0.5, "No equity curve", ha="center", va="center")

    ax1.set_title("Long-Short Equity Curve & Drawdown Shadow")
    ax1.set_ylabel("Equity")
    ax1.grid(True, alpha=0.2)
    ax1.legend(loc="upper left", fontsize=7)

    ax2.set_xlabel("Date")
    ax2.set_ylabel("Drawdown")
    ax2.grid(True, alpha=0.2)
    ax2.axhline(0, color="#667085", linewidth=0.6)
    ax2.set_ylim(-1.0, 0.1)

    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def save_rolling_sharpe_chart(backtest_series: dict, output_path: str, window: int = 63) -> None:
    """Rolling Sharpe ratio chart (BOAT-FX style, default 63-day)."""
    plt = _pyplot()

    fig, ax = plt.subplots(figsize=(10, 4))
    plotted = False
    for factor_name, payload in backtest_series.items():
        lr_points = payload.get("long_short_returns", [])
        if not lr_points:
            continue
        lr_frame = _points_to_frame(lr_points)
        if lr_frame.empty or len(lr_frame) < window:
            continue
        rolling_sharpe = (
            lr_frame["value"].rolling(window).mean()
            / lr_frame["value"].rolling(window).std()
            * np.sqrt(252)
        )
        rolling_sharpe.plot(ax=ax, label=factor_name, linewidth=1.0)
        plotted = True

    if not plotted:
        ax.text(0.5, 0.5, "Not enough data for rolling Sharpe", ha="center", va="center")
    else:
        ax.axhline(0, color="#667085", linewidth=0.6, linestyle="--")
        ax.legend(loc="upper right", fontsize=7)
    ax.set_title(f"Rolling Sharpe Ratio ({window}-day)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Sharpe (ann.)")
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def save_monthly_heatmap(backtest_series: dict, output_path: str) -> None:
    """Monthly returns heatmap (BOAT-FX style)."""
    plt = _pyplot()

    factor_name, payload = _first_factor_payload(backtest_series)
    lr_points = payload.get("long_short_returns", []) if payload else []
    if not lr_points:
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.text(0.5, 0.5, "No return data for monthly heatmap", ha="center", va="center")
        fig.tight_layout()
        fig.savefig(output_path, dpi=160)
        plt.close(fig)
        return

    lr_frame = _points_to_frame(lr_points)
    if lr_frame.empty:
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.text(0.5, 0.5, "No return data", ha="center", va="center")
        fig.tight_layout()
        fig.savefig(output_path, dpi=160)
        plt.close(fig)
        return

    # Build monthly return matrix
    monthly = lr_frame["value"].resample("ME").apply(lambda x: (1 + x).prod() - 1)
    months = monthly.index.month.unique()
    years = monthly.index.year.unique()
    if len(years) == 0:
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.text(0.5, 0.5, "Insufficient data for monthly heatmap", ha="center", va="center")
        fig.tight_layout()
        fig.savefig(output_path, dpi=160)
        plt.close(fig)
        return

    pivot = pd.DataFrame(index=sorted(months), columns=sorted(years), dtype=float)
    for (ts, val) in monthly.items():
        pivot.loc[ts.month, ts.year] = val

    pivot = pivot.sort_index()

    fig, ax = plt.subplots(figsize=(max(8, len(years) * 1.1), 5))
    import matplotlib.colors as mcolors

    vmax = max(abs(pivot.min().min()), abs(pivot.max().max()), 0.01)
    norm = mcolors.TwoSlopeNorm(vmin=-vmax, vcenter=0, vmax=vmax)
    im = ax.imshow(
        pivot.values,
        cmap="RdYlGn",
        norm=norm,
        aspect="auto",
        interpolation="nearest",
    )

    ax.set_xticks(range(len(years)))
    ax.set_xticklabels([str(int(y)) for y in sorted(years)], rotation=0)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels([f"{int(m):02d}" for m in pivot.index])
    ax.set_xlabel("Year")
    ax.set_ylabel("Month")
    ax.set_title(f"Monthly Returns Heatmap: {factor_name or 'factor'}")

    # Annotate cells with percentage
    for i in range(len(pivot.index)):
        for j in range(len(years)):
            val = pivot.values[i, j]
            if not np.isnan(val):
                color = "white" if abs(val) > vmax * 0.5 else "black"
                ax.text(j, i, f"{val:.1%}", ha="center", va="center", fontsize=8, color=color)

    cbar = fig.colorbar(im, ax=ax, shrink=0.85)
    cbar.set_label("Monthly Return")
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def save_ic_decay_chart(backtest_series: dict, output_path: str) -> None:
    """IC decay: rolling 20-day Rank IC to visualize alpha decay over time."""
    plt = _pyplot()

    fig, ax = plt.subplots(figsize=(10, 4))
    plotted = False
    for factor_name, payload in backtest_series.items():
        points = payload.get("rank_ic", [])
        if not points:
            continue
        frame = _points_to_frame(points)
        if frame.empty or len(frame) < 20:
            continue
        rolling_20 = frame["value"].rolling(20).mean()
        rolling_20.plot(ax=ax, label=factor_name, linewidth=1.0)
        plotted = True

    if not plotted:
        ax.text(0.5, 0.5, "Not enough data for IC decay", ha="center", va="center")
    else:
        ax.axhline(0, color="#667085", linewidth=0.6, linestyle="--")
        ax.legend(loc="upper right", fontsize=7)
    ax.set_title("IC Decay (Rolling 20-day Rank IC)")
    ax.set_xlabel("Date")
    ax.set_ylabel("Rolling Rank IC")
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def _save_series_chart(
    backtest_series: dict,
    output_path: str,
    *,
    series_key: str,
    title: str,
    ylabel: str,
    baseline: bool,
) -> None:
    plt = _pyplot()

    fig, ax = plt.subplots(figsize=(8, 4))
    plotted = False
    for factor_name, payload in backtest_series.items():
        points = payload.get(series_key, [])
        if not points:
            continue
        frame = pd.DataFrame(points)
        frame["date"] = pd.to_datetime(frame["date"])
        frame = frame.set_index("date")
        frame["value"].astype(float).plot(ax=ax, label=factor_name)
        plotted = True
    if not plotted:
        ax.text(0.5, 0.5, f"No {series_key}", ha="center", va="center")
    if baseline:
        ax.axhline(0, color="#667085", linewidth=0.8)
    ax.set_title(title)
    ax.set_xlabel("Date")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    if plotted:
        ax.legend(loc="best", fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def _first_factor_payload(backtest_series: dict) -> tuple[str | None, dict | None]:
    for factor_name, payload in backtest_series.items():
        return factor_name, payload
    return None, None


def _points_to_frame(points: list[dict]) -> pd.DataFrame:
    """Convert [{date, value}] list to datetime-indexed DataFrame."""
    if not points:
        return pd.DataFrame(columns=["value"])
    frame = pd.DataFrame(points)
    frame["date"] = pd.to_datetime(frame["date"])
    frame = frame.set_index("date")
    return frame


def save_factor_correlation_chart(
    correlation_matrix: pd.DataFrame, output_path: str
) -> None:
    """Factor Spearman correlation heatmap."""
    plt = _pyplot()

    if correlation_matrix.empty or len(correlation_matrix) < 2:
        fig, ax = plt.subplots(figsize=(6, 5))
        ax.text(0.5, 0.5, "Insufficient factors for correlation matrix",
                ha="center", va="center")
        fig.tight_layout()
        fig.savefig(output_path, dpi=160)
        plt.close(fig)
        return

    import matplotlib.colors as mcolors

    fig, ax = plt.subplots(figsize=(max(6, len(correlation_matrix) * 1.2),
                                    max(5, len(correlation_matrix) * 1.0)))
    norm = mcolors.TwoSlopeNorm(vmin=-1, vcenter=0, vmax=1)
    im = ax.imshow(correlation_matrix.values, cmap="RdBu_r", norm=norm,
                   aspect="auto", interpolation="nearest")

    labels = list(correlation_matrix.index)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_title("Factor Cross-Sectional Spearman Correlation")

    for i in range(len(labels)):
        for j in range(len(labels)):
            val = correlation_matrix.values[i, j]
            if not np.isnan(val):
                ax.text(j, i, f"{val:.2f}", ha="center", va="center",
                        fontsize=7, color="white" if abs(val) > 0.5 else "black")

    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label("Spearman ρ")
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def save_drawdown_chart(backtest_series: dict, output_path: str) -> None:
    _save_series_chart(
        backtest_series,
        output_path,
        series_key="drawdown",
        title="Drawdown Curve",
        ylabel="Drawdown",
        baseline=True,
    )


def save_grouped_returns_chart(backtest_series: dict, output_path: str) -> None:
    plt = _pyplot()

    fig, ax = plt.subplots(figsize=(8, 4))
    factor_name, payload = _first_factor_payload(backtest_series)
    records = payload.get("grouped_returns", []) if payload else []
    if not records:
        ax.text(0.5, 0.5, "No grouped returns", ha="center", va="center")
    else:
        frame = pd.DataFrame(records).drop(columns=["date"], errors="ignore")
        means = frame.astype(float).mean(axis=0)
        means.plot(kind="bar", ax=ax, color="#0b766e")
        ax.axhline(0, color="#667085", linewidth=0.8)
        ax.set_xlabel("Group")
        ax.set_ylabel("Average Forward Return")
    ax.set_title(f"Grouped Returns: {factor_name or 'factor'}")
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_path, dpi=160)
    plt.close(fig)
