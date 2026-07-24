import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import duckdb

from app.market_data.models import DataVersion, IngestError, IngestRun, QualityResult
from app.market_data.paths import MarketDataPaths


class DataCatalog:
    """Tracks immutable market-data versions and their quality evidence."""

    def __init__(self, root: str | Path = "market_data") -> None:
        self.paths = MarketDataPaths(root)
        self.paths.root.mkdir(parents=True, exist_ok=True)
        self.paths.manifest_dir.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    def create_draft(self, *, source: str, as_of_date: str) -> DataVersion:
        if not source.strip():
            raise ValueError("source is required")
        created_at = _now()
        version_id = f"v{as_of_date.replace('-', '')}_{uuid4().hex[:8]}"
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO data_versions(version_id, source, as_of_date, status, created_at)
                VALUES (?, ?, ?, 'draft', ?)
                """,
                [version_id, source, as_of_date, created_at],
            )
        return self.get_version(version_id)

    def publish(self, version_id: str, *, manifest: dict) -> DataVersion:
        version = self.get_version(version_id)
        if version.status != "draft":
            raise ValueError("data version is immutable after publication")
        manifest_payload = {
            "version_id": version_id,
            "source": version.source,
            "as_of_date": version.as_of_date,
            "manifest": manifest,
        }
        encoded = json.dumps(manifest_payload, ensure_ascii=False, sort_keys=True)
        manifest_hash = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        manifest_path = self.paths.manifest_dir / f"{version_id}.json"
        manifest_path.write_text(encoded, encoding="utf-8")
        published_at = _now()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE data_versions
                SET status = 'published', published_at = ?, manifest_hash = ?
                WHERE version_id = ?
                """,
                [published_at, manifest_hash, version_id],
            )
        return self.get_version(version_id)

    def get_version(self, version_id: str) -> DataVersion:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT version_id, source, as_of_date, status, created_at, published_at, manifest_hash
                FROM data_versions WHERE version_id = ?
                """,
                [version_id],
            ).fetchone()
        if row is None:
            raise KeyError(f"unknown data version: {version_id}")
        return DataVersion(*row)

    def get_manifest(self, version_id: str) -> dict:
        manifest_path = self.paths.manifest_dir / f"{version_id}.json"
        if not manifest_path.exists():
            raise KeyError(f"no manifest for data version: {version_id}")
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    def has_published_child(self, parent_version_id: str, update_date: str) -> bool:
        with self._connect() as conn:
            rows = conn.execute("SELECT version_id FROM data_versions WHERE status = 'published'").fetchall()
        for (version_id,) in rows:
            manifest = self.get_manifest(version_id)
            context = manifest.get("manifest", {})
            if context.get("parent_version_id") == parent_version_id and context.get("update_date") == update_date:
                return True
        return False

    def record_quality_result(
        self,
        version_id: str,
        *,
        check_name: str,
        passed: bool,
        affected_count: int,
        severity: str,
    ) -> QualityResult:
        self.get_version(version_id)
        if affected_count < 0:
            raise ValueError("affected_count must be non-negative")
        recorded_at = _now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO quality_results(version_id, check_name, passed, affected_count, severity, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [version_id, check_name, passed, affected_count, severity, recorded_at],
            )
        return QualityResult(
            version_id, check_name, passed, affected_count, severity, recorded_at
        )

    def list_quality_results(self, version_id: str) -> list[QualityResult]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT version_id, check_name, passed, affected_count, severity, recorded_at
                FROM quality_results WHERE version_id = ? ORDER BY recorded_at
                """,
                [version_id],
            ).fetchall()
        return [QualityResult(*row) for row in rows]

    def create_ingest_run(
        self, version_id: str, *, start_date: str, end_date: str, batch_size: int, symbols: list[str]
    ) -> IngestRun:
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        self.get_version(version_id)
        run_id = f"ingest_{uuid4().hex}"
        created_at = _now()
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO ingest_runs VALUES (?, ?, ?, ?, ?, ?, 0, 'running', ?)""",
                [run_id, version_id, start_date, end_date, batch_size, json.dumps(symbols), created_at],
            )
        return self.get_ingest_run(run_id)

    def get_ingest_run(self, ingest_run_id: str) -> IngestRun:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM ingest_runs WHERE ingest_run_id = ?", [ingest_run_id]).fetchone()
        if row is None:
            raise KeyError(f"unknown ingest run: {ingest_run_id}")
        return IngestRun(*row[:5], tuple(json.loads(row[5])), *row[6:])

    def update_ingest_run(self, ingest_run_id: str, *, next_symbol_index: int, status: str) -> IngestRun:
        with self._connect() as conn:
            conn.execute(
                "UPDATE ingest_runs SET next_symbol_index = ?, status = ? WHERE ingest_run_id = ?",
                [next_symbol_index, status, ingest_run_id],
            )
        return self.get_ingest_run(ingest_run_id)

    def record_ingest_error(
        self, ingest_run_id: str, *, symbol: str, error_message: str, attempt_count: int
    ) -> IngestError:
        if attempt_count < 1:
            raise ValueError("attempt_count must be positive")
        recorded_at = _now()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO ingest_errors VALUES (?, ?, ?, ?, ?)",
                [ingest_run_id, symbol, error_message, attempt_count, recorded_at],
            )
        return IngestError(ingest_run_id, symbol, error_message, attempt_count, recorded_at)

    def list_ingest_errors(self, ingest_run_id: str) -> list[IngestError]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM ingest_errors WHERE ingest_run_id = ? ORDER BY recorded_at", [ingest_run_id]
            ).fetchall()
        return [IngestError(*row) for row in rows]

    def _initialize_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS data_versions (
                    version_id VARCHAR PRIMARY KEY,
                    source VARCHAR NOT NULL,
                    as_of_date VARCHAR NOT NULL,
                    status VARCHAR NOT NULL,
                    created_at VARCHAR NOT NULL,
                    published_at VARCHAR,
                    manifest_hash VARCHAR
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ingest_errors (
                    ingest_run_id VARCHAR NOT NULL,
                    symbol VARCHAR NOT NULL,
                    error_message VARCHAR NOT NULL,
                    attempt_count INTEGER NOT NULL,
                    recorded_at VARCHAR NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ingest_runs (
                    ingest_run_id VARCHAR PRIMARY KEY,
                    data_version VARCHAR NOT NULL,
                    start_date VARCHAR NOT NULL,
                    end_date VARCHAR NOT NULL,
                    batch_size INTEGER NOT NULL,
                    symbols_json VARCHAR NOT NULL,
                    next_symbol_index INTEGER NOT NULL,
                    status VARCHAR NOT NULL,
                    created_at VARCHAR NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS quality_results (
                    version_id VARCHAR NOT NULL,
                    check_name VARCHAR NOT NULL,
                    passed BOOLEAN NOT NULL,
                    affected_count BIGINT NOT NULL,
                    severity VARCHAR NOT NULL,
                    recorded_at VARCHAR NOT NULL
                )
                """
            )

    def _connect(self):
        return duckdb.connect(str(self.paths.database_path))


def _now() -> str:
    return datetime.now(UTC).isoformat()
