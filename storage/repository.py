from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from metadata.models import ColumnMetadata, TableMetadata
from storage.database import DEFAULT_DATABASE_PATH, connection_context
from storage.scan_history import ScanComparison, ScanSnapshot, compare_snapshots


class MetadataRepository:
    """SQLite repository for source-neutral table and column metadata.

    Values that are not native JSON primitives are stored with small type tags.
    Dates and datetimes are restored as ISO-8601 strings, and Decimals are
    restored as their exact string representation.
    """

    def __init__(self, database_path: str | Path = DEFAULT_DATABASE_PATH) -> None:
        self.database_path = Path(database_path)
        self.initialize()

    def initialize(self) -> None:
        with connection_context(self.database_path) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS metadata_tables (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_type TEXT NOT NULL,
                    database_name TEXT NOT NULL,
                    schema_name TEXT NOT NULL,
                    table_name TEXT NOT NULL,
                    table_type TEXT NOT NULL,
                    row_count INTEGER,
                    scanned_at TEXT NOT NULL,
                    user_id TEXT,
                    UNIQUE (user_id, source_type, database_name, schema_name, table_name)
                );

                CREATE TABLE IF NOT EXISTS metadata_columns (
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
                    FOREIGN KEY (table_metadata_id)
                        REFERENCES metadata_tables (id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_metadata_columns_table_id
                    ON metadata_columns (table_metadata_id);

                CREATE TABLE IF NOT EXISTS metadata_scan_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_type TEXT NOT NULL,
                    database_name TEXT NOT NULL,
                    schema_name TEXT NOT NULL,
                    table_name TEXT NOT NULL,
                    table_type TEXT NOT NULL,
                    row_count INTEGER,
                    column_count INTEGER NOT NULL,
                    scanned_at TEXT NOT NULL,
                    user_id TEXT
                );

                CREATE TABLE IF NOT EXISTS metadata_scan_snapshot_columns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scan_snapshot_id INTEGER NOT NULL,
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
                    FOREIGN KEY (scan_snapshot_id)
                        REFERENCES metadata_scan_snapshots (id)
                        ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_metadata_scan_snapshots_dataset
                    ON metadata_scan_snapshots(user_id, source_type, database_name, schema_name, table_name, scanned_at DESC);
                CREATE INDEX IF NOT EXISTS idx_metadata_scan_snapshot_columns_id
                    ON metadata_scan_snapshot_columns(scan_snapshot_id);
                """
            )
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(metadata_tables)").fetchall()}
            if "user_id" not in columns:
                self._migrate_legacy_ownership(connection)
            connection.execute("CREATE INDEX IF NOT EXISTS idx_metadata_tables_user_id ON metadata_tables(user_id)")
            connection.commit()

    def _migrate_legacy_ownership(self, connection: sqlite3.Connection) -> None:
        """Rebuild the metadata tables with nullable owners; legacy rows stay unowned."""
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute("ALTER TABLE metadata_columns RENAME TO metadata_columns_legacy")
        connection.execute("ALTER TABLE metadata_tables RENAME TO metadata_tables_legacy")
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
                user_id TEXT,
                UNIQUE (user_id, source_type, database_name, schema_name, table_name)
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
            """
        )
        connection.execute("INSERT INTO metadata_tables (id, source_type, database_name, schema_name, table_name, table_type, row_count, scanned_at, user_id) SELECT id, source_type, database_name, schema_name, table_name, table_type, row_count, scanned_at, NULL FROM metadata_tables_legacy")
        connection.execute("INSERT INTO metadata_columns SELECT * FROM metadata_columns_legacy")
        connection.execute("DROP TABLE metadata_columns_legacy")
        connection.execute("DROP TABLE metadata_tables_legacy")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_metadata_columns_table_id ON metadata_columns(table_metadata_id)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_metadata_tables_user_id ON metadata_tables(user_id)")
        connection.execute("PRAGMA foreign_keys = ON")

    def save_table_metadata(
        self,
        metadata: TableMetadata,
        user_id: str | None = None,
        scanned_at: str | None = None,
    ) -> None:
        scanned_at = scanned_at or datetime.now(timezone.utc).isoformat()
        with connection_context(self.database_path) as connection:
            try:
                with connection:
                    self._save_scan_snapshot(connection, metadata, scanned_at, user_id)
                    table_id = self._upsert_table(connection, metadata, scanned_at, user_id)
                    connection.execute(
                        "DELETE FROM metadata_columns WHERE table_metadata_id = ?",
                        (table_id,),
                    )
                    self._insert_columns(connection, table_id, metadata.columns)
            except Exception:
                raise

    def save_scan_snapshot(self, metadata: TableMetadata, user_id: str | None = None, scanned_at: str | None = None) -> int:
        """Persist one successful scan snapshot without changing latest catalog state."""
        timestamp = scanned_at or datetime.now(timezone.utc).isoformat()
        with connection_context(self.database_path) as connection:
            with connection:
                return self._save_scan_snapshot(connection, metadata, timestamp, user_id)

    def list_scan_history(
        self,
        source_type: str,
        database_name: str,
        schema_name: str,
        table_name: str,
        user_id: str | None = None,
        limit: int = 20,
    ) -> list[ScanSnapshot]:
        safe_limit = max(1, min(int(limit), 100))
        with connection_context(self.database_path) as connection:
            rows = connection.execute(
                """
                SELECT id, source_type, database_name, schema_name, table_name,
                       table_type, row_count, scanned_at
                FROM metadata_scan_snapshots
                WHERE user_id IS ? AND source_type = ?
                  AND database_name = ? AND schema_name = ? AND table_name = ?
                ORDER BY scanned_at DESC, id DESC
                LIMIT ?
                """,
                (user_id, source_type, database_name, schema_name, table_name, safe_limit),
            ).fetchall()
            return [self._snapshot_from_row(connection, row) for row in rows]

    def get_dataset_scan_history(self, *args: Any, **kwargs: Any) -> list[ScanSnapshot]:
        return self.list_scan_history(*args, **kwargs)

    def get_latest_scan(self, *args: Any, **kwargs: Any) -> ScanSnapshot | None:
        history = self.list_scan_history(*args, limit=1, **kwargs)
        return history[0] if history else None

    def get_previous_scan(self, *args: Any, **kwargs: Any) -> ScanSnapshot | None:
        history = self.list_scan_history(*args, limit=2, **kwargs)
        return history[1] if len(history) > 1 else None

    def get_scan_comparison(
        self,
        source_type: str,
        database_name: str,
        schema_name: str,
        table_name: str,
        user_id: str | None = None,
    ) -> ScanComparison | None:
        history = self.list_scan_history(source_type, database_name, schema_name, table_name, user_id, limit=2)
        if len(history) < 2:
            return None
        return compare_snapshots(history[1], history[0])

    def _save_scan_snapshot(
        self,
        connection: sqlite3.Connection,
        metadata: TableMetadata,
        scanned_at: str,
        user_id: str | None,
    ) -> int:
        cursor = connection.execute(
            """
            INSERT INTO metadata_scan_snapshots(
                source_type, database_name, schema_name, table_name,
                table_type, row_count, column_count, scanned_at, user_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                metadata.source_type, metadata.database_name, metadata.schema_name,
                metadata.table_name, metadata.table_type, metadata.row_count,
                len(metadata.columns), scanned_at, user_id,
            ),
        )
        snapshot_id = int(cursor.lastrowid)
        connection.executemany(
            """
            INSERT INTO metadata_scan_snapshot_columns(
                scan_snapshot_id, column_name, source_data_type,
                normalized_data_type, nullable, ordinal_position,
                sample_values, null_count, distinct_count, minimum, maximum
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    snapshot_id, column.column_name, column.source_data_type,
                    column.normalized_data_type, 1 if column.nullable else 0,
                    column.ordinal_position, self._to_json(column.sample_values),
                    column.null_count, column.distinct_count,
                    self._to_json(column.minimum), self._to_json(column.maximum),
                )
                for column in metadata.columns
            ],
        )
        return snapshot_id

    def _snapshot_from_row(self, connection: sqlite3.Connection, row: sqlite3.Row) -> ScanSnapshot:
        column_rows = connection.execute(
            """
            SELECT column_name, source_data_type, normalized_data_type, nullable,
                   ordinal_position, sample_values, null_count, distinct_count,
                   minimum, maximum
            FROM metadata_scan_snapshot_columns
            WHERE scan_snapshot_id = ?
            ORDER BY ordinal_position
            """,
            (row["id"],),
        ).fetchall()
        return ScanSnapshot(
            scan_id=int(row["id"]),
            source_type=str(row["source_type"]),
            database_name=str(row["database_name"]),
            schema_name=str(row["schema_name"]),
            table_name=str(row["table_name"]),
            table_type=str(row["table_type"]),
            scanned_at=str(row["scanned_at"]),
            row_count=row["row_count"],
            columns=tuple(
                ColumnMetadata(
                    column_name=str(column["column_name"]),
                    source_data_type=str(column["source_data_type"]),
                    normalized_data_type=str(column["normalized_data_type"]),
                    nullable=bool(column["nullable"]),
                    ordinal_position=int(column["ordinal_position"]),
                    sample_values=self._from_json(column["sample_values"]),
                    null_count=column["null_count"],
                    distinct_count=column["distinct_count"],
                    minimum=self._from_json(column["minimum"]),
                    maximum=self._from_json(column["maximum"]),
                )
                for column in column_rows
            ),
        )

    def get_table_metadata(
        self,
        source_type: str,
        database_name: str,
        schema_name: str,
        table_name: str,
        user_id: str | None = None,
    ) -> TableMetadata | None:
        with connection_context(self.database_path) as connection:
            table_row = connection.execute(
                """
                SELECT id, source_type, database_name, schema_name, table_name, table_type, row_count
                FROM metadata_tables
                WHERE user_id IS ? AND source_type = ?
                  AND database_name = ?
                  AND schema_name = ?
                  AND table_name = ?
                """,
                (user_id, source_type, database_name, schema_name, table_name),
            ).fetchone()
            if table_row is None:
                return None
            return self._table_from_row(connection, table_row)

    def list_tables(self, user_id: str | None = None) -> list[TableMetadata]:
        with connection_context(self.database_path) as connection:
            table_rows = connection.execute(
                """
                SELECT id, source_type, database_name, schema_name, table_name, table_type, row_count
                FROM metadata_tables
                WHERE user_id IS ?
                ORDER BY source_type, database_name, schema_name, table_name
                """ , (user_id,)
            ).fetchall()
            return [self._table_from_row(connection, table_row) for table_row in table_rows]

    def _upsert_table(
        self,
        connection: sqlite3.Connection,
        metadata: TableMetadata,
        scanned_at: str,
        user_id: str | None = None,
    ) -> int:
        existing = connection.execute(
            """
            SELECT id
            FROM metadata_tables
            WHERE user_id IS ? AND source_type = ?
              AND database_name = ?
              AND schema_name = ?
              AND table_name = ?
            """,
            (
                user_id, metadata.source_type,
                metadata.database_name,
                metadata.schema_name,
                metadata.table_name,
            ),
        ).fetchone()

        if existing is None:
            cursor = connection.execute(
                """
                INSERT INTO metadata_tables (
                    source_type, database_name, schema_name, table_name,
                    table_type, row_count, scanned_at, user_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    metadata.source_type,
                    metadata.database_name,
                    metadata.schema_name,
                    metadata.table_name,
                    metadata.table_type,
                    metadata.row_count,
                    scanned_at,
                    user_id,
                ),
            )
            return int(cursor.lastrowid)

        table_id = int(existing["id"])
        connection.execute(
            """
            UPDATE metadata_tables
            SET table_type = ?,
                row_count = ?,
                scanned_at = ?
            WHERE id = ?
            """,
            (metadata.table_type, metadata.row_count, scanned_at, table_id),
        )
        return table_id

    def _insert_columns(
        self,
        connection: sqlite3.Connection,
        table_id: int,
        columns: list[ColumnMetadata],
    ) -> None:
        connection.executemany(
            """
            INSERT INTO metadata_columns (
                table_metadata_id, column_name, source_data_type,
                normalized_data_type, nullable, ordinal_position,
                sample_values, null_count, distinct_count, minimum, maximum
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    table_id,
                    column.column_name,
                    column.source_data_type,
                    column.normalized_data_type,
                    1 if column.nullable else 0,
                    column.ordinal_position,
                    self._to_json(column.sample_values),
                    column.null_count,
                    column.distinct_count,
                    self._to_json(column.minimum),
                    self._to_json(column.maximum),
                )
                for column in columns
            ],
        )

    def _table_from_row(self, connection: sqlite3.Connection, table_row: sqlite3.Row) -> TableMetadata:
        column_rows = connection.execute(
            """
            SELECT column_name, source_data_type, normalized_data_type, nullable,
                   ordinal_position, sample_values, null_count, distinct_count,
                   minimum, maximum
            FROM metadata_columns
            WHERE table_metadata_id = ?
            ORDER BY ordinal_position
            """,
            (table_row["id"],),
        ).fetchall()

        return TableMetadata(
            source_type=str(table_row["source_type"]),
            database_name=str(table_row["database_name"]),
            schema_name=str(table_row["schema_name"]),
            table_name=str(table_row["table_name"]),
            table_type=str(table_row["table_type"]),
            row_count=table_row["row_count"],
            columns=[
                ColumnMetadata(
                    column_name=str(column_row["column_name"]),
                    source_data_type=str(column_row["source_data_type"]),
                    normalized_data_type=str(column_row["normalized_data_type"]),
                    nullable=bool(column_row["nullable"]),
                    ordinal_position=int(column_row["ordinal_position"]),
                    sample_values=self._from_json(column_row["sample_values"]),
                    null_count=column_row["null_count"],
                    distinct_count=column_row["distinct_count"],
                    minimum=self._from_json(column_row["minimum"]),
                    maximum=self._from_json(column_row["maximum"]),
                )
                for column_row in column_rows
            ],
        )

    def _to_json(self, value: Any) -> str:
        return json.dumps(self._serialize_value(value), separators=(",", ":"))

    def _from_json(self, value: str) -> Any:
        return self._deserialize_value(json.loads(value))

    def _serialize_value(self, value: Any) -> Any:
        if isinstance(value, list):
            return [self._serialize_value(item) for item in value]
        if isinstance(value, tuple):
            return [self._serialize_value(item) for item in value]
        if isinstance(value, dict):
            return {str(key): self._serialize_value(item) for key, item in value.items()}
        if isinstance(value, datetime):
            return {"__type__": "datetime", "value": value.isoformat()}
        if isinstance(value, date):
            return {"__type__": "date", "value": value.isoformat()}
        if isinstance(value, Decimal):
            return {"__type__": "decimal", "value": str(value)}
        return value

    def _deserialize_value(self, value: Any) -> Any:
        if isinstance(value, list):
            return [self._deserialize_value(item) for item in value]
        if isinstance(value, dict):
            value_type = value.get("__type__")
            if value_type in {"date", "datetime", "decimal"}:
                return value.get("value")
            return {key: self._deserialize_value(item) for key, item in value.items()}
        return value
