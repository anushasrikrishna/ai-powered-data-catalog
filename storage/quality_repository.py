from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from quality.rule_engine import QualityReport, QualityResult
from storage.database import DEFAULT_DATABASE_PATH, connection_context


@dataclass(frozen=True)
class StoredQualityRun:
    run_id: str
    executed_at: str
    report: QualityReport


def _safe_error_message(value: str | None) -> str | None:
    if value is None:
        return None
    lowered = value.casefold()
    if any(token in lowered for token in ("password", "secret", "token", "private key", "connection string")):
        return "Execution failed. Verify the source connection and permissions."
    return value


class QualityRunRepository:
    """SQLite persistence for safe, completed quality execution history."""

    def __init__(self, database_path: str | Path = DEFAULT_DATABASE_PATH) -> None:
        self.database_path = Path(database_path)
        self.initialize()

    def initialize(self) -> None:
        with connection_context(self.database_path) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS quality_runs (
                    run_id TEXT PRIMARY KEY,
                    source_type TEXT NOT NULL,
                    database_name TEXT NOT NULL,
                    schema_name TEXT NOT NULL,
                    table_name TEXT NOT NULL,
                    executed_at TEXT NOT NULL,
                    quality_score REAL,
                    total_checks INTEGER NOT NULL,
                    passed_checks INTEGER NOT NULL,
                    failed_checks INTEGER NOT NULL,
                    error_checks INTEGER NOT NULL,
                    user_id TEXT
                );

                CREATE TABLE IF NOT EXISTS quality_run_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL,
                    result_order INTEGER NOT NULL,
                    rule_type TEXT NOT NULL,
                    column_name TEXT NOT NULL,
                    rule_config TEXT NOT NULL,
                    status TEXT NOT NULL,
                    total_records INTEGER NOT NULL,
                    passed_records INTEGER NOT NULL,
                    failed_records INTEGER NOT NULL,
                    failure_percentage REAL NOT NULL,
                    error_message TEXT,
                    FOREIGN KEY (run_id) REFERENCES quality_runs(run_id) ON DELETE CASCADE,
                    UNIQUE (run_id, result_order)
                );

                CREATE INDEX IF NOT EXISTS idx_quality_runs_dataset
                    ON quality_runs(source_type, database_name, schema_name, table_name, executed_at);
                CREATE INDEX IF NOT EXISTS idx_quality_run_results_run_id
                    ON quality_run_results(run_id, result_order);
                """
            )
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(quality_runs)").fetchall()}
            if "user_id" not in columns:
                connection.execute("ALTER TABLE quality_runs ADD COLUMN user_id TEXT")
            connection.execute("CREATE INDEX IF NOT EXISTS idx_quality_runs_user_dataset ON quality_runs(user_id, source_type, database_name, schema_name, table_name, executed_at)")
            connection.commit()

    def save_quality_run(
        self,
        run_id: str,
        report: QualityReport,
        executed_at: str | None = None,
        user_id: str | None = None,
    ) -> StoredQualityRun:
        timestamp = executed_at or datetime.now(timezone.utc).isoformat()
        with connection_context(self.database_path) as connection:
            with connection:
                connection.execute(
                    """
                    INSERT INTO quality_runs (
                        run_id, source_type, database_name, schema_name, table_name,
                        executed_at, quality_score, total_checks, passed_checks,
                        failed_checks, error_checks, user_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        report.source_type,
                        report.database_name,
                        report.schema_name,
                        report.table_name,
                        timestamp,
                        report.quality_score,
                        report.total_rules,
                        report.passed_rules,
                        report.failed_rules,
                        report.error_rules,
                        user_id,
                    ),
                )
                connection.executemany(
                    """
                    INSERT INTO quality_run_results (
                        run_id, result_order, rule_type, column_name, rule_config,
                        status, total_records, passed_records, failed_records,
                        failure_percentage, error_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            run_id,
                            index,
                            result.rule_type,
                            result.column,
                            json.dumps(result.rule_config, default=str, separators=(",", ":")),
                            result.status,
                            result.total_records,
                            result.passed_records,
                            result.failed_records,
                            result.failure_percentage,
                            _safe_error_message(result.error_message),
                        )
                        for index, result in enumerate(report.results)
                    ],
                )
        return StoredQualityRun(run_id=run_id, executed_at=timestamp, report=report)

    def get_quality_run(self, run_id: str, user_id: str | None = None) -> StoredQualityRun | None:
        with connection_context(self.database_path) as connection:
            row = connection.execute(
                "SELECT * FROM quality_runs WHERE run_id = ? AND user_id IS ?",
                (run_id, user_id),
            ).fetchone()
            if row is None:
                return None
            return self._stored_run(connection, row)

    def list_quality_runs_for_dataset(
        self,
        source_type: str,
        database_name: str,
        schema_name: str,
        table_name: str,
        user_id: str | None = None,
    ) -> list[StoredQualityRun]:
        with connection_context(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT * FROM quality_runs
                WHERE user_id IS ? AND source_type = ? AND database_name = ?
                  AND schema_name = ? AND table_name = ?
                ORDER BY executed_at DESC
                """,
                (user_id, source_type, database_name, schema_name, table_name),
            ).fetchall()
            return [self._stored_run(connection, row) for row in rows]

    def get_latest_run_for_user(self, user_id: str) -> StoredQualityRun | None:
        with connection_context(self.database_path) as connection:
            row = connection.execute(
                "SELECT * FROM quality_runs WHERE user_id = ? ORDER BY executed_at DESC LIMIT 1",
                (user_id,),
            ).fetchone()
            return self._stored_run(connection, row) if row is not None else None

    def _stored_run(self, connection: Any, row: Any) -> StoredQualityRun:
        result_rows = connection.execute(
            """
            SELECT rule_type, column_name, rule_config, status, total_records,
                   passed_records, failed_records, failure_percentage, error_message
            FROM quality_run_results
            WHERE run_id = ?
            ORDER BY result_order
            """,
            (row["run_id"],),
        ).fetchall()
        report = QualityReport(
            source_type=row["source_type"],
            database_name=row["database_name"],
            schema_name=row["schema_name"],
            table_name=row["table_name"],
            total_rules=row["total_checks"],
            passed_rules=row["passed_checks"],
            failed_rules=row["failed_checks"],
            error_rules=row["error_checks"],
            quality_score=row["quality_score"],
            results=[
                QualityResult(
                    rule_type=result["rule_type"],
                    column=result["column_name"],
                    rule_config=json.loads(result["rule_config"]),
                    status=result["status"],
                    total_records=result["total_records"],
                    passed_records=result["passed_records"],
                    failed_records=result["failed_records"],
                    failure_percentage=result["failure_percentage"],
                    error_message=result["error_message"],
                )
                for result in result_rows
            ],
        )
        return StoredQualityRun(run_id=row["run_id"], executed_at=row["executed_at"], report=report)


__all__ = ["QualityRunRepository", "StoredQualityRun"]
