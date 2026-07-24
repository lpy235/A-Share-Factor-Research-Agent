import pandas as pd
import pytest

from app.market_data.store import MarketDataStore


@pytest.fixture
def raw_bars() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "symbol": ["000001.SZ", "000001.SZ", "600000.SH"],
            "trade_date": ["2020-01-02", "2020-01-03", "2021-01-04"],
            "open": [10.0, 10.2, 8.0],
            "high": [10.5, 10.6, 8.4],
            "low": [9.9, 10.1, 7.9],
            "close": [10.3, 10.4, 8.2],
            "volume": [1000.0, 1100.0, 1200.0],
            "amount": [10300.0, 11440.0, 9840.0],
        }
    )


def test_store_writes_unadjusted_daily_bars_with_lineage(tmp_path, raw_bars):
    store = MarketDataStore(tmp_path)

    paths = store.write_raw_daily_bars(raw_bars, data_version="v1", source="fixture")
    loaded = store.read_raw_daily_bars("v1", "2020-01-01", "2020-12-31")

    assert len(paths) == 2
    assert all(path.exists() for path in paths)
    assert list(loaded["trade_date"].dt.strftime("%Y-%m-%d")) == ["2020-01-02", "2020-01-03"]
    assert {"source", "ingested_at", "data_version", "adjustment"} <= set(loaded.columns)
    assert loaded["source"].eq("fixture").all()
    assert loaded["data_version"].eq("v1").all()
    assert loaded["adjustment"].eq("none").all()
    assert loaded["ingested_at"].notna().all()


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda frame: frame.assign(adjustment="qfq"), "caller-supplied lineage"),
        (lambda frame: pd.concat([frame, frame.iloc[[0]]], ignore_index=True), "duplicate"),
        (lambda frame: frame.assign(low=11.0), "OHLC"),
    ],
)
def test_store_rejects_invalid_or_adjusted_raw_bars(tmp_path, raw_bars, mutate, message):
    store = MarketDataStore(tmp_path)

    with pytest.raises(ValueError, match=message):
        store.write_raw_daily_bars(mutate(raw_bars), data_version="v1", source="fixture")


def test_store_writes_versioned_reference_and_event_tables(tmp_path):
    store = MarketDataStore(tmp_path)

    paths = [
        store.write_security_master(
            pd.DataFrame(
                {
                    "symbol": ["000001.SZ"],
                    "exchange": ["SZSE"],
                    "security_name": ["Ping An Bank"],
                    "listing_date": ["1991-04-03"],
                }
            ),
            data_version="v1",
            source="fixture",
        ),
        store.write_trading_calendar(
            pd.DataFrame(
                {"exchange": ["SZSE"], "trade_date": ["2020-01-02"], "is_trading_day": [True]}
            ),
            data_version="v1",
            source="fixture",
        ),
        *store.write_corporate_actions(
            pd.DataFrame(
                {"symbol": ["000001.SZ"], "ex_date": ["2020-07-01"], "action_type": ["cash_dividend"]}
            ),
            data_version="v1",
            source="fixture",
        ),
        *store.write_security_status(
            pd.DataFrame(
                {
                    "symbol": ["000001.SZ"],
                    "trade_date": ["2020-01-02"],
                    "is_st": [False],
                    "is_suspended": [False],
                }
            ),
            data_version="v1",
            source="fixture",
        ),
    ]

    assert all(path.exists() for path in paths)
    for path in paths:
        saved = pd.read_parquet(path)
        assert {"source", "ingested_at", "data_version"} <= set(saved.columns)
        assert saved["data_version"].eq("v1").all()
