import pandas as pd
from fastapi.testclient import TestClient

from app.main import app
from app.market_data.catalog import DataCatalog
from app.market_data.quality import QualityGateService
from app.market_data.store import MarketDataStore


def test_research_run_records_a_published_market_data_version(tmp_path):
    dates = pd.date_range("2020-01-01", "2020-12-31", freq="B")
    rows = []
    for symbol, base in [("000001.SZ", 10.0), ("000002.SZ", 20.0)]:
        for index, date in enumerate(dates):
            close = base + index * (0.03 if symbol == "000001.SZ" else -0.01)
            rows.append(
                {
                    "symbol": symbol,
                    "trade_date": date,
                    "open": close * 0.999,
                    "high": close * 1.01,
                    "low": close * 0.99,
                    "close": close,
                    "volume": 100_000 + index,
                    "amount": close * (100_000 + index),
                }
            )
    catalog = DataCatalog(tmp_path)
    version = catalog.create_draft(source="rehearsal_csv", as_of_date="2020-12-31")
    store = MarketDataStore(tmp_path)
    store.write_raw_daily_bars(pd.DataFrame(rows), data_version=version.version_id, source="rehearsal_csv")
    published = QualityGateService(catalog).publish_if_valid(
        version.version_id, store.read_raw_daily_bars(version.version_id, "2020-01-01", "2020-12-31"),
        expected_trading_dates=dates.strftime("%Y-%m-%d"), total_symbol_count=2,
    )

    response = TestClient(app).post(
        "/research/runs",
        json={
            "research_topic": "日频演练",
            "source_mode": "upload",
            "data_provider": "warehouse",
            "data_version": published.version_id,
            "market_data_root": str(tmp_path),
            "start_date": "2020-01-01",
            "end_date": "2020-12-31",
            "cache_enabled": False,
            "fallback_to_fixture": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["backtest_assumptions"]["data_version"] == published.version_id
    assert body["backtest_assumptions"]["manifest_hash"] == published.manifest_hash
    assert published.version_id in body["report_markdown"]
