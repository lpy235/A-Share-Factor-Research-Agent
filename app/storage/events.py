import json
import sqlite3
from typing import Any


class EventStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def append(self, run_id: str, node: str, event_type: str, payload: dict[str, Any]) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO events(run_id, node, event_type, payload_json) VALUES (?, ?, ?, ?)",
                (run_id, node, event_type, json.dumps(payload, ensure_ascii=False)),
            )
            conn.commit()

    def list_events(self, run_id: str) -> list[dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                """
                SELECT id, run_id, node, event_type, payload_json, created_at
                FROM events
                WHERE run_id = ?
                ORDER BY id ASC
                """,
                (run_id,),
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item.pop("payload_json"))
            result.append(item)
        return result

