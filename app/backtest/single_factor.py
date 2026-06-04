import pandas as pd


def compute_forward_returns(close: pd.Series, periods: int = 1) -> pd.Series:
    future_close = close.groupby(level="symbol", group_keys=False).shift(-periods)
    return future_close / close - 1


def compute_rank_ic(factor: pd.Series, forward_returns: pd.Series) -> pd.Series:
    df = pd.DataFrame({"factor": factor, "forward_returns": forward_returns}).dropna()
    return df.groupby(level="date").apply(
        lambda x: x["factor"].rank().corr(x["forward_returns"].rank())
    )


def compute_ic(factor: pd.Series, forward_returns: pd.Series) -> pd.Series:
    df = pd.DataFrame({"factor": factor, "forward_returns": forward_returns}).dropna()
    return df.groupby(level="date").apply(lambda x: x["factor"].corr(x["forward_returns"]))


def grouped_forward_returns(
    factor: pd.Series,
    forward_returns: pd.Series,
    groups: int = 5,
) -> pd.DataFrame:
    df = pd.DataFrame({"factor": factor, "forward_returns": forward_returns}).dropna()

    def assign_group(x: pd.Series) -> pd.Series:
        if len(x) < groups:
            return pd.Series([pd.NA] * len(x), index=x.index)
        return pd.qcut(x.rank(method="first"), groups, labels=range(1, groups + 1)).astype(int)

    df["group"] = df.groupby(level="date")["factor"].transform(assign_group)
    grouped = df.dropna().groupby([df.dropna().index.get_level_values("date"), "group"])[
        "forward_returns"
    ].mean()
    return grouped.unstack("group")

