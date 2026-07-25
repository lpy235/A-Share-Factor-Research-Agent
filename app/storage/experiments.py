"""Append-only storage for bounded, version-pinned research experiments."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.storage.db import init_db


class ExperimentStore:
    def __init__(self, db_path: str | Path = "runs.db") -> None:
        self.db_path = str(db_path)
        init_db(self.db_path)

    def create(
        self, *, source_run_id: str, data_version: str, manifest_hash: str | None, budget: dict[str, int]
    ) -> dict[str, Any]:
        experiment_id = f"experiment_{uuid4().hex}"
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO research_experiments(
                    experiment_id, source_run_id, data_version, manifest_hash, budget_json, status
                ) VALUES (?, ?, ?, ?, ?, 'running')""",
                [experiment_id, source_run_id, data_version, manifest_hash, json.dumps(budget)],
            )
            conn.commit()
        return self.get(experiment_id)

    def add_candidate(
        self, experiment_id: str, *, spec: dict[str, Any], parent_factor_names: list[str],
        reason: str, round_number: int, status: str, rejection_reasons: list[str], metrics: dict[str, Any] | None
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO research_experiment_candidates(
                    experiment_id, factor_name, spec_json, parent_factor_names_json, variation_reason,
                    round_number, status, rejection_reasons_json, metrics_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [experiment_id, spec["factor_name"], json.dumps(spec, ensure_ascii=False),
                 json.dumps(parent_factor_names, ensure_ascii=False), reason, round_number, status,
                 json.dumps(rejection_reasons, ensure_ascii=False), json.dumps(metrics or {}, ensure_ascii=False)],
            )
            conn.commit()

    def finish(self, experiment_id: str, *, status: str) -> dict[str, Any]:
        if status not in {"completed", "failed"}:
            raise ValueError("experiment status must be completed or failed")
        with self._connect() as conn:
            conn.execute("UPDATE research_experiments SET status = ? WHERE experiment_id = ?", [status, experiment_id])
            conn.commit()
        return self.get(experiment_id)

    def get(self, experiment_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM research_experiments WHERE experiment_id = ?", [experiment_id]).fetchone()
            if row is None:
                raise KeyError(f"unknown experiment: {experiment_id}")
            candidates = conn.execute(
                "SELECT * FROM research_experiment_candidates WHERE experiment_id = ? ORDER BY id", [experiment_id]
            ).fetchall()
        item = dict(row)
        item["budget"] = json.loads(item.pop("budget_json"))
        item["candidates"] = [_candidate_from_row(candidate) for candidate in candidates]
        return item

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn


def _candidate_from_row(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["spec"] = json.loads(item.pop("spec_json"))
    item["parent_factor_names"] = json.loads(item.pop("parent_factor_names_json"))
    item["rejection_reasons"] = json.loads(item.pop("rejection_reasons_json"))
    item["metrics"] = json.loads(item.pop("metrics_json"))
    return item
