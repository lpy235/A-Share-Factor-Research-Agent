from dataclasses import dataclass


@dataclass(frozen=True)
class DataVersion:
    version_id: str
    source: str
    as_of_date: str
    status: str
    created_at: str
    published_at: str | None = None
    manifest_hash: str | None = None


@dataclass(frozen=True)
class QualityResult:
    version_id: str
    check_name: str
    passed: bool
    affected_count: int
    severity: str
    recorded_at: str
