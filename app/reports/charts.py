import pandas as pd


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
    _save_series_chart(
        backtest_series,
        output_path,
        series_key="equity_curve",
        title="Long-Short Equity Curve",
        ylabel="Equity",
        baseline=False,
    )


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
