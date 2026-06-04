import pandas as pd


def save_equity_curve(returns: pd.Series, output_path: str, title: str) -> None:
    import matplotlib.pyplot as plt

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

