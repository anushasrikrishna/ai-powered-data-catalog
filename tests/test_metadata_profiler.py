from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
import unittest
from types import SimpleNamespace

from sqlalchemy import Boolean, Column, Date, DateTime, Integer, LargeBinary, MetaData, Numeric, String, Table, create_engine, insert
from sqlalchemy.pool import StaticPool

from metadata.models import ColumnMetadata, TableMetadata
from metadata.profiler import MetadataProfiler


class TestMetadataProfiler(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        metadata = MetaData()
        self.customers = Table(
            "customers",
            metadata,
            Column("id", Integer, primary_key=True, nullable=False),
            Column("name", String(50), nullable=True),
            Column("amount", Numeric(10, 2), nullable=True),
            Column("created_on", Date, nullable=True),
            Column("created_at", DateTime, nullable=True),
            Column("active", Boolean, nullable=True),
            Column("payload", LargeBinary, nullable=True),
        )
        self.empty_table = Table(
            "empty_table",
            metadata,
            Column("id", Integer, nullable=True),
        )
        self.all_nulls = Table(
            "all_nulls",
            metadata,
            Column("id", Integer, nullable=True),
            Column("notes", String(50), nullable=True),
        )
        metadata.create_all(self.engine)

        with self.engine.begin() as connection:
            connection.execute(
                insert(self.customers),
                [
                    {
                        "id": 1,
                        "name": "Alice",
                        "amount": Decimal("10.50"),
                        "created_on": date(2026, 1, 1),
                        "created_at": datetime(2026, 1, 1, 9, 0, 0),
                        "active": True,
                        "payload": b"a",
                    },
                    {
                        "id": 2,
                        "name": "Bob",
                        "amount": None,
                        "created_on": date(2026, 1, 2),
                        "created_at": datetime(2026, 1, 2, 10, 0, 0),
                        "active": False,
                        "payload": b"b",
                    },
                    {
                        "id": 3,
                        "name": "Bob",
                        "amount": Decimal("7.25"),
                        "created_on": None,
                        "created_at": datetime(2026, 1, 3, 11, 0, 0),
                        "active": None,
                        "payload": None,
                    },
                    {
                        "id": 4,
                        "name": None,
                        "amount": Decimal("7.25"),
                        "created_on": date(2026, 1, 1),
                        "created_at": None,
                        "active": True,
                        "payload": b"c",
                    },
                ],
            )
            connection.execute(
                insert(self.all_nulls),
                [
                    {"id": None, "notes": None},
                    {"id": None, "notes": None},
                ],
            )

        self.connector = SimpleNamespace(engine=self.engine)
        self.profiler = MetadataProfiler(self.connector, sample_value_limit=3)

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_profile_table_calculates_row_null_distinct_min_max_and_samples(self) -> None:
        table_metadata = TableMetadata(
            source_type="sqlite",
            database_name="catalog_demo",
            schema_name="",
            table_name="customers",
            table_type="TABLE",
            columns=[
                ColumnMetadata(column_name="id", source_data_type="INTEGER", normalized_data_type="NUMBER", nullable=False, ordinal_position=1),
                ColumnMetadata(column_name="name", source_data_type="VARCHAR(50)", normalized_data_type="STRING", nullable=True, ordinal_position=2),
                ColumnMetadata(column_name="amount", source_data_type="NUMERIC(10,2)", normalized_data_type="DECIMAL", nullable=True, ordinal_position=3),
                ColumnMetadata(column_name="created_on", source_data_type="DATE", normalized_data_type="DATE", nullable=True, ordinal_position=4),
                ColumnMetadata(column_name="created_at", source_data_type="DATETIME", normalized_data_type="DATETIME", nullable=True, ordinal_position=5),
                ColumnMetadata(column_name="active", source_data_type="BOOLEAN", normalized_data_type="BOOLEAN", nullable=True, ordinal_position=6),
                ColumnMetadata(column_name="payload", source_data_type="BLOB", normalized_data_type="BINARY", nullable=True, ordinal_position=7),
            ],
        )

        profiled = self.profiler.profile_table(table_metadata)

        self.assertEqual(profiled.row_count, 4)
        self.assertEqual(profiled.columns[0].null_count, 0)
        self.assertEqual(profiled.columns[0].distinct_count, 4)
        self.assertEqual(profiled.columns[0].minimum, 1)
        self.assertEqual(profiled.columns[0].maximum, 4)
        self.assertEqual(profiled.columns[0].sample_values, [1, 2, 3])

        self.assertEqual(profiled.columns[1].null_count, 1)
        self.assertEqual(profiled.columns[1].distinct_count, 2)
        self.assertEqual(profiled.columns[1].minimum, "Alice")
        self.assertEqual(profiled.columns[1].maximum, "Bob")
        self.assertEqual(profiled.columns[1].sample_values, ["Alice", "Bob"])

        self.assertEqual(profiled.columns[2].null_count, 1)
        self.assertEqual(profiled.columns[2].distinct_count, 2)
        self.assertEqual(profiled.columns[2].minimum, Decimal("7.25"))
        self.assertEqual(profiled.columns[2].maximum, Decimal("10.50"))
        self.assertEqual(profiled.columns[2].sample_values, [Decimal("7.25"), Decimal("10.50")])

        self.assertEqual(profiled.columns[3].null_count, 1)
        self.assertEqual(profiled.columns[3].distinct_count, 2)
        self.assertEqual(profiled.columns[3].minimum, date(2026, 1, 1))
        self.assertEqual(profiled.columns[3].maximum, date(2026, 1, 2))
        self.assertEqual(profiled.columns[3].sample_values, [date(2026, 1, 1), date(2026, 1, 2)])

        self.assertEqual(profiled.columns[4].null_count, 1)
        self.assertEqual(profiled.columns[4].distinct_count, 3)
        self.assertEqual(profiled.columns[4].minimum, datetime(2026, 1, 1, 9, 0, 0))
        self.assertEqual(profiled.columns[4].maximum, datetime(2026, 1, 3, 11, 0, 0))
        self.assertEqual(profiled.columns[4].sample_values, [
            datetime(2026, 1, 1, 9, 0, 0),
            datetime(2026, 1, 2, 10, 0, 0),
            datetime(2026, 1, 3, 11, 0, 0),
        ])

        self.assertEqual(profiled.columns[5].null_count, 1)
        self.assertEqual(profiled.columns[5].distinct_count, 2)
        self.assertEqual(profiled.columns[5].minimum, False)
        self.assertEqual(profiled.columns[5].maximum, True)
        self.assertEqual(profiled.columns[5].sample_values, [False, True])

        self.assertEqual(profiled.columns[6].null_count, 1)
        self.assertGreaterEqual(profiled.columns[6].distinct_count, 2)
        self.assertIsNone(profiled.columns[6].minimum)
        self.assertIsNone(profiled.columns[6].maximum)
        self.assertEqual(profiled.columns[6].sample_values, [])

    def test_profile_empty_table(self) -> None:
        table_metadata = TableMetadata(
            source_type="sqlite",
            database_name="catalog_demo",
            schema_name="",
            table_name="empty_table",
            table_type="TABLE",
            columns=[ColumnMetadata(column_name="id", source_data_type="INTEGER", normalized_data_type="NUMBER", nullable=True, ordinal_position=1)],
        )

        profiled = self.profiler.profile_table(table_metadata)

        self.assertEqual(profiled.row_count, 0)
        self.assertEqual(profiled.columns[0].null_count, 0)
        self.assertEqual(profiled.columns[0].distinct_count, 0)
        self.assertIsNone(profiled.columns[0].minimum)
        self.assertIsNone(profiled.columns[0].maximum)
        self.assertEqual(profiled.columns[0].sample_values, [])

    def test_profile_all_null_columns(self) -> None:
        table_metadata = TableMetadata(
            source_type="sqlite",
            database_name="catalog_demo",
            schema_name="",
            table_name="all_nulls",
            table_type="TABLE",
            columns=[
                ColumnMetadata(column_name="id", source_data_type="INTEGER", normalized_data_type="NUMBER", nullable=True, ordinal_position=1),
                ColumnMetadata(column_name="notes", source_data_type="VARCHAR(50)", normalized_data_type="STRING", nullable=True, ordinal_position=2),
            ],
        )

        profiled = self.profiler.profile_table(table_metadata)

        self.assertEqual(profiled.row_count, 2)
        for column in profiled.columns:
            self.assertEqual(column.null_count, 2)
            self.assertEqual(column.distinct_count, 0)
            self.assertIsNone(column.minimum)
            self.assertIsNone(column.maximum)
            self.assertEqual(column.sample_values, [])
