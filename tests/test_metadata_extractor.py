from __future__ import annotations

import unittest
from unittest.mock import MagicMock
from types import SimpleNamespace

from sqlalchemy.engine import create_engine

from metadata.extractor import MetadataExtractor
from metadata.models import TableMetadata


class StubProfiler:
    def profile_table(self, table_metadata: TableMetadata) -> TableMetadata:
        table_metadata.row_count = 4
        for index, column in enumerate(table_metadata.columns, start=1):
            column.null_count = index - 1
            column.distinct_count = index + 1
            column.minimum = None
            column.maximum = None
            column.sample_values = [f"sample-{column.column_name}"]
        return table_metadata


class TestMetadataExtractor(unittest.TestCase):
    def test_extract_table_metadata_uses_common_connector_contract(self) -> None:
        connector = MagicMock()
        connector.engine = SimpleNamespace(url=SimpleNamespace(drivername="mssql+pyodbc"), dialect=SimpleNamespace(name="mssql"))
        connector.get_columns.return_value = [
            {
                "name": "CUSTOMER_ID",
                "data_type": "INT",
                "nullable": False,
                "ordinal_position": 1,
            },
            {
                "name": "EMAIL",
                "data_type": "VARCHAR(255)",
                "nullable": True,
                "ordinal_position": 2,
            },
            {
                "name": "CREATED_AT",
                "data_type": "DATETIME2",
                "nullable": True,
                "ordinal_position": 3,
            },
        ]

        extractor = MetadataExtractor(connector, profiler=StubProfiler())
        metadata = extractor.extract_table_metadata("catalog_demo", "dbo", "customers")

        connector.get_columns.assert_called_once_with("dbo", "customers")
        self.assertEqual(metadata.source_type, "sqlserver")
        self.assertEqual(metadata.database_name, "catalog_demo")
        self.assertEqual(metadata.schema_name, "dbo")
        self.assertEqual(metadata.table_name, "customers")
        self.assertEqual(metadata.table_type, "TABLE")
        self.assertEqual(metadata.row_count, 4)
        self.assertEqual([column.column_name for column in metadata.columns], ["CUSTOMER_ID", "EMAIL", "CREATED_AT"])
        self.assertEqual([column.source_data_type for column in metadata.columns], ["INT", "VARCHAR(255)", "DATETIME2"])
        self.assertEqual([column.normalized_data_type for column in metadata.columns], ["NUMBER", "STRING", "DATETIME"])
        self.assertEqual([column.nullable for column in metadata.columns], [False, True, True])
        self.assertEqual([column.ordinal_position for column in metadata.columns], [1, 2, 3])
        self.assertEqual([column.sample_values for column in metadata.columns], [["sample-CUSTOMER_ID"], ["sample-EMAIL"], ["sample-CREATED_AT"]])
        self.assertEqual([column.null_count for column in metadata.columns], [0, 1, 2])
        self.assertEqual([column.distinct_count for column in metadata.columns], [2, 3, 4])

    def test_extract_table_metadata_resolves_postgresql_source_type(self) -> None:
        connector = MagicMock()
        connector.engine = SimpleNamespace(url=SimpleNamespace(drivername="postgresql+psycopg"), dialect=SimpleNamespace(name="postgresql"))
        connector.get_columns.return_value = [
            {
                "name": "order_id",
                "data_type": "INTEGER",
                "nullable": False,
                "ordinal_position": 1,
            },
        ]

        extractor = MetadataExtractor(connector, profiler=StubProfiler())
        metadata = extractor.extract_table_metadata("sales_db", "public", "orders")

        self.assertEqual(metadata.source_type, "postgresql")
        self.assertEqual(metadata.columns[0].normalized_data_type, "NUMBER")

    def test_extract_table_metadata_canonicalizes_explicit_source_alias(self) -> None:
        connector = MagicMock()
        connector.source_type = "postgres"
        connector.engine = None
        connector.get_columns.return_value = [
            {
                "name": "order_id",
                "data_type": "INTEGER",
                "nullable": False,
                "ordinal_position": 1,
            },
        ]

        extractor = MetadataExtractor(connector, profiler=StubProfiler())
        metadata = extractor.extract_table_metadata("sales_db", "public", "orders")

        self.assertEqual(metadata.source_type, "postgresql")

    def test_extract_table_metadata_fallback_class_name_is_canonical(self) -> None:
        class PostgresConnector:
            def __init__(self) -> None:
                self.engine = None

            def get_columns(self, schema_name: str, table_name: str):
                return [
                    {
                        "name": "order_id",
                        "data_type": "INTEGER",
                        "nullable": False,
                        "ordinal_position": 1,
                    }
                ]

        connector = PostgresConnector()
        extractor = MetadataExtractor(connector, profiler=StubProfiler())
        metadata = extractor.extract_table_metadata("sales_db", "public", "orders")

        self.assertEqual(metadata.source_type, "postgresql")
