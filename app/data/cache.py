from pathlib import Path

import pandas as pd


class DailyBarCache:
    def __init__(self, cache_dir: str = "data_cache") -> None:
        self.cache_dir = Path(cache_dir)

    def read(
        self,
        provider_name: str,
        symbol: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame | None:
        path = self._path(provider_name, symbol, start_date, end_date)
        if not path.exists():
            return None
        frame = pd.read_csv(path, parse_dates=["date"])
        if frame.empty:
            return _empty_daily_bars()
        return frame.set_index(["symbol", "date"]).sort_index()

    def write(
        self,
        provider_name: str,
        symbol: str,
        start_date: str,
        end_date: str,
        data: pd.DataFrame,
    ) -> Path:
        path = self._path(provider_name, symbol, start_date, end_date)
        path.parent.mkdir(parents=True, exist_ok=True)
        if data.empty:
            _empty_daily_bars().reset_index().to_csv(path, index=False)
            return path

        frame = data.reset_index()
        frame.to_csv(path, index=False)
        return path

    def _path(self, provider_name: str, symbol: str, start_date: str, end_date: str) -> Path:
        safe_provider = _safe_part(provider_name)
        safe_symbol = _safe_part(symbol)
        safe_start = _safe_part(start_date)
        safe_end = _safe_part(end_date)
        return self.cache_dir / safe_provider / f"{safe_symbol}_{safe_start}_{safe_end}.csv"


def _safe_part(value: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in value)


def _empty_daily_bars() -> pd.DataFrame:
    return pd.DataFrame(
        columns=["open", "high", "low", "close", "volume", "amount"],
        index=pd.MultiIndex.from_arrays([[], []], names=["symbol", "date"]),
    )
