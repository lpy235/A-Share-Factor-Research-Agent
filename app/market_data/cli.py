"""Local-only operations for the versioned raw daily-data warehouse."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from app.market_data.catalog import DataCatalog
from app.market_data.ingestion import BackfillService
from app.market_data.quality import QualityGateService
from app.market_data.sources.csv_import import CsvRawDataSource
from app.market_data.store import MarketDataStore


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "import-csv":
        return _import_csv(args)
    parser.error(f"unsupported command: {args.command}")
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="A-share raw daily-data warehouse operations")
    subparsers = parser.add_subparsers(dest="command", required=True)
    importer = subparsers.add_parser("import-csv", help="quality-gate and publish an authorized local CSV snapshot")
    importer.add_argument("--csv", required=True, type=Path, help="raw daily-bar CSV")
    importer.add_argument("--calendar-csv", required=True, type=Path, help="trading-calendar CSV")
    importer.add_argument("--source", required=True, help="auditable source name")
    importer.add_argument("--snapshot-ref", required=True, help="export batch, URL, Git commit, or Release reference")
    importer.add_argument("--start-date", required=True, help="inclusive YYYY-MM-DD")
    importer.add_argument("--end-date", required=True, help="inclusive YYYY-MM-DD")
    importer.add_argument("--warehouse-root", default="market_data", type=Path)
    importer.add_argument("--batch-size", default=100, type=int)
    importer.add_argument("--max-retries", default=0, type=int)
    return parser


def _import_csv(args: argparse.Namespace) -> int:
    source = CsvRawDataSource.from_daily_bars_csv(args.csv, source=args.source)
    expected_dates = _read_expected_trading_dates(args.calendar_csv, args.start_date, args.end_date)
    root = args.warehouse_root
    catalog = DataCatalog(root)
    service = BackfillService(
        catalog,
        MarketDataStore(root),
        source,
        max_retries=args.max_retries,
        quality_gate=QualityGateService(catalog),
        expected_trading_dates=expected_dates,
        manifest_context={
            "snapshot_ref": args.snapshot_ref,
            "daily_bars_file_sha256": _sha256(args.csv),
            "calendar_file_sha256": _sha256(args.calendar_csv),
        },
    )
    result = service.run(args.start_date, args.end_date, batch_size=args.batch_size)
    version = catalog.get_version(result.data_version)
    print(
        json.dumps(
            {
                "ingest_run_id": result.ingest_run_id,
                "data_version": result.data_version,
                "status": result.status,
                "manifest_hash": version.manifest_hash,
            },
            ensure_ascii=False,
        )
    )
    return 0 if result.status == "published" else 1


def _read_expected_trading_dates(path: Path, start_date: str, end_date: str) -> list[str]:
    calendar = pd.read_csv(path)
    if "trade_date" not in calendar:
        raise ValueError("calendar CSV must contain trade_date")
    dates = pd.to_datetime(calendar["trade_date"], errors="coerce")
    if dates.isna().any():
        raise ValueError("calendar CSV contains invalid trade_date")
    if "is_trading_day" in calendar:
        values = calendar["is_trading_day"]
        calendar = calendar.loc[values.astype(str).str.lower().isin({"true", "1", "yes"})]
        dates = pd.to_datetime(calendar["trade_date"])
    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    expected = sorted({date.strftime("%Y-%m-%d") for date in dates if start <= date <= end})
    if not expected:
        raise ValueError("calendar CSV has no trading dates in the requested range")
    return expected


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
