import json

import pandas as pd

from app.market_data.catalog import DataCatalog
from app.market_data.cli import main


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
    assert manifest["snapshot_ref"] == "internal-export-2020-01"
    assert len(manifest["daily_bars_file_sha256"]) == 64
    assert len(manifest["calendar_file_sha256"]) == 64


def test_import_csv_persists_reference_tables_and_their_hashes(tmp_path, capsys):
    bars_path = tmp_path / "bars.csv"
    calendar_path = tmp_path / "calendar.csv"
    master_path = tmp_path / "master.csv"
    status_path = tmp_path / "status.csv"
    actions_path = tmp_path / "actions.csv"
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

    exit_code = main(
        [
            "import-csv", "--csv", str(bars_path), "--calendar-csv", str(calendar_path),
            "--security-master-csv", str(master_path), "--security-status-csv", str(status_path),
            "--corporate-actions-csv", str(actions_path), "--source", "authorized_export",
            "--snapshot-ref", "internal-export-2020-01", "--start-date", "2020-01-01",
            "--end-date", "2020-01-31", "--warehouse-root", str(warehouse_root),
        ]
    )

    result = json.loads(capsys.readouterr().out)
    manifest = DataCatalog(warehouse_root).get_manifest(result["data_version"])["manifest"]
    assert exit_code == 0
    assert set(manifest["reference_table_file_sha256"]) == {
        "security_master", "security_status", "corporate_actions"
    }
    for table_name in ("security_master", "trading_calendar", "security_status", "corporate_actions"):
        table_dir = warehouse_root / "lake" / table_name / f"data_version={result['data_version']}"
        assert list(table_dir.rglob("*.parquet"))
