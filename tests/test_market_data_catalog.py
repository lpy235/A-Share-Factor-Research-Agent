import pytest

from app.market_data.catalog import DataCatalog


def test_catalog_publishes_an_immutable_data_version(tmp_path):
    catalog = DataCatalog(tmp_path)

    version = catalog.create_draft(source="fixture", as_of_date="2026-07-24")
    assert version.status == "draft"

    catalog.publish(version.version_id, manifest={"tables": {"raw_daily_bars": 10}})
    published = catalog.get_version(version.version_id)

    assert published.status == "published"
    assert published.manifest_hash
    with pytest.raises(ValueError, match="immutable"):
        catalog.publish(version.version_id, manifest={"tables": {"raw_daily_bars": 11}})


def test_catalog_records_quality_results_before_publication(tmp_path):
    catalog = DataCatalog(tmp_path)
    version = catalog.create_draft(source="fixture", as_of_date="2026-07-24")

    catalog.record_quality_result(
        version.version_id,
        check_name="raw_daily_bar_uniqueness",
        passed=True,
        affected_count=0,
        severity="hard",
    )

    results = catalog.list_quality_results(version.version_id)
    assert results[0].check_name == "raw_daily_bar_uniqueness"
    assert results[0].passed is True
