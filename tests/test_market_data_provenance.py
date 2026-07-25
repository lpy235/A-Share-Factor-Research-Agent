import json

import pytest

from app.market_data.provenance import load_formal_baseline_provenance


def _provenance() -> dict:
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


def test_formal_provenance_requires_unadjusted_price_and_matching_import_scope(tmp_path):
    path = tmp_path / "provenance.json"
    payload = _provenance() | {"price_adjustment": "forward"}
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="price_adjustment must be 'none'"):
        load_formal_baseline_provenance(
            path,
            source_name="authorized_export",
            snapshot_ref="internal-export-2020-01",
            start_date="2020-01-01",
            end_date="2020-12-31",
        )


def test_formal_provenance_returns_validated_payload(tmp_path):
    path = tmp_path / "provenance.json"
    payload = _provenance()
    path.write_text(json.dumps(payload), encoding="utf-8")

    assert load_formal_baseline_provenance(
        path,
        source_name="authorized_export",
        snapshot_ref="internal-export-2020-01",
        start_date="2020-01-01",
        end_date="2020-12-31",
    ) == payload
