"""Explicit operator entry point for a resumable unadjusted A-share backfill."""

import argparse

from app.market_data.catalog import DataCatalog
from app.market_data.ingestion import BackfillService
from app.market_data.sources.akshare_raw import AkshareRawDataSource
from app.market_data.store import MarketDataStore


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--warehouse", default="market_data")
    args = parser.parse_args()

    catalog = DataCatalog(args.warehouse)
    service = BackfillService(catalog, MarketDataStore(args.warehouse), AkshareRawDataSource())
    result = service.run(args.start, args.end, batch_size=args.batch_size)
    print(f"draft_version={result.data_version}")
    print(f"ingest_run_id={result.ingest_run_id}")
    print(f"status={result.status}")
    print(f"completed_symbol_count={result.completed_symbol_count}")
    if result.status != "completed":
        print(f"resume_command=make resume-raw-ashare RUN_ID={result.ingest_run_id}")


if __name__ == "__main__":
    main()
