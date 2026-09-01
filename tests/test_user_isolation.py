from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path

from metadata.models import ColumnMetadata, TableMetadata
from quality.rule_engine import QualityReport
from storage.quality_repository import QualityRunRepository
from storage.repository import MetadataRepository


def _table() -> TableMetadata:
    return TableMetadata(
        source_type="sqlserver",
        database_name="catalog",
        schema_name="dbo",
        table_name="orders",
        table_type="TABLE",
        row_count=2,
        columns=[
            ColumnMetadata(
                column_name="id",
                source_data_type="int",
                normalized_data_type="NUMBER",
                nullable=False,
                ordinal_position=1,
            )
        ],
    )


def _report() -> QualityReport:
    return QualityReport(
        source_type="sqlserver",
        database_name="catalog",
        schema_name="dbo",
        table_name="orders",
        total_rules=0,
        passed_rules=0,
        failed_rules=0,
        error_rules=0,
        quality_score=None,
        results=[],
    )


class TestUserIsolation(unittest.TestCase):
    def test_same_physical_dataset_is_independent_per_user(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = MetadataRepository(Path(directory) / "catalog.db")
            metadata = _table()
            repository.save_table_metadata(metadata, user_id="user-a")
            repository.save_table_metadata(metadata, user_id="user-b")

            self.assertEqual(len(repository.list_tables("user-a")), 1)
            self.assertEqual(len(repository.list_tables("user-b")), 1)
            self.assertEqual(repository.list_tables("user-c"), [])
            self.assertIsNotNone(
                repository.get_table_metadata("sqlserver", "catalog", "dbo", "orders", "user-b")
            )

    def test_legacy_metadata_is_unowned_and_migration_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database_path = Path(directory) / "legacy.db"
            with closing(sqlite3.connect(database_path)) as connection:
                connection.executescript(
                    """
                    CREATE TABLE metadata_tables (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        source_type TEXT NOT NULL,
                        database_name TEXT NOT NULL,
                        schema_name TEXT NOT NULL,
                        table_name TEXT NOT NULL,
                        table_type TEXT NOT NULL,
                        row_count INTEGER,
                        scanned_at TEXT NOT NULL,
                        UNIQUE (source_type, database_name, schema_name, table_name)
                    );
                    CREATE TABLE metadata_columns (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        table_metadata_id INTEGER NOT NULL,
                        column_name TEXT NOT NULL,
                        source_data_type TEXT NOT NULL,
                        normalized_data_type TEXT NOT NULL,
                        nullable INTEGER NOT NULL,
                        ordinal_position INTEGER NOT NULL,
                        sample_values TEXT NOT NULL,
                        null_count INTEGER,
                        distinct_count INTEGER,
                        minimum TEXT NOT NULL,
                        maximum TEXT NOT NULL,
                        FOREIGN KEY (table_metadata_id) REFERENCES metadata_tables(id) ON DELETE CASCADE
                    );
                    INSERT INTO metadata_tables
                        (source_type, database_name, schema_name, table_name, table_type, row_count, scanned_at)
                    VALUES ('sqlserver', 'catalog', 'dbo', 'orders', 'TABLE', 2, '2026-01-01T00:00:00+00:00');
                    """
                )
                connection.commit()

            repository = MetadataRepository(database_path)
            repository.initialize()
            self.assertEqual(repository.list_tables("user-a"), [])
            self.assertEqual(len(repository.list_tables()), 1)
            with closing(sqlite3.connect(database_path)) as connection:
                columns = {row[1] for row in connection.execute("PRAGMA table_info(metadata_tables)")}
            self.assertIn("user_id", columns)

    def test_quality_history_is_visible_only_to_owner(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = QualityRunRepository(Path(directory) / "quality.db")
            repository.save_quality_run("run-a", _report(), user_id="user-a")

            self.assertEqual(
                [run.run_id for run in repository.list_quality_runs_for_dataset(
                    "sqlserver", "catalog", "dbo", "orders", user_id="user-a"
                )],
                ["run-a"],
            )
            self.assertEqual(
                repository.list_quality_runs_for_dataset(
                    "sqlserver", "catalog", "dbo", "orders", user_id="user-b"
                ),
                [],
            )
            self.assertIsNone(repository.get_quality_run("run-a", user_id="user-b"))


if __name__ == "__main__":
    unittest.main()
