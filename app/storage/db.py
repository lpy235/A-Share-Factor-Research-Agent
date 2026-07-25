import sqlite3


def init_db(db_path: str) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                node TEXT NOT NULL,
                event_type TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_events_run_id ON events(run_id, id)")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                research_topic TEXT NOT NULL,
                status TEXT NOT NULL,
                config_json TEXT NOT NULL,
                response_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_runs_updated_at ON runs(updated_at DESC)")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS factor_versions (
                version_id TEXT PRIMARY KEY,
                factor_name TEXT NOT NULL,
                formula TEXT NOT NULL,
                direction TEXT NOT NULL,
                required_fields_json TEXT NOT NULL,
                source_evidence_json TEXT NOT NULL,
                metrics_json TEXT NOT NULL,
                run_id TEXT NOT NULL,
                data_version TEXT,
                manifest_hash TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_factor_versions_name ON factor_versions(factor_name)")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS factor_decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version_id TEXT NOT NULL,
                status TEXT NOT NULL,
                decision_maker TEXT NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(version_id) REFERENCES factor_versions(version_id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_factor_decisions_version ON factor_decisions(version_id, id)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS factor_recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version_id TEXT NOT NULL,
                recommendation TEXT NOT NULL,
                reasons_json TEXT NOT NULL,
                evidence_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(version_id) REFERENCES factor_versions(version_id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_factor_recommendations_version ON factor_recommendations(version_id, id)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS research_experiments (
                experiment_id TEXT PRIMARY KEY,
                source_run_id TEXT NOT NULL,
                data_version TEXT NOT NULL,
                manifest_hash TEXT,
                budget_json TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS research_experiment_candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id TEXT NOT NULL,
                factor_name TEXT NOT NULL,
                spec_json TEXT NOT NULL,
                parent_factor_names_json TEXT NOT NULL,
                variation_reason TEXT NOT NULL,
                round_number INTEGER NOT NULL,
                status TEXT NOT NULL,
                rejection_reasons_json TEXT NOT NULL,
                metrics_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(experiment_id) REFERENCES research_experiments(experiment_id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_research_experiment_candidates ON research_experiment_candidates(experiment_id, id)"
        )
        conn.commit()
