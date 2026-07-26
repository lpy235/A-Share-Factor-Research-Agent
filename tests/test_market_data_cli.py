import json

import pandas as pd
import pytest

import app.market_data.cli as market_data_cli
from app.market_data.catalog import DataCatalog
from app.market_data.cli import main
from app.market_data.store import MarketDataStore


def _formal_provenance_payload() -> dict:
    return {
        "schema_version": 1,
        "source_name": "authorized_export",
        "snapshot_ref": "internal-export-2020-01",
        "source_location": "internal://exports/2020-01",
        "authorization_basis": "internal research data authorization",
        "license_or_terms": "internal research use only",
        "coverage_start": "2020-01-01",
        "coverage_end": "2020-12-31",
        "universe_description": "A-share common stocks",
        "field_definition_ref": "internal-data-dictionary-v1",
        "price_adjustment": "none",
        "reviewed_by": "data-governance",
        "reviewed_at": "2026-07-25",
    }


def test_import_csv_publishes_a_version_with_snapshot_hashes(tmp_path, capsys):
    bars_path = tmp_path / "bars.csv"
    calendar_path = tmp_path / "calendar.csv"
    warehouse_root = tmp_path / "warehouse"
    pd.DataFrame(
        {
            "symbol": ["000001.SZ", "000002.SZ", "000001.SZ", "000002.SZ"],
            "trade_date": ["2020-01-02", "2020-01-02", "2020-01-03", "2020-01-03"],
            "open": [10.0, 20.0, 10.2, 20.2],
            "high": [10.5, 20.5, 10.6, 20.6],
            "low": [9.8, 19.8, 10.0, 20.0],
            "close": [10.2, 20.2, 10.4, 20.4],
            "volume": [1000, 2000, 1100, 2100],
            "amount": [10200, 40400, 11440, 42840],
        }
    ).to_csv(bars_path, index=False)
    pd.DataFrame({"trade_date": ["2020-01-02", "2020-01-03"]}).to_csv(calendar_path, index=False)

    exit_code = main(
        [
            "import-csv",
            "--csv", str(bars_path),
            "--calendar-csv", str(calendar_path),
            "--source", "authorized_export",
            "--snapshot-ref", "internal-export-2020-01",
            "--start-date", "2020-01-01",
            "--end-date", "2020-01-31",
            "--warehouse-root", str(warehouse_root),
            "--batch-size", "2",
        ]
    )

    result = json.loads(capsys.readouterr().out)
    manifest = DataCatalog(warehouse_root).get_manifest(result["data_version"])["manifest"]
    assert exit_code == 0
    assert result["status"] == "published"
    assert result["manifest_hash"]
    assert manifest["formal_baseline"] is False
    assert manifest["snapshot_ref"] == "internal-export-2020-01"
    assert len(manifest["daily_bars_file_sha256"]) == 64
    assert len(manifest["calendar_file_sha256"]) == 64


def test_import_csv_persists_reference_tables_and_their_hashes(tmp_path, capsys):
    bars_path = tmp_path / "bars.csv"
    calendar_path = tmp_path / "calendar.csv"
    master_path = tmp_path / "master.csv"
    status_path = tmp_path / "status.csv"
    actions_path = tmp_path / "actions.csv"
    provenance_path = tmp_path / "provenance.json"
    warehouse_root = tmp_path / "warehouse"
    pd.DataFrame(
        {
            "symbol": ["000001.SZ"], "trade_date": ["2020-01-02"], "open": [10.0],
            "high": [10.5], "low": [9.8], "close": [10.2], "volume": [1000], "amount": [10200],
        }
    ).to_csv(bars_path, index=False)
    pd.DataFrame({"trade_date": ["2020-01-02"], "is_trading_day": [True]}).to_csv(calendar_path, index=False)
    pd.DataFrame(
        {"symbol": ["000001.SZ"], "exchange": ["SZSE"], "security_name": ["Ping An Bank"], "listing_date": ["1991-04-03"]}
    ).to_csv(master_path, index=False)
    pd.DataFrame(
        {"symbol": ["000001.SZ"], "trade_date": ["2020-01-02"], "is_st": [False], "is_suspended": [False]}
    ).to_csv(status_path, index=False)
    pd.DataFrame(
        {"symbol": ["000001.SZ"], "ex_date": ["2020-01-02"], "action_type": ["cash_dividend"]}
    ).to_csv(actions_path, index=False)
    provenance_path.write_text(
        json.dumps(_formal_provenance_payload()),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "import-csv", "--csv", str(bars_path), "--calendar-csv", str(calendar_path),
            "--security-master-csv", str(master_path), "--security-status-csv", str(status_path),
            "--corporate-actions-csv", str(actions_path), "--source", "authorized_export",
            "--formal-baseline", "--provenance-json", str(provenance_path),
            "--snapshot-ref", "internal-export-2020-01", "--start-date", "2020-01-01",
            "--end-date", "2020-01-31", "--warehouse-root", str(warehouse_root),
        ]
    )

    result = json.loads(capsys.readouterr().out)
    manifest = DataCatalog(warehouse_root).get_manifest(result["data_version"])["manifest"]
    assert exit_code == 0
    assert manifest["reference_tables_required"] is True
    assert manifest["formal_baseline"] is True
    assert manifest["provenance"]["snapshot_ref"] == "internal-export-2020-01"
    assert len(manifest["provenance_file_sha256"]) == 64
    assert set(manifest["reference_table_file_sha256"]) == {
        "security_master", "security_status", "corporate_actions"
    }
    for table_name in ("security_master", "trading_calendar", "security_status", "corporate_actions"):
        table_dir = warehouse_root / "lake" / table_name / f"data_version={result['data_version']}"
        assert list(table_dir.rglob("*.parquet"))


def test_formal_baseline_requires_provenance_json(tmp_path):
    bars_path = tmp_path / "bars.csv"
    calendar_path = tmp_path / "calendar.csv"
    pd.DataFrame(
        {
            "symbol": ["000001.SZ"], "trade_date": ["2020-01-02"], "open": [10.0],
            "high": [10.5], "low": [9.8], "close": [10.2], "volume": [1000], "amount": [10200],
        }
    ).to_csv(bars_path, index=False)
    pd.DataFrame({"trade_date": ["2020-01-02"], "is_trading_day": [True]}).to_csv(calendar_path, index=False)

    with pytest.raises(ValueError, match="--formal-baseline requires --provenance-json"):
        main(
            [
                "import-csv", "--csv", str(bars_path), "--calendar-csv", str(calendar_path),
                "--formal-baseline", "--source", "authorized_export",
                "--snapshot-ref", "internal-export-2020-01", "--start-date", "2020-01-01",
                "--end-date", "2020-01-31", "--warehouse-root", str(tmp_path / "warehouse"),
            ]
        )


def test_formal_baseline_automatically_requires_reference_tables(tmp_path, capsys):
    bars_path = tmp_path / "bars.csv"
    calendar_path = tmp_path / "calendar.csv"
    provenance_path = tmp_path / "provenance.json"
    warehouse_root = tmp_path / "warehouse"
    pd.DataFrame(
        {
            "symbol": ["000001.SZ"], "trade_date": ["2020-01-02"], "open": [10.0],
            "high": [10.5], "low": [9.8], "close": [10.2], "volume": [1000], "amount": [10200],
        }
    ).to_csv(bars_path, index=False)
    pd.DataFrame({"trade_date": ["2020-01-02"], "is_trading_day": [True]}).to_csv(calendar_path, index=False)
    provenance_path.write_text(json.dumps(_formal_provenance_payload()), encoding="utf-8")

    exit_code = main(
        [
            "import-csv", "--csv", str(bars_path), "--calendar-csv", str(calendar_path),
            "--formal-baseline", "--provenance-json", str(provenance_path),
            "--source", "authorized_export", "--snapshot-ref", "internal-export-2020-01",
            "--start-date", "2020-01-01", "--end-date", "2020-01-31",
            "--warehouse-root", str(warehouse_root),
        ]
    )

    result = json.loads(capsys.readouterr().out)
    checks = {
        item.check_name: item
        for item in DataCatalog(warehouse_root).list_quality_results(result["data_version"])
    }
    assert exit_code == 1
    assert result["status"] == "quality_failed"
    for table_name in ("security_master", "security_status", "corporate_actions"):
        assert checks[f"{table_name}_required"].passed is False


def test_import_csv_requires_all_reference_tables_when_flag_is_enabled(tmp_path, capsys):
    bars_path = tmp_path / "bars.csv"
    calendar_path = tmp_path / "calendar.csv"
    warehouse_root = tmp_path / "warehouse"
    pd.DataFrame(
        {
            "symbol": ["000001.SZ"], "trade_date": ["2020-01-02"], "open": [10.0],
            "high": [10.5], "low": [9.8], "close": [10.2], "volume": [1000], "amount": [10200],
        }
    ).to_csv(bars_path, index=False)
    pd.DataFrame({"trade_date": ["2020-01-02"], "is_trading_day": [True]}).to_csv(calendar_path, index=False)

    exit_code = main(
        [
            "import-csv", "--csv", str(bars_path), "--calendar-csv", str(calendar_path),
            "--require-reference-tables", "--source", "authorized_export",
            "--snapshot-ref", "internal-export-2020-01", "--start-date", "2020-01-01",
            "--end-date", "2020-01-31", "--warehouse-root", str(warehouse_root),
        ]
    )

    result = json.loads(capsys.readouterr().out)
    catalog = DataCatalog(warehouse_root)
    checks = {item.check_name: item for item in catalog.list_quality_results(result["data_version"])}
    assert exit_code == 1
    assert result["status"] == "quality_failed"
    assert catalog.get_version(result["data_version"]).status == "draft"
    for table_name in ("security_master", "security_status", "corporate_actions"):
        assert checks[f"{table_name}_required"].passed is False


def test_akshare_sina_hs_backfill_cli_publishes_limited_research_baseline(tmp_path, capsys, monkeypatch):
    class FakeSinaSource:
        source_name = "akshare_sina_hs_active_research"

        def __init__(self, *, include_delisted=False):
            self.include_delisted = include_delisted

        def list_securities(self, as_of_date):
            return pd.DataFrame({"symbol": ["000001.SZ", "600000.SH"]})

        def fetch_daily_bars(self, symbols, start_date, end_date):
            return pd.DataFrame(
                {
                    "symbol": symbols,
                    "trade_date": ["2020-01-02"] * len(symbols),
                    "open": [10.0] * len(symbols),
                    "high": [10.5] * len(symbols),
                    "low": [9.9] * len(symbols),
                    "close": [10.3] * len(symbols),
                    "volume": [1000.0] * len(symbols),
                    "amount": [10300.0] * len(symbols),
                }
            )

        def fetch_calendar(self, start_date, end_date):
            return pd.DataFrame(
                {"exchange": ["CN"], "trade_date": ["2020-01-02"], "is_trading_day": [True]}
            )

        def fetch_security_master(self, as_of_date):
            del as_of_date
            return pd.DataFrame(
                {
                    "symbol": ["000001.SZ", "600000.SH"], "exchange": ["SZ", "SH"],
                    "security_name": ["SZ", "SH"], "listing_date": ["1991-04-03", "1999-11-10"],
                }
            )

    monkeypatch.setattr(market_data_cli, "AkshareSinaHsRawDataSource", FakeSinaSource)
    warehouse_root = tmp_path / "warehouse"

    exit_code = main(
        [
            "backfill-akshare-sina", "--start-date", "2020-01-01", "--end-date", "2020-01-31",
            "--warehouse-root", str(warehouse_root), "--batch-size", "1",
        ]
    )

    result = json.loads(capsys.readouterr().out)
    manifest = DataCatalog(warehouse_root).get_manifest(result["data_version"])["manifest"]
    assert exit_code == 0
    assert result["status"] == "published"
    assert manifest["source_channel"] == "akshare_stock_zh_a_daily_sina"
    assert "北京市场" in manifest["universe_limitations"]
    assert manifest["reference_table_partitions"]["trading_calendar"]
    assert manifest["reference_table_partitions"]["security_master"]


def test_corporate_action_cli_resumes_existing_draft_and_publishes_child(tmp_path, capsys, monkeypatch):
    class FakeCorporateActionSource:
        source_name = "akshare_sina_hs_active_research"
        corporate_actions_source_name = "akshare_stock_dividend_cninfo"

        def __init__(self, *, cninfo_timeout_seconds=30.0):
            self.cninfo_timeout_seconds = cninfo_timeout_seconds

        @staticmethod
        def fetch_cninfo_corporate_actions_for_symbol(symbol, start_date, end_date):
            del start_date, end_date
            return pd.DataFrame(
                {
                    "symbol": [symbol], "ex_date": ["2020-07-01"],
                    "action_type": ["cash_dividend"], "per_10_shares": [1.0],
                }
            )

    monkeypatch.setattr(market_data_cli, "AkshareSinaHsRawDataSource", FakeCorporateActionSource)
    warehouse_root = tmp_path / "warehouse"
    catalog = DataCatalog(warehouse_root)
    store = MarketDataStore(warehouse_root)
    parent = catalog.create_draft(source="parent_fixture", as_of_date="2020-12-31")
    store.write_raw_daily_bars(
        pd.DataFrame(
            {
                "symbol": ["000001.SZ"], "trade_date": ["2020-01-02"], "open": [10.0],
                "high": [10.5], "low": [9.8], "close": [10.2], "volume": [1000.0], "amount": [10200.0],
            }
        ),
        data_version=parent.version_id,
        source="parent_fixture",
    )
    store.write_security_master(
        pd.DataFrame(
            {"symbol": ["000001.SZ"], "exchange": ["SZ"], "security_name": ["SZ"], "listing_date": ["1991-04-03"]}
        ),
        data_version=parent.version_id,
        source="parent_fixture",
    )
    store.write_trading_calendar(
        pd.DataFrame({"exchange": ["CN"], "trade_date": ["2020-01-02"], "is_trading_day": [True]}),
        data_version=parent.version_id,
        source="parent_fixture",
    )
    catalog.publish(parent.version_id, manifest={})
    child = catalog.create_draft(source="akshare_stock_dividend_cninfo", as_of_date="2020-12-31")
    run = catalog.create_ingest_run(
        child.version_id,
        start_date="2020-01-01",
        end_date="2020-12-31",
        batch_size=1,
        symbols=["000001.SZ"],
    )
    catalog.update_ingest_run(run.ingest_run_id, next_symbol_index=0, status="paused")

    exit_code = main(
        [
            "backfill-corporate-actions-cninfo", "--parent-version-id", parent.version_id,
            "--start-date", "2020-01-01", "--end-date", "2020-12-31",
            "--warehouse-root", str(warehouse_root), "--resume-ingest-run-id", run.ingest_run_id,
        ]
    )

    result = json.loads(capsys.readouterr().out)
    manifest = catalog.get_manifest(child.version_id)["manifest"]
    assert exit_code == 0
    assert result["status"] == "published"
    assert result["parent_version_id"] == parent.version_id
    assert manifest["parent_version_id"] == parent.version_id
