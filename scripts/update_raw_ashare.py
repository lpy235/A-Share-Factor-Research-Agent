"""Create one daily child data version from an explicit local CSV snapshot."""

import argparse

from app.market_data.catalog import DataCatalog
from app.market_data.daily_update import DailyUpdateService
from app.market_data.quality import QualityGateService
from app.market_data.sources.csv_import import CsvRawDataSource
from app.market_data.store import MarketDataStore


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trade-date", required=True)
    parser.add_argument("--parent-version", required=True)
    parser.add_argument("--daily-bars-csv", required=True)
    parser.add_argument("--source", default="snapshot_csv")
    parser.add_argument("--warehouse", default="market_data")
    args = parser.parse_args()

    catalog = DataCatalog(args.warehouse)
    source = CsvRawDataSource.from_daily_bars_csv(args.daily_bars_csv, source=args.source)
    result = DailyUpdateService(
        catalog, MarketDataStore(args.warehouse), source, QualityGateService(catalog)
    ).run(args.trade_date, args.parent_version)
    print(f"status={result.status}")
    if result.data_version:
        print(f"data_version={result.data_version}")


if __name__ == "__main__":
    main()
