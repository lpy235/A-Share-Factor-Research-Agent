import pandas as pd
import pytest

from app.market_data.catalog import DataCatalog
from app.market_data.quality import QualityGateService


def _bars() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "symbol": ["000001.SZ", "000002.SZ"],
            "trade_date": pd.to_datetime(["2020-01-02", "2020-01-02"]),
            "open": [10.0, 8.0],
            "high": [10.5, 8.4],
            "low": [9.9, 7.9],
            "close": [10.3, 8.2],
            "source": ["fixture", "fixture"],
            "ingested_at": ["2020-01-03T00:00:00+00:00"] * 2,
            "data_version": ["v1", "v1"],
            "adjustment": ["none", "none"],
        }
    )


def test_quality_gate_keeps_invalid_version_as_draft(tmp_path):
    catalog = DataCatalog(tmp_path)
    version = catalog.create_draft(source="fixture", as_of_date="2020-01-02")
    bars = _bars().assign(data_version=version.version_id, high=[9.0, 8.4])

    with pytest.raises(ValueError, match="quality gates failed"):
        QualityGateService(catalog).publish_if_valid(
            version.version_id, bars, expected_trading_dates=["2020-01-02"]
        )

    assert catalog.get_version(version.version_id).status == "draft"
    assert any(not result.passed for result in catalog.list_quality_results(version.version_id))


def test_quality_gate_publishes_manifest_only_after_all_hard_checks_pass(tmp_path):
    catalog = DataCatalog(tmp_path)
    version = catalog.create_draft(source="fixture", as_of_date="2020-01-02")
    bars = _bars().assign(data_version=version.version_id)

    published = QualityGateService(catalog).publish_if_valid(
        version.version_id, bars, expected_trading_dates=["2020-01-02"]
    )

    assert published.status == "published"
    assert published.manifest_hash
