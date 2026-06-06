import json
import sqlite3
from typing import Any


class RunStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def save_run(
        self,
        run_id: str,
        *,
        research_topic: str,
        status: str,
        config: dict[str, Any],
        response: dict[str, Any],
    ) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO runs(run_id, research_topic, status, config_json, response_json, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(run_id) DO UPDATE SET
                    research_topic = excluded.research_topic,
                    status = excluded.status,
                    config_json = excluded.config_json,
                    response_json = excluded.response_json,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    run_id,
                    research_topic,
                    status,
                    json.dumps(config, ensure_ascii=False),
                    json.dumps(response, ensure_ascii=False),
                ),
            )
            conn.commit()

    def list_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT run_id, research_topic, status, config_json, response_json, created_at, updated_at
                FROM runs
                ORDER BY updated_at DESC, created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._row_to_summary(row) for row in rows]

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                """
                SELECT run_id, research_topic, status, config_json, response_json, created_at, updated_at
                FROM runs
                WHERE run_id = ?
                """,
                (run_id,),
            ).fetchone()
        if row is None:
            return None
        item = dict(row)
        item["config"] = json.loads(item.pop("config_json"))
        item["response"] = json.loads(item.pop("response_json"))
        return item

    def _row_to_summary(self, row: sqlite3.Row) -> dict[str, Any]:
        response = json.loads(row["response_json"])
        config = json.loads(row["config_json"])
        return {
            "run_id": row["run_id"],
            "research_topic": row["research_topic"],
            "status": row["status"],
            "source_mode": config.get("source_mode"),
            "selected_count": len(response.get("selected_factors", [])),
            "factor_count": len(response.get("factor_specs", [])),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
