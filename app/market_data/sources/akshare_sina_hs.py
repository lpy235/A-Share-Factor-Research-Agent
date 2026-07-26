"""AKShare 新浪通道的沪深在市 A 股原始日线来源。"""

from __future__ import annotations

from typing import Any

import pandas as pd
import requests

from app.market_data.sources.base import SourceCapabilityError


class AkshareSinaHsRawDataSource:
    """Fetch unadjusted daily bars for currently listed Shanghai and Shenzhen A-shares.

    Sina does not provide Beijing-market data through this endpoint. The source
    deliberately excludes those codes so callers cannot mistake its universe
    for a complete A-share history.
    """

    source_name = "akshare_sina_hs_active_research"
    corporate_actions_source_name = "akshare_stock_dividend_cninfo"
    _SH_PREFIXES = ("600", "601", "603", "605", "688", "689")
    _SZ_PREFIXES = ("000", "001", "002", "003", "300", "301")

    def __init__(
        self,
        client: Any | None = None,
        *,
        include_delisted: bool = False,
        cninfo_timeout_seconds: float = 30.0,
    ) -> None:
        if cninfo_timeout_seconds <= 0:
            raise ValueError("cninfo_timeout_seconds must be positive")
        self._client = client
        self.include_delisted = include_delisted
        self.cninfo_timeout_seconds = float(cninfo_timeout_seconds)
        if include_delisted:
            self.source_name = "akshare_sina_hs_active_and_delisted_research"

    def list_securities(self, as_of_date: str) -> pd.DataFrame:
        del as_of_date
        raw = self._get_client().stock_info_a_code_name()
        code_column = _first_column(raw, "code", "代码")
        name_column = _first_column(raw, "name", "名称")
        frame = raw.loc[:, [code_column, name_column]].rename(
            columns={code_column: "code", name_column: "security_name"}
        )
        frame["code"] = frame["code"].astype(str).str.zfill(6)
        sh_mask = frame["code"].str.startswith(self._SH_PREFIXES)
        sz_mask = frame["code"].str.startswith(self._SZ_PREFIXES)
        selected = frame.loc[sh_mask | sz_mask].copy()
        selected["exchange"] = selected["code"].where(sh_mask.loc[selected.index], "SZ")
        selected.loc[selected["exchange"].ne("SZ"), "exchange"] = "SH"
        selected["symbol"] = selected["code"] + "." + selected["exchange"]
        active = selected.loc[:, ["symbol", "security_name"]]
        if not self.include_delisted:
            return active.reset_index(drop=True)
        delisted = self._delisted_security_master().loc[:, ["symbol", "security_name"]]
        return pd.concat([active, delisted], ignore_index=True).drop_duplicates("symbol", keep="first")

    def fetch_security_master(self, as_of_date: str) -> pd.DataFrame:
        """Return an exchange-sourced master for the configured universe snapshot."""
        del as_of_date
        client = self._get_client()
        current = pd.concat(
            [
                _normalize_security_master(
                    client.stock_info_sh_name_code(board),
                    code_column="证券代码",
                    name_column="证券简称",
                    listing_column="上市日期",
                    exchange="SH",
                )
                for board in ("主板A股", "科创板")
            ]
            + [
                _normalize_security_master(
                    client.stock_info_sz_name_code(),
                    code_column="A股代码",
                    name_column="A股简称",
                    listing_column="A股上市日期",
                    exchange="SZ",
                )
            ],
            ignore_index=True,
        )
        frames = [current]
        if self.include_delisted:
            frames.append(self._delisted_security_master())
        master = pd.concat(frames, ignore_index=True)
        return master.drop_duplicates("symbol", keep="first").reset_index(drop=True)

    def _delisted_security_master(self) -> pd.DataFrame:
        client = self._get_client()
        return pd.concat(
            [
                _normalize_security_master(
                    client.stock_info_sh_delist("全部"),
                    code_column="公司代码",
                    name_column="公司简称",
                    listing_column="上市日期",
                    exchange="SH",
                    exit_column="暂停上市日期",
                    exit_type="suspension",
                ),
                _normalize_security_master(
                    client.stock_info_sz_delist("终止上市公司"),
                    code_column="证券代码",
                    name_column="证券简称",
                    listing_column="上市日期",
                    exchange="SZ",
                    exit_column="终止上市日期",
                    exit_type="delisting",
                ),
            ],
            ignore_index=True,
        )

    def fetch_daily_bars(
        self, symbols: list[str], start_date: str, end_date: str
    ) -> pd.DataFrame:
        frames: list[pd.DataFrame] = []
        for symbol in symbols:
            code, exchange = _split_hs_symbol(symbol)
            sina_symbol = f"{exchange.lower()}{code}"
            try:
                raw = self._get_client().stock_zh_a_daily(
                    symbol=sina_symbol,
                    start_date=start_date.replace("-", ""),
                    end_date=end_date.replace("-", ""),
                    adjust="",
                )
            except Exception as exc:
                if type(exc).__name__ != "JSONDecodeError" and "decode" not in str(exc).lower():
                    raise
                raw = _fetch_sina_price_history(sina_symbol)
            if raw.empty:
                continue
            frame = raw.copy()
            if "date" not in frame and frame.index.name == "date":
                frame = frame.reset_index()
            required = ["date", "open", "high", "low", "close", "volume", "amount"]
            if set(required) - set(frame.columns):
                raise ValueError(f"AKShare Sina daily-bar response is missing columns for {symbol}")
            frame = frame.rename(columns={"date": "trade_date"})
            frame["trade_date"] = pd.to_datetime(frame["trade_date"], errors="coerce", utc=True).dt.tz_localize(None)
            zero_value_placeholder = (
                frame[["open", "high", "low"]].eq(0).all(axis=1)
                & frame[["volume", "amount"]].eq(0).all(axis=1)
            )
            frame = frame.loc[~zero_value_placeholder].copy()
            frame = frame.loc[
                frame["trade_date"].between(pd.Timestamp(start_date), pd.Timestamp(end_date))
            ].copy()
            if frame.empty:
                continue
            frame["symbol"] = symbol
            frames.append(
                frame.loc[:, ["symbol", "trade_date", "open", "high", "low", "close", "volume", "amount"]]
            )
        if not frames:
            return pd.DataFrame(
                columns=["symbol", "trade_date", "open", "high", "low", "close", "volume", "amount"]
            )
        return pd.concat(frames, ignore_index=True)

    def fetch_calendar(self, start_date: str, end_date: str) -> pd.DataFrame:
        raw = self._get_client().tool_trade_date_hist_sina()
        date_column = _first_column(raw, "trade_date")
        calendar = pd.DataFrame({"trade_date": pd.to_datetime(raw[date_column], errors="coerce")})
        calendar = calendar.loc[
            calendar["trade_date"].between(pd.Timestamp(start_date), pd.Timestamp(end_date))
        ].copy()
        calendar.insert(0, "exchange", "CN")
        calendar["is_trading_day"] = True
        return calendar.reset_index(drop=True)

    def fetch_corporate_actions(self, start_date: str, end_date: str) -> pd.DataFrame:
        raise SourceCapabilityError("use fetch_cninfo_corporate_actions_for_symbol for resumable corporate-action backfill")

    def fetch_cninfo_corporate_actions_for_symbol(
        self, symbol: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        code, _ = _split_hs_symbol(symbol)
        raw = (
            self._client.stock_dividend_cninfo(code)
            if self._client is not None
            else _fetch_cninfo_dividend_records(code, timeout_seconds=self.cninfo_timeout_seconds)
        )
        if raw.empty:
            return pd.DataFrame(columns=["symbol", "ex_date", "action_type", "per_10_shares"])
        return _normalize_cninfo_corporate_actions(raw, symbol, start_date, end_date)

    def fetch_security_status(self, start_date: str, end_date: str) -> pd.DataFrame:
        raise SourceCapabilityError("AKShare Sina security-status endpoint is not configured")

    def _get_client(self) -> Any:
        if self._client is None:
            import akshare

            self._client = akshare
        return self._client


def _first_column(frame: pd.DataFrame, *candidates: str) -> str:
    for name in candidates:
        if name in frame:
            return name
    raise ValueError(f"AKShare Sina response is missing columns: {', '.join(candidates)}")


def _split_hs_symbol(symbol: str) -> tuple[str, str]:
    code, separator, exchange = symbol.partition(".")
    if not separator or exchange not in {"SH", "SZ"}:
        raise ValueError(f"AKShare Sina only supports Shanghai/Shenzhen symbols: {symbol}")
    return code, exchange


def _normalize_security_master(
    frame: pd.DataFrame,
    *,
    code_column: str,
    name_column: str,
    listing_column: str,
    exchange: str,
    exit_column: str | None = None,
    exit_type: str | None = None,
) -> pd.DataFrame:
    selected = frame.loc[:, [code_column, name_column, listing_column]].rename(
        columns={code_column: "code", name_column: "security_name", listing_column: "listing_date"}
    )
    selected["code"] = selected["code"].astype(str).str.zfill(6)
    prefixes = AkshareSinaHsRawDataSource._SH_PREFIXES if exchange == "SH" else AkshareSinaHsRawDataSource._SZ_PREFIXES
    selected = selected.loc[selected["code"].str.startswith(prefixes)].copy()
    selected["exchange"] = exchange
    selected["symbol"] = selected["code"] + "." + exchange
    selected["listing_date"] = pd.to_datetime(selected["listing_date"], errors="coerce")
    if exit_column is None:
        selected["market_exit_date"] = pd.NaT
        selected["market_exit_type"] = pd.NA
    else:
        selected["market_exit_date"] = pd.to_datetime(frame.loc[selected.index, exit_column], errors="coerce")
        selected["market_exit_type"] = exit_type
    return selected.loc[:, ["symbol", "exchange", "security_name", "listing_date", "market_exit_date", "market_exit_type"]]


def _fetch_sina_price_history(symbol: str) -> pd.DataFrame:
    """Decode Sina's price payload when its optional share-amount API is unavailable."""
    import requests
    from akshare.stock.stock_zh_a_sina import hk_js_decode, zh_sina_a_stock_hist_url
    from py_mini_racer import MiniRacer

    response = requests.get(zh_sina_a_stock_hist_url.format(symbol), timeout=30)
    response.raise_for_status()
    encoded = response.text.partition("=")[2].partition(";")[0].replace('"', "")
    if not encoded:
        raise ValueError(f"Sina price history is empty for {symbol}")
    engine = MiniRacer()
    engine.eval(hk_js_decode)
    frame = pd.DataFrame(engine.call("d", encoded))
    required = ["date", "open", "high", "low", "close", "volume", "amount"]
    if set(required) - set(frame.columns):
        raise ValueError(f"Sina price history is missing columns for {symbol}")
    return frame.loc[:, required]


def _fetch_cninfo_dividend_records(code: str, *, timeout_seconds: float) -> pd.DataFrame:
    """Fetch the AKShare CNInfo payload with an explicit network timeout."""
    from akshare.stock.stock_dividend_cninfo import _get_file_content_ths
    from py_mini_racer import MiniRacer

    engine = MiniRacer()
    engine.eval(_get_file_content_ths("cninfo.js"))
    response = requests.post(
        "https://webapi.cninfo.com.cn/api/sysapi/p_sysapi1139",
        params={"scode": code},
        headers={
            "Accept": "*/*",
            "Accept-Enckey": engine.call("getResCode1"),
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Cache-Control": "no-cache",
            "Content-Length": "0",
            "Host": "webapi.cninfo.com.cn",
            "Origin": "http://webapi.cninfo.com.cn",
            "Pragma": "no-cache",
            "Referer": "http://webapi.cninfo.com.cn/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36",
            "X-Requested-With": "XMLHttpRequest",
        },
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    payload = response.json()
    records = payload.get("records") if isinstance(payload, dict) else None
    if records is None:
        raise ValueError("CNInfo dividend response is missing records")
    if not isinstance(records, list):
        raise ValueError("CNInfo dividend records must be a list")
    return pd.DataFrame(records).rename(
        columns={"F020D": "除权日", "F012N": "派息比例", "F010N": "送股比例", "F011N": "转增比例"}
    )


def _normalize_cninfo_corporate_actions(
    frame: pd.DataFrame, symbol: str, start_date: str, end_date: str
) -> pd.DataFrame:
    date_column = _first_column(frame, "除权日", "除权除息日")
    normalized = pd.DataFrame({"ex_date": pd.to_datetime(frame[date_column], errors="coerce")})
    normalized = normalized.loc[normalized["ex_date"].between(pd.Timestamp(start_date), pd.Timestamp(end_date))].copy()
    events: list[pd.DataFrame] = []
    for column, action_type in (("派息比例", "cash_dividend"), ("送股比例", "bonus_share"), ("转增比例", "capitalization")):
        if column not in frame:
            continue
        values = pd.to_numeric(frame.loc[normalized.index, column], errors="coerce")
        action = normalized.loc[values.gt(0)].copy()
        action["symbol"] = symbol
        action["action_type"] = action_type
        action["per_10_shares"] = values.loc[action.index].astype(float)
        events.append(action.loc[:, ["symbol", "ex_date", "action_type", "per_10_shares"]])
    if not events:
        return pd.DataFrame(columns=["symbol", "ex_date", "action_type", "per_10_shares"])
    return pd.concat(events, ignore_index=True).drop_duplicates(["symbol", "ex_date", "action_type"])
