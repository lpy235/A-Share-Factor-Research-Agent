"""Explicit operator entry point for a resumable local raw-data import."""

import argparse

from app.market_data.catalog import DataCatalog
from app.market_data.ingestion import BackfillService
from app.market_data.sources.csv_import import CsvRawDataSource
from app.market_data.store import MarketDataStore


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start")
    parser.add_argument("--end")
    parser.add_argument("--daily-bars-csv", required=True)
    parser.add_argument("--source", default="snapshot_csv")
    parser.add_argument("--resume-run-id")
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--warehouse", default="market_data")
    args = parser.parse_args()

    if not args.resume_run_id and (not args.start or not args.end):
        parser.error("--start and --end are required unless --resume-run-id is supplied")
    source = CsvRawDataSource.from_daily_bars_csv(args.daily_bars_csv, source=args.source)
    catalog = DataCatalog(args.warehouse)
    service = BackfillService(catalog, MarketDataStore(args.warehouse), source)
    result = (
        service.resume(args.resume_run_id)
        if args.resume_run_id
        else service.run(args.start, args.end, batch_size=args.batch_size)
    )
    print(f"draft_version={result.data_version}")
    print(f"ingest_run_id={result.ingest_run_id}")
    print(f"status={result.status}")
    print(f"completed_symbol_count={result.completed_symbol_count}")
    if result.status != "completed":
        print(
            "resume_command=make resume-raw-ashare "
            f"RUN_ID={result.ingest_run_id} DAILY_BARS_CSV={args.daily_bars_csv} SOURCE={args.source}"
        )


if __name__ == "__main__":
    main()
