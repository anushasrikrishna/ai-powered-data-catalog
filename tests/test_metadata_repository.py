from __future__ import annotations

import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from metadata.models import ColumnMetadata, TableMetadata
from storage.repository import MetadataRepository


class TestMetadataRepository(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "metadata_test.sqlite"
        self.repository = MetadataRepository(self.database_path)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _orders_metadata(self, columns: list[ColumnMetadata] | None = None) -> TableMetadata:
        return TableMetadata(
            source_type="snowflake",
            database_name="DATA_CATALOG_DEMO",
            schema_name="RAW",
            table_name="ORDERS",
            table_type="TABLE",
            row_count=12,
            columns=columns
            if columns is not None
            else [
                ColumnMetadata(
                    column_name="ORDER_ID",
                    source_data_type="NUMBER(38,0)",
                    normalized_data_type="NUMBER",
                    nullable=False,
                    ordinal_position=2,
                    sample_values=[1001, 1002, 1003],
                    null_count=0,
                    distinct_count=12,
                    minimum=1001,
                    maximum=1012,
                ),
                ColumnMetadata(
                    column_name="ORDER_DATE",
                    source_data_type="TIMESTAMP_NTZ",
                    normalized_data_type="DATETIME",
                    nullable=True,
                    ordinal_position=1,
                    sample_values=["2026-01-01T10:30:00", "2026-01-02T12:00:00"],
                    null_count=1,
                    distinct_count=11,
                    minimum="2026-01-01T10:30:00",
                    maximum="2026-01-12T17:45:00",
                ),
            ],
        )

    def test_initialization_is_idempotent(self) -> None:
        MetadataRepository(self.database_path).initialize()
        MetadataRepository(self.database_path).initialize()

        with closing(sqlite3.connect(self.database_path)) as connection:
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }

        self.assertIn("metadata_tables", tables)
        self.assertIn("metadata_columns", tables)

    def test_save_and_retrieve_table_metadata_round_trips_models(self) -> None:
        original = self._orders_metadata()
        self.repository.save_table_metadata(original)

        retrieved = self.repository.get_table_metadata(
            "snowflake",
            "DATA_CATALOG_DEMO",
            "RAW",
            "ORDERS",
        )

        self.assertIsInstance(retrieved, TableMetadata)
        assert retrieved is not None
        self.assertEqual(retrieved.source_type, original.source_type)
        self.assertEqual(retrieved.database_name, original.database_name)
        self.assertEqual(retrieved.schema_name, original.schema_name)
        self.assertEqual(retrieved.table_name, original.table_name)
        self.assertEqual(retrieved.table_type, original.table_type)
        self.assertEqual(retrieved.row_count, original.row_count)
        self.assertEqual([column.ordinal_position for column in retrieved.columns], [1, 2])
        self.assertTrue(all(isinstance(column, ColumnMetadata) for column in retrieved.columns))

        order_id = retrieved.columns[1]
        self.assertEqual(order_id.column_name, "ORDER_ID")
        self.assertEqual(order_id.source_data_type, "NUMBER(38,0)")
        self.assertEqual(order_id.normalized_data_type, "NUMBER")
        self.assertFalse(order_id.nullable)
        self.assertEqual(order_id.ordinal_position, 2)
        self.assertEqual(order_id.sample_values, [1001, 1002, 1003])
        self.assertEqual(order_id.null_count, 0)
        self.assertEqual(order_id.distinct_count, 12)
        self.assertEqual(order_id.minimum, 1001)
        self.assertEqual(order_id.maximum, 1012)

    def test_missing_table_returns_none(self) -> None:
        self.assertIsNone(
            self.repository.get_table_metadata("snowflake", "DB", "RAW", "MISSING")
        )

    def test_same_logical_table_rescan_updates_without_duplicate_and_replaces_columns(self) -> None:
        self.repository.save_table_metadata(self._orders_metadata())
        rescanned = self._orders_metadata(
            [
                ColumnMetadata(
                    column_name="ORDER_STATUS",
                    source_data_type="VARCHAR",
                    normalized_data_type="STRING",
                    nullable=True,
                    ordinal_position=1,
                    sample_values=["NEW", "SHIPPED"],
                    null_count=2,
                    distinct_count=2,
                    minimum="NEW",
                    maximum="SHIPPED",
                )
            ]
        )
        rescanned.row_count = 20
        self.repository.save_table_metadata(rescanned)

        all_tables = self.repository.list_tables()
        retrieved = self.repository.get_table_metadata(
            "snowflake",
            "DATA_CATALOG_DEMO",
            "RAW",
            "ORDERS",
        )

        self.assertEqual(len(all_tables), 1)
        assert retrieved is not None
        self.assertEqual(retrieved.row_count, 20)
        self.assertEqual([column.column_name for column in retrieved.columns], ["ORDER_STATUS"])

        with closing(sqlite3.connect(self.database_path)) as connection:
            table_count = connection.execute("SELECT COUNT(*) FROM metadata_tables").fetchone()[0]
            column_count = connection.execute("SELECT COUNT(*) FROM metadata_columns").fetchone()[0]
        self.assertEqual(table_count, 1)
        self.assertEqual(column_count, 1)

    def test_multiple_different_tables_coexist(self) -> None:
        self.repository.save_table_metadata(self._orders_metadata())
        self.repository.save_table_metadata(
            TableMetadata(
                source_type="snowflake",
                database_name="DATA_CATALOG_DEMO",
                schema_name="RAW",
                table_name="CUSTOMERS",
                table_type="TABLE",
                row_count=5,
                columns=[
                    ColumnMetadata(
                        column_name="CUSTOMER_ID",
                        source_data_type="NUMBER",
                        normalized_data_type="NUMBER",
                        nullable=False,
                        ordinal_position=1,
                    )
                ],
            )
        )

        table_names = [metadata.table_name for metadata in self.repository.list_tables()]
        self.assertEqual(table_names, ["CUSTOMERS", "ORDERS"])

    def test_repository_is_source_neutral(self) -> None:
        for source_type in ("sqlserver", "postgresql", "snowflake"):
            metadata = self._orders_metadata()
            metadata.source_type = source_type
            metadata.database_name = f"{source_type}_database"
            self.repository.save_table_metadata(metadata)

        self.assertEqual(len(self.repository.list_tables()), 3)

    def test_date_datetime_decimal_serialization_does_not_fail(self) -> None:
        metadata = TableMetadata(
            source_type="postgresql",
            database_name="analytics",
            schema_name="public",
            table_name="events",
            row_count=3,
            columns=[
                ColumnMetadata(
                    column_name="EVENT_AT",
                    source_data_type="TIMESTAMP",
                    normalized_data_type="DATETIME",
                    nullable=True,
                    ordinal_position=1,
                    sample_values=[date(2026, 1, 1), datetime(2026, 1, 2, 3, 4, 5), Decimal("12.34")],
                    minimum=date(2026, 1, 1),
                    maximum=datetime(2026, 1, 2, 3, 4, 5),
                )
            ],
        )

        self.repository.save_table_metadata(metadata)
        retrieved = self.repository.get_table_metadata("postgresql", "analytics", "public", "events")

        assert retrieved is not None
        self.assertEqual(
            retrieved.columns[0].sample_values,
            ["2026-01-01", "2026-01-02T03:04:05", "12.34"],
        )
        self.assertEqual(retrieved.columns[0].minimum, "2026-01-01")
        self.assertEqual(retrieved.columns[0].maximum, "2026-01-02T03:04:05")

    def test_schema_contains_no_credential_fields(self) -> None:
        forbidden = {"username", "password", "token", "secret", "connection_string", "url"}
        with closing(sqlite3.connect(self.database_path)) as connection:
            table_columns = {
                row[1]
                for table_name in ("metadata_tables", "metadata_columns")
                for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
            }

        self.assertTrue(forbidden.isdisjoint(table_columns))


if __name__ == "__main__":
    unittest.main()
