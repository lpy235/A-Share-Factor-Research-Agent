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
