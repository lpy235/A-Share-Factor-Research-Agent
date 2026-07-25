from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.storage.db import init_db


VALID_FACTOR_STATUSES = frozenset({"candidate", "approved", "rejected", "retired"})
REQUIRED_CANDIDATE_FIELDS = frozenset(
    {
        "factor_name",
        "formula",
        "direction",
        "required_fields",
        "source_evidence",
        "metrics",
        "run_id",
    }
)


class FactorRegistryStore:
    """Persists immutable factor snapshots and append-only human decisions."""

    def __init__(self, db_path: str | Path = "factor_registry.db") -> None:
        self.db_path = str(db_path)
        init_db(self.db_path)

    def register_candidate(self, payload: dict[str, Any]) -> dict[str, Any]:
        missing = sorted(REQUIRED_CANDIDATE_FIELDS - set(payload))
        if missing:
            raise ValueError(f"missing candidate fields: {missing}")
        version_id = f"factor_{uuid4().hex}"
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO factor_versions(
                    version_id, factor_name, formula, direction, required_fields_json,
                    source_evidence_json, metrics_json, run_id, data_version, manifest_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    version_id,
                    str(payload["factor_name"]),
                    str(payload["formula"]),
                    str(payload["direction"]),
                    json.dumps(payload["required_fields"], ensure_ascii=False),
                    json.dumps(payload["source_evidence"], ensure_ascii=False),
                    json.dumps(payload["metrics"], ensure_ascii=False),
                    str(payload["run_id"]),
                    payload.get("data_version"),
                    payload.get("manifest_hash"),
                ),
            )
            self._insert_decision(
                conn,
                version_id,
                status="candidate",
                decision_maker="registry",
                reason="Registered from a selected research factor.",
            )
            conn.commit()
        return self.get(version_id)

    def record_decision(
        self, version_id: str, status: str, decision_maker: str, reason: str
    ) -> dict[str, Any]:
        if not decision_maker.strip() or not reason.strip():
            raise ValueError("decision_maker and reason are required")
        with self._connect() as conn:
            if conn.execute("SELECT 1 FROM factor_versions WHERE version_id = ?", [version_id]).fetchone() is None:
                raise KeyError(f"unknown factor version: {version_id}")
            self._insert_decision(conn, version_id, status, decision_maker, reason)
            conn.commit()
        return self.get(version_id)["decisions"][-1]

    def get(self, version_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM factor_versions WHERE version_id = ?", [version_id]).fetchone()
            if row is None:
                raise KeyError(f"unknown factor version: {version_id}")
            decisions = conn.execute(
                """SELECT status, decision_maker, reason, created_at FROM factor_decisions
                WHERE version_id = ? ORDER BY id""",
                [version_id],
            ).fetchall()
            recommendations = conn.execute(
                """SELECT recommendation, reasons_json, evidence_json, created_at
                FROM factor_recommendations WHERE version_id = ? ORDER BY id""",
                [version_id],
            ).fetchall()
        item = dict(row)
        item["required_fields"] = json.loads(item.pop("required_fields_json"))
        item["source_evidence"] = json.loads(item.pop("source_evidence_json"))
        item["metrics"] = json.loads(item.pop("metrics_json"))
        item["decisions"] = [dict(decision) for decision in decisions]
        item["status"] = item["decisions"][-1]["status"]
        item["recommendations"] = [
            {
                "recommendation": recommendation["recommendation"],
                "reasons": json.loads(recommendation["reasons_json"]),
                "evidence": json.loads(recommendation["evidence_json"]),
                "created_at": recommendation["created_at"],
            }
            for recommendation in recommendations
        ]
        return item

    def list(self) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT version_id FROM factor_versions ORDER BY created_at DESC").fetchall()
        return [self.get(row["version_id"]) for row in rows]

    def record_recommendation(
        self, version_id: str, recommendation: str, reasons: list[str], evidence: dict[str, Any]
    ) -> dict[str, Any]:
        if recommendation not in {"approve", "reject", "continue_research"}:
            raise ValueError("invalid recommendation")
        with self._connect() as conn:
            if conn.execute("SELECT 1 FROM factor_versions WHERE version_id = ?", [version_id]).fetchone() is None:
                raise KeyError(f"unknown factor version: {version_id}")
            conn.execute(
                """INSERT INTO factor_recommendations(version_id, recommendation, reasons_json, evidence_json)
                VALUES (?, ?, ?, ?)""",
                [version_id, recommendation, json.dumps(reasons, ensure_ascii=False), json.dumps(evidence, ensure_ascii=False)],
            )
            conn.commit()
        return self.get(version_id)["recommendations"][-1]

    def _insert_decision(
        self, conn: sqlite3.Connection, version_id: str, status: str, decision_maker: str, reason: str
    ) -> None:
        if status not in VALID_FACTOR_STATUSES:
            raise ValueError(f"invalid factor status: {status}")
        conn.execute(
            """INSERT INTO factor_decisions(version_id, status, decision_maker, reason)
            VALUES (?, ?, ?, ?)""",
            [version_id, status, decision_maker, reason],
        )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
