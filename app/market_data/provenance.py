"""Validation for the local evidence required by a formal data baseline."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path


_REQUIRED_FIELDS = {
    "schema_version",
    "source_name",
    "snapshot_ref",
    "source_location",
    "authorization_basis",
    "license_or_terms",
    "coverage_start",
    "coverage_end",
    "universe_description",
    "field_definition_ref",
    "price_adjustment",
    "reviewed_by",
    "reviewed_at",
}


def load_formal_baseline_provenance(
    path: str | Path,
    *,
    source_name: str,
    snapshot_ref: str,
    start_date: str,
    end_date: str,
) -> dict:
    """Load and validate operator-supplied provenance for a formal baseline.

    This validates that auditable evidence has been supplied. It cannot verify
    the truth or legal sufficiency of the referenced authorization materials.
    """
    provenance_path = Path(path)
    try:
        payload = json.loads(provenance_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"provenance JSON does not exist: {provenance_path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"provenance JSON is invalid: {provenance_path}") from exc

    if not isinstance(payload, dict):
        raise ValueError("provenance JSON must be an object")
    missing = sorted(_REQUIRED_FIELDS - set(payload))
    if missing:
        raise ValueError(f"provenance JSON missing required fields: {', '.join(missing)}")
    empty = sorted(
        name for name in _REQUIRED_FIELDS - {"schema_version"} if not str(payload[name]).strip()
    )
    if empty:
        raise ValueError(f"provenance JSON has empty required fields: {', '.join(empty)}")
    if payload["schema_version"] != 1:
        raise ValueError("provenance schema_version must be 1")
    if payload["source_name"] != source_name:
        raise ValueError("provenance source_name must match --source")
    if payload["snapshot_ref"] != snapshot_ref:
        raise ValueError("provenance snapshot_ref must match --snapshot-ref")
    if payload["price_adjustment"] != "none":
        raise ValueError("provenance price_adjustment must be 'none'")

    coverage_start = _parse_date(payload["coverage_start"], "coverage_start")
    coverage_end = _parse_date(payload["coverage_end"], "coverage_end")
    requested_start = _parse_date(start_date, "requested start_date")
    requested_end = _parse_date(end_date, "requested end_date")
    _parse_date(payload["reviewed_at"], "reviewed_at")
    if coverage_start > coverage_end:
        raise ValueError("provenance coverage_start must not be after coverage_end")
    if requested_start > requested_end:
        raise ValueError("requested start_date must not be after end_date")
    if coverage_start > requested_start or coverage_end < requested_end:
        raise ValueError("provenance coverage must include the requested import date range")
    return payload


def _parse_date(value: object, field_name: str) -> date:
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValueError(f"provenance {field_name} must use YYYY-MM-DD") from exc
