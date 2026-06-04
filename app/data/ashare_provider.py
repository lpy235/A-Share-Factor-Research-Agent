import pandas as pd


class AkshareAshareDataProvider:
    def get_universe(self, universe_name: str, date: str) -> list[str]:
        return ["000001", "000002", "600000", "600519", "300750"]

    def get_daily_bars(
        self,
        symbols: list[str],
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        import akshare as ak

        frames = []
        for symbol in symbols:
            raw = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start_date.replace("-", ""),
                end_date=end_date.replace("-", ""),
                adjust="qfq",
            )
            if raw.empty:
                continue
            frame = raw.rename(
                columns={
                    "日期": "date",
                    "开盘": "open",
                    "收盘": "close",
                    "最高": "high",
                    "最低": "low",
                    "成交量": "volume",
                    "成交额": "amount",
                }
            )
            frame["symbol"] = symbol
            frame["date"] = pd.to_datetime(frame["date"])
            frames.append(frame[["symbol", "date", "open", "high", "low", "close", "volume", "amount"]])

        if not frames:
            return pd.DataFrame(
                columns=["open", "high", "low", "close", "volume", "amount"],
                index=pd.MultiIndex.from_arrays([[], []], names=["symbol", "date"]),
            )
        return pd.concat(frames).set_index(["symbol", "date"]).sort_index()

