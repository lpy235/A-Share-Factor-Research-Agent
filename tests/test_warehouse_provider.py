import pandas as pd
import pytest

from app.data.warehouse_provider import WarehouseAshareDataProvider
from app.market_data.catalog import DataCatalog
from app.market_data.store import MarketDataStore


def test_warehouse_provider_requires_a_published_version(tmp_path):
    catalog = DataCatalog(tmp_path)
    draft = catalog.create_draft(source="fixture", as_of_date="2020-01-02")

    with pytest.raises(ValueError, match="published"):
        WarehouseAshareDataProvider(draft.version_id, warehouse_root=tmp_path)


def test_warehouse_provider_reads_pinned_raw_daily_bars(tmp_path):
    catalog = DataCatalog(tmp_path)
    version = catalog.create_draft(source="fixture", as_of_date="2020-01-02")
    MarketDataStore(tmp_path).write_raw_daily_bars(
        pd.DataFrame(
            {
                "symbol": ["000001.SZ"], "trade_date": ["2020-01-02"], "open": [10.0],
                "high": [10.5], "low": [9.9], "close": [10.3], "volume": [1000.0], "amount": [10300.0],
            }
        ),
        data_version=version.version_id,
        source="fixture",
    )
    published = catalog.publish(version.version_id, manifest={"tables": {}})

    provider = WarehouseAshareDataProvider(published.version_id, warehouse_root=tmp_path)
    bars = provider.get_daily_bars(["000001.SZ"], "2020-01-01", "2020-01-02")

    assert bars.index.names == ["symbol", "date"]
    assert bars.loc[("000001.SZ", pd.Timestamp("2020-01-02")), "close"] == 10.3
    assert provider.diagnostics["manifest_hash"] == published.manifest_hash


def test_warehouse_provider_uses_first_available_trading_day_for_non_trading_start(tmp_path):
    catalog = DataCatalog(tmp_path)
    version = catalog.create_draft(source="fixture", as_of_date="2020-01-02")
    MarketDataStore(tmp_path).write_raw_daily_bars(
        pd.DataFrame(
            {
                "symbol": ["000001.SZ", "600000.SH"], "trade_date": ["2020-01-02", "2020-01-02"],
                "open": [10.0, 8.0], "high": [10.5, 8.5], "low": [9.9, 7.9], "close": [10.3, 8.2],
                "volume": [1000.0, 1200.0], "amount": [10300.0, 9840.0],
            }
        ),
        data_version=version.version_id,
        source="fixture",
    )
    published = catalog.publish(version.version_id, manifest={"tables": {}})

    universe = WarehouseAshareDataProvider(
        published.version_id, warehouse_root=tmp_path
    ).get_universe("CSI300", "2020-01-01")

    assert universe == ["000001.SZ", "600000.SH"]


def test_warehouse_provider_derives_prices_from_effective_corporate_actions(tmp_path):
    catalog = DataCatalog(tmp_path)
    store = MarketDataStore(tmp_path)
    version = catalog.create_draft(source="fixture", as_of_date="2020-01-04")
    store.write_raw_daily_bars(
        pd.DataFrame(
            {
                "symbol": ["000001.SZ"] * 3,
                "trade_date": ["2020-01-02", "2020-01-03", "2020-01-04"],
                "open": [100.0, 90.0, 91.0],
                "high": [101.0, 91.0, 92.0],
                "low": [99.0, 89.0, 90.0],
                "close": [100.0, 90.0, 91.0],
                "volume": [1000.0, 1100.0, 1200.0],
                "amount": [100000.0, 99000.0, 109200.0],
            }
        ),
        data_version=version.version_id,
        source="fixture",
    )
    store.write_corporate_actions(
        pd.DataFrame(
            {
                "symbol": ["000001.SZ"],
                "ex_date": ["2020-01-03"],
                "action_type": ["cash_dividend"],
                "per_10_shares": [1.0],
            }
        ),
        data_version=version.version_id,
        source="fixture",
    )
    published = catalog.publish(version.version_id, manifest={})

    adjusted = WarehouseAshareDataProvider(published.version_id, warehouse_root=tmp_path)
    raw = WarehouseAshareDataProvider(
        published.version_id, warehouse_root=tmp_path, price_adjustment_mode="raw"
    )

    adjusted_bars = adjusted.get_daily_bars(["000001.SZ"], "2020-01-02", "2020-01-04")
    raw_bars = raw.get_daily_bars(["000001.SZ"], "2020-01-02", "2020-01-04")

    assert adjusted_bars.loc[("000001.SZ", pd.Timestamp("2020-01-02")), "close"] == pytest.approx(99.9)
    assert raw_bars.loc[("000001.SZ", pd.Timestamp("2020-01-02")), "close"] == 100.0
    assert adjusted.diagnostics["applied_event_count"] == 1
