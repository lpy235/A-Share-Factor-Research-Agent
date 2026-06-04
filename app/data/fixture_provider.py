import numpy as np
import pandas as pd


class FixtureAshareDataProvider:
    def get_universe(self, universe_name: str, date: str) -> list[str]:
        return [f"{i:06d}" for i in range(1, 51)]

    def get_daily_bars(
        self,
        symbols: list[str],
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        dates = pd.date_range(start_date, end_date, freq="B")
        idx = pd.MultiIndex.from_product([symbols, dates], names=["symbol", "date"])
        rng = np.random.default_rng(42)
        df = pd.DataFrame(index=idx)

        symbol_codes = pd.Series(idx.get_level_values("symbol"), index=idx).astype(str)
        symbol_id = symbol_codes.str[-2:].astype(int).to_numpy()
        daily_noise = rng.normal(0, 0.008, size=len(idx))
        drift = (symbol_id % 7 - 3) * 0.0003
        returns = daily_noise + drift
        close = 100 * (1 + pd.Series(returns, index=idx).groupby(level="symbol").cumsum())

        df["close"] = close.clip(lower=1)
        df["open"] = df["close"] * (1 + rng.normal(0, 0.002, size=len(idx)))
        df["high"] = df[["open", "close"]].max(axis=1) * 1.01
        df["low"] = df[["open", "close"]].min(axis=1) * 0.99
        df["volume"] = rng.integers(100_000, 2_000_000, size=len(idx))
        df["amount"] = df["close"] * df["volume"]
        return df

