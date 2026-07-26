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


@dataclass(frozen=True)
class IngestRun:
    ingest_run_id: str
    data_version: str
    start_date: str
    end_date: str
    batch_size: int
    symbols: tuple[str, ...]
    next_symbol_index: int
    status: str
    created_at: str
    parent_version_id: str | None = None

    @property
    def completed_symbol_count(self) -> int:
        return self.next_symbol_index


@dataclass(frozen=True)
class IngestError:
    ingest_run_id: str
    symbol: str
    error_message: str
    attempt_count: int
    recorded_at: str


@dataclass(frozen=True)
class IngestSymbolProgress:
    ingest_run_id: str
    symbol: str
    symbol_index: int
    status: str
    action_count: int
    completed_at: str
