from __future__ import annotations

import unittest

from metadata.models import ColumnMetadata, TableMetadata
from metadata.normalizer import MetadataNormalizer


class TestMetadataNormalizer(unittest.TestCase):
    def setUp(self) -> None:
        self.normalizer = MetadataNormalizer()

    def test_known_datatype_mappings(self) -> None:
        cases = {
            "INT": "NUMBER",
            "BIGINT": "NUMBER",
            "SMALLINT": "NUMBER",
            "TINYINT": "NUMBER",
            "INTEGER": "NUMBER",
            "DECIMAL(10,2)": "DECIMAL",
            "NUMERIC(18,4)": "DECIMAL",
            "VARCHAR(255)": "STRING",
            "NVARCHAR(100)": "STRING",
            "TEXT": "STRING",
            "CHARACTER VARYING": "STRING",
            "DATE": "DATE",
            "DATETIME": "DATETIME",
            "DATETIME2": "DATETIME",
            "TIMESTAMP": "DATETIME",
            "TIMESTAMP WITHOUT TIME ZONE": "DATETIME",
            "TIMESTAMP WITH TIME ZONE": "DATETIME",
            "BIT": "BOOLEAN",
            "BOOLEAN": "BOOLEAN",
            "BOOL": "BOOLEAN",
            "VARBINARY": "BINARY",
            "BYTEA": "BINARY",
            "NUMBER(38,0)": "NUMBER",
            "NUMBER(10,2)": "DECIMAL",
            "FLOAT": "DECIMAL",
            "DOUBLE PRECISION": "DECIMAL",
            "TIMESTAMP_NTZ(9)": "DATETIME",
            "TIMESTAMP_LTZ(9)": "DATETIME",
            "TIMESTAMP_TZ(9)": "DATETIME",
            "BINARY": "BINARY",
            "JSON": "OTHER",
            "JSONB": "OTHER",
            "UUID": "OTHER",
            "VARIANT": "OTHER",
            "OBJECT": "OTHER",
            "ARRAY": "OTHER",
            "GEOGRAPHY": "OTHER",
        }

        for source_type, expected in cases.items():
            with self.subTest(source_type=source_type):
                self.assertEqual(self.normalizer.normalize_data_type(source_type), expected)

    def test_canonicalization_handles_whitespace_and_case(self) -> None:
        self.assertEqual(self.normalizer.normalize_data_type("  varchar( 255 )  "), "STRING")
        self.assertEqual(self.normalizer.normalize_data_type("  integer  "), "NUMBER")
        self.assertEqual(self.normalizer.normalize_data_type("  decimal( 10 , 0 )  "), "DECIMAL")

    def test_sqlserver_collate_suffix_is_ignored(self) -> None:
        cases = {
            'VARCHAR(100) COLLATE "SQL_Latin1_General_CP1_CI_AS"': "STRING",
            'VARCHAR(150) COLLATE "Different_Collation"': "STRING",
            'NVARCHAR(100) COLLATE "SQL_Latin1_General_CP1_CI_AS"': "STRING",
            'CHAR(20) COLLATE "SQL_Latin1_General_CP1_CI_AS"': "STRING",
            'NCHAR(20) COLLATE "SQL_Latin1_General_CP1_CI_AS"': "STRING",
        }

        for source_type, expected in cases.items():
            with self.subTest(source_type=source_type):
                self.assertEqual(self.normalizer.normalize_data_type(source_type), expected)

    def test_normalize_column_and_table_metadata(self) -> None:
        table_metadata = TableMetadata(
            source_type="postgresql",
            database_name="sales_db",
            schema_name="public",
            table_name="orders",
            columns=[
                ColumnMetadata(
                    column_name="order_id",
                    source_data_type="INTEGER",
                    normalized_data_type="OTHER",
                    nullable=False,
                    ordinal_position=1,
                ),
                ColumnMetadata(
                    column_name="amount",
                    source_data_type="NUMERIC(10,2)",
                    normalized_data_type="OTHER",
                    nullable=True,
                    ordinal_position=2,
                ),
            ],
        )

        normalized = self.normalizer.normalize_table_metadata(table_metadata)

        self.assertEqual(normalized.columns[0].normalized_data_type, "NUMBER")
        self.assertEqual(normalized.columns[1].normalized_data_type, "DECIMAL")
        self.assertEqual(normalized.columns[0].column_name, "order_id")
        self.assertEqual(normalized.columns[1].column_name, "amount")
