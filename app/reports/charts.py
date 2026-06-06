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
