from __future__ import annotations

from typing import Any

import pandas as pd

from app.market_data.sources.base import SourceCapabilityError


class AkshareRawDataSource:
    """AKShare adapter that normalizes daily bars without price adjustment."""

    source_name = "akshare"

    def __init__(self, client: Any | None = None) -> None:
        self._client = client

    def list_securities(self, as_of_date: str) -> pd.DataFrame:
        del as_of_date
        raw = self._get_client().stock_info_a_code_name()
        frame = raw.rename(columns={"code": "symbol", "名称": "security_name", "代码": "symbol"})
        if not {"symbol", "security_name"} <= set(frame.columns):
            raise ValueError("AKShare security master response has unexpected columns")
        return frame.loc[:, ["symbol", "security_name"]].copy()

    def fetch_daily_bars(
        self, symbols: list[str], start_date: str, end_date: str
    ) -> pd.DataFrame:
        frames: list[pd.DataFrame] = []
        for symbol in symbols:
            raw = self._get_client().stock_zh_a_hist(
                symbol=symbol.split(".", maxsplit=1)[0],
                period="daily",
                start_date=start_date.replace("-", ""),
                end_date=end_date.replace("-", ""),
                adjust="",
            )
            if raw.empty:
                continue
            frame = raw.rename(
                columns={
                    "日期": "trade_date",
                    "开盘": "open",
                    "最高": "high",
                    "最低": "low",
                    "收盘": "close",
                    "成交量": "volume",
                    "成交额": "amount",
                }
            )
            required = ["trade_date", "open", "high", "low", "close", "volume", "amount"]
            if set(required) - set(frame.columns):
                raise ValueError(f"AKShare daily-bar response is missing columns for {symbol}")
            frame["symbol"] = symbol
            frames.append(frame.loc[:, ["symbol", *required]])
        if not frames:
            return pd.DataFrame(
                columns=["symbol", "trade_date", "open", "high", "low", "close", "volume", "amount"]
            )
        return pd.concat(frames, ignore_index=True)

    def fetch_corporate_actions(self, start_date: str, end_date: str) -> pd.DataFrame:
        raise SourceCapabilityError("AKShare corporate-action endpoint is not configured")

    def fetch_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        raise SourceCapabilityError("AKShare trading-calendar endpoint is not configured")

    def fetch_security_status(self, start_date: str, end_date: str) -> pd.DataFrame:
        raise SourceCapabilityError("AKShare security-status endpoint is not configured")

    def _get_client(self) -> Any:
        if self._client is None:
            import akshare

            self._client = akshare
        return self._client
