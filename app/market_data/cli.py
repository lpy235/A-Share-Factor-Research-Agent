"""Local-only operations for the versioned raw daily-data warehouse."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from app.market_data.catalog import DataCatalog
from app.market_data.ingestion import BackfillService, CorporateActionBackfillService
from app.market_data.provenance import load_formal_baseline_provenance
from app.market_data.quality import QualityGateService
from app.market_data.sources.csv_import import CsvRawDataSource
from app.market_data.sources.akshare_sina_hs import AkshareSinaHsRawDataSource
from app.market_data.store import MarketDataStore


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "import-csv":
        return _import_csv(args)
    if args.command == "backfill-akshare-sina":
        return _backfill_akshare_sina(args)
    if args.command == "backfill-corporate-actions-cninfo":
        return _backfill_corporate_actions_cninfo(args)
    parser.error(f"unsupported command: {args.command}")
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="A-share raw daily-data warehouse operations")
    subparsers = parser.add_subparsers(dest="command", required=True)
    importer = subparsers.add_parser("import-csv", help="quality-gate and publish an authorized local CSV snapshot")
    importer.add_argument("--csv", required=True, type=Path, help="raw daily-bar CSV")
    importer.add_argument("--calendar-csv", required=True, type=Path, help="trading-calendar CSV")
    importer.add_argument("--calendar-exchange", default="CN", help="calendar exchange when CSV omits exchange")
    importer.add_argument("--security-master-csv", type=Path, help="optional security-master CSV")
    importer.add_argument("--security-status-csv", type=Path, help="optional ST/suspension status CSV")
    importer.add_argument("--corporate-actions-csv", type=Path, help="optional corporate-actions CSV")
    importer.add_argument(
        "--require-reference-tables",
        action="store_true",
        help="reject publication unless security master, calendar, status, and corporate-actions tables are supplied",
    )
    importer.add_argument(
        "--formal-baseline",
        action="store_true",
        help="require provenance evidence and all reference tables for a formal full-market baseline",
    )
    importer.add_argument(
        "--provenance-json",
        type=Path,
        help="local provenance JSON required with --formal-baseline",
    )
    importer.add_argument("--source", required=True, help="auditable source name")
    importer.add_argument("--snapshot-ref", required=True, help="export batch, URL, Git commit, or Release reference")
    importer.add_argument("--start-date", required=True, help="inclusive YYYY-MM-DD")
    importer.add_argument("--end-date", required=True, help="inclusive YYYY-MM-DD")
    importer.add_argument("--warehouse-root", default="market_data", type=Path)
    importer.add_argument("--batch-size", default=100, type=int)
    importer.add_argument("--max-retries", default=0, type=int)

    sina_backfill = subparsers.add_parser(
        "backfill-akshare-sina",
        help="backfill currently listed Shanghai/Shenzhen A-shares from AKShare's Sina raw-price endpoint",
    )
    sina_backfill.add_argument("--start-date", required=True, help="inclusive YYYY-MM-DD")
    sina_backfill.add_argument("--end-date", required=True, help="inclusive YYYY-MM-DD")
    sina_backfill.add_argument("--warehouse-root", default="market_data", type=Path)
    sina_backfill.add_argument("--batch-size", default=25, type=int)
    sina_backfill.add_argument("--max-retries", default=2, type=int)
    sina_backfill.add_argument(
        "--stop-after-batches",
        type=int,
        help="pause after this many batches; use --resume-ingest-run-id to continue",
    )
    sina_backfill.add_argument(
        "--resume-ingest-run-id",
        help="resume a prior backfill-akshare-sina ingest run in the same warehouse",
    )
    sina_backfill.add_argument(
        "--include-delisted",
        action="store_true",
        help="include Shanghai/Shenzhen A-shares from exchange delisting or suspension lists",
    )

    actions_backfill = subparsers.add_parser(
        "backfill-corporate-actions-cninfo",
        help="resumable backfill of CNInfo cash-dividend, bonus-share, and capitalization events",
    )
    actions_backfill.add_argument("--parent-version-id", required=True, help="published raw-bar parent version")
    actions_backfill.add_argument("--start-date", required=True, help="inclusive YYYY-MM-DD")
    actions_backfill.add_argument("--end-date", required=True, help="inclusive YYYY-MM-DD")
    actions_backfill.add_argument("--warehouse-root", default="market_data", type=Path)
    actions_backfill.add_argument("--batch-size", default=25, type=int)
    actions_backfill.add_argument("--max-retries", default=2, type=int)
    actions_backfill.add_argument("--request-timeout-seconds", default=30.0, type=float)
    actions_backfill.add_argument("--stop-after-batches", type=int)
    actions_backfill.add_argument("--resume-ingest-run-id")
    return parser


def _import_csv(args: argparse.Namespace) -> int:
    provenance = _read_formal_baseline_provenance(args)
    source = CsvRawDataSource.from_daily_bars_csv(args.csv, source=args.source)
    expected_dates = _read_expected_trading_dates(args.calendar_csv, args.start_date, args.end_date)
    reference_tables, reference_hashes = _read_reference_tables(args)
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
            "reference_table_file_sha256": reference_hashes,
            "formal_baseline": args.formal_baseline,
            **(
                {
                    "provenance": provenance,
                    "provenance_file_sha256": _sha256(args.provenance_json),
                }
                if provenance is not None
                else {}
            ),
        },
        reference_tables=reference_tables,
        required_reference_tables=args.require_reference_tables or args.formal_baseline,
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


def _read_formal_baseline_provenance(args: argparse.Namespace) -> dict | None:
    if args.formal_baseline:
        if args.provenance_json is None:
            raise ValueError("--formal-baseline requires --provenance-json")
        return load_formal_baseline_provenance(
            args.provenance_json,
            source_name=args.source,
            snapshot_ref=args.snapshot_ref,
            start_date=args.start_date,
            end_date=args.end_date,
        )
    if args.provenance_json is not None:
        raise ValueError("--provenance-json requires --formal-baseline")
    return None


def _backfill_akshare_sina(args: argparse.Namespace) -> int:
    source = AkshareSinaHsRawDataSource(include_delisted=args.include_delisted)
    calendar = source.fetch_calendar(args.start_date, args.end_date).copy()
    security_master = source.fetch_security_master(args.end_date)
    calendar["trade_date"] = pd.to_datetime(calendar["trade_date"], errors="raise")
    if calendar.empty:
        raise ValueError("AKShare Sina calendar has no trading dates in the requested range")
    expected_dates = calendar.loc[calendar["is_trading_day"], "trade_date"].dt.strftime("%Y-%m-%d").tolist()
    root = args.warehouse_root
    catalog = DataCatalog(root)
    universe_scope = "沪深交易所当前在市及退出/暂停上市 A 股" if args.include_delisted else "沪深交易所当前在市 A 股"
    universe_limitations = (
        "不含北京市场；交易所退出清单是当前快照，不能替代完整逐日证券状态；"
        "仅限本机研究，不构成正式授权全 A 股基线。"
        if args.include_delisted
        else "不含北京市场；证券清单来自当前可得列表，可能缺失已退市证券，"
        "存在幸存者偏差；仅限本机研究，不构成正式授权全 A 股基线。"
    )
    service = BackfillService(
        catalog,
        MarketDataStore(root),
        source,
        max_retries=args.max_retries,
        quality_gate=QualityGateService(catalog),
        expected_trading_dates=expected_dates,
        manifest_context={
            "source_channel": "akshare_stock_zh_a_daily_sina",
            "akshare_version": _akshare_version(),
            "universe_scope": universe_scope,
            "universe_limitations": universe_limitations,
        },
        reference_tables={"trading_calendar": calendar, "security_master": security_master},
    )
    if args.resume_ingest_run_id:
        result = service.resume(args.resume_ingest_run_id, stop_after_batches=args.stop_after_batches)
    else:
        result = service.run(
            args.start_date,
            args.end_date,
            batch_size=args.batch_size,
            stop_after_batches=args.stop_after_batches,
        )
    version = catalog.get_version(result.data_version)
    print(
        json.dumps(
            {
                "ingest_run_id": result.ingest_run_id,
                "data_version": result.data_version,
                "status": result.status,
                "manifest_hash": version.manifest_hash,
                "universe_scope": universe_scope,
            },
            ensure_ascii=False,
        )
    )
    return 0 if result.status in {"paused", "published"} else 1


def _backfill_corporate_actions_cninfo(args: argparse.Namespace) -> int:
    root = args.warehouse_root
    catalog = DataCatalog(root)
    source = AkshareSinaHsRawDataSource(cninfo_timeout_seconds=args.request_timeout_seconds)
    service = CorporateActionBackfillService(
        catalog,
        MarketDataStore(root),
        source,
        max_retries=args.max_retries,
    )
    if args.resume_ingest_run_id:
        result = service.resume(
            args.resume_ingest_run_id,
            parent_version_id=args.parent_version_id,
            stop_after_batches=args.stop_after_batches,
        )
    else:
        result = service.run(
            parent_version_id=args.parent_version_id,
            start_date=args.start_date,
            end_date=args.end_date,
            batch_size=args.batch_size,
            stop_after_batches=args.stop_after_batches,
        )
    if result.status == "completed":
        result = service.publish(result.ingest_run_id)
    version = catalog.get_version(result.data_version)
    print(
        json.dumps(
            {
                "ingest_run_id": result.ingest_run_id,
                "data_version": result.data_version,
                "parent_version_id": result.parent_version_id,
                "status": result.status,
                "completed_symbols": result.completed_symbol_count,
                "total_symbols": len(result.symbols),
                "manifest_hash": version.manifest_hash,
                "failed_symbols": len(catalog.list_ingest_errors(result.ingest_run_id)),
            },
            ensure_ascii=False,
        )
    )
    return 0 if result.status in {"paused", "published"} else 1


def _akshare_version() -> str:
    import akshare

    return str(akshare.__version__)


def _read_reference_tables(args: argparse.Namespace) -> tuple[dict[str, pd.DataFrame], dict[str, str]]:
    calendar = pd.read_csv(args.calendar_csv)
    if "is_trading_day" not in calendar:
        calendar["is_trading_day"] = True
    if "exchange" not in calendar:
        calendar["exchange"] = args.calendar_exchange
    tables = {"trading_calendar": calendar}
    hashes: dict[str, str] = {}
    for table_name, path in {
        "security_master": args.security_master_csv,
        "security_status": args.security_status_csv,
        "corporate_actions": args.corporate_actions_csv,
    }.items():
        if path is not None:
            tables[table_name] = pd.read_csv(path)
            hashes[table_name] = _sha256(path)
    return tables, hashes


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
