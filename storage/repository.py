from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from metadata.models import ColumnMetadata, TableMetadata
from storage.database import DEFAULT_DATABASE_PATH, connection_context


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
                    UNIQUE (source_type, database_name, schema_name, table_name)
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
                """
            )
            connection.commit()

    def save_table_metadata(self, metadata: TableMetadata) -> None:
        scanned_at = datetime.now(timezone.utc).isoformat()
        with connection_context(self.database_path) as connection:
            try:
                with connection:
                    table_id = self._upsert_table(connection, metadata, scanned_at)
                    connection.execute(
                        "DELETE FROM metadata_columns WHERE table_metadata_id = ?",
                        (table_id,),
                    )
                    self._insert_columns(connection, table_id, metadata.columns)
            except Exception:
                raise

    def get_table_metadata(
        self,
        source_type: str,
        database_name: str,
        schema_name: str,
        table_name: str,
    ) -> TableMetadata | None:
        with connection_context(self.database_path) as connection:
            table_row = connection.execute(
                """
                SELECT id, source_type, database_name, schema_name, table_name, table_type, row_count
                FROM metadata_tables
                WHERE source_type = ?
                  AND database_name = ?
                  AND schema_name = ?
                  AND table_name = ?
                """,
                (source_type, database_name, schema_name, table_name),
            ).fetchone()
            if table_row is None:
                return None
            return self._table_from_row(connection, table_row)

    def list_tables(self) -> list[TableMetadata]:
        with connection_context(self.database_path) as connection:
            table_rows = connection.execute(
                """
                SELECT id, source_type, database_name, schema_name, table_name, table_type, row_count
                FROM metadata_tables
                ORDER BY source_type, database_name, schema_name, table_name
                """
            ).fetchall()
            return [self._table_from_row(connection, table_row) for table_row in table_rows]

    def _upsert_table(
        self,
        connection: sqlite3.Connection,
        metadata: TableMetadata,
        scanned_at: str,
    ) -> int:
        existing = connection.execute(
            """
            SELECT id
            FROM metadata_tables
            WHERE source_type = ?
              AND database_name = ?
              AND schema_name = ?
              AND table_name = ?
            """,
            (
                metadata.source_type,
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
                    table_type, row_count, scanned_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    metadata.source_type,
                    metadata.database_name,
                    metadata.schema_name,
                    metadata.table_name,
                    metadata.table_type,
                    metadata.row_count,
                    scanned_at,
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
