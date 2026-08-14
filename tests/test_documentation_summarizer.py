from __future__ import annotations

from datetime import date
from decimal import Decimal
import unittest

from documentation.models import TableDocumentation
from documentation.summarizer import MetadataDocumentationGenerator
from metadata.models import ColumnMetadata, TableMetadata


class TestMetadataDocumentationGenerator(unittest.TestCase):
    def setUp(self) -> None:
        self.generator = MetadataDocumentationGenerator()
        self.metadata = TableMetadata(
            source_type="postgresql",
            database_name="sales_db",
            schema_name="public",
            table_name="orders",
            table_type="TABLE",
            row_count=10240,
            columns=[
                ColumnMetadata(
                    column_name="order_id",
                    source_data_type="INTEGER",
                    normalized_data_type="NUMBER",
                    nullable=False,
                    ordinal_position=1,
                    null_count=0,
                    distinct_count=10240,
                    minimum=1,
                    maximum=10240,
                    sample_values=[1, 2, 3],
                ),
                ColumnMetadata(
                    column_name="amount",
                    source_data_type="NUMERIC(10,2)",
                    normalized_data_type="DECIMAL",
                    nullable=True,
                    ordinal_position=2,
                    null_count=10,
                    distinct_count=500,
                    minimum=Decimal("1.50"),
                    maximum=Decimal("999.99"),
                    sample_values=[Decimal("1.50"), Decimal("2.00")],
                ),
                ColumnMetadata(
                    column_name="status",
                    source_data_type="VARCHAR(20)",
                    normalized_data_type="STRING",
                    nullable=False,
                    ordinal_position=3,
                    null_count=0,
                    distinct_count=3,
                    minimum="closed",
                    maximum="pending",
                    sample_values=["closed", "open"],
                ),
                ColumnMetadata(
                    column_name="order_date",
                    source_data_type="DATE",
                    normalized_data_type="DATE",
                    nullable=True,
                    ordinal_position=4,
                    null_count=2,
                    distinct_count=100,
                    minimum=date(2026, 1, 1),
                    maximum=date(2026, 2, 1),
                    sample_values=[date(2026, 1, 1)],
                ),
                ColumnMetadata(
                    column_name="created_at",
                    source_data_type="TIMESTAMP",
                    normalized_data_type="DATETIME",
                    nullable=False,
                    ordinal_position=5,
                ),
                ColumnMetadata(
                    column_name="is_active",
                    source_data_type="BOOLEAN",
                    normalized_data_type="BOOLEAN",
                    nullable=False,
                    ordinal_position=6,
                ),
                ColumnMetadata(
                    column_name="payload",
                    source_data_type="BYTEA",
                    normalized_data_type="BINARY",
                    nullable=True,
                    ordinal_position=7,
                ),
                ColumnMetadata(
                    column_name="attributes",
                    source_data_type="JSONB",
                    normalized_data_type="OTHER",
                    nullable=True,
                    ordinal_position=8,
                ),
            ],
        )

    def test_generate_builds_summary_and_preserves_metadata(self) -> None:
        documentation = self.generator.generate(self.metadata)

        self.assertIsInstance(documentation, TableDocumentation)
        self.assertEqual(documentation.source_type, "postgresql")
        self.assertEqual(documentation.database_name, "sales_db")
        self.assertEqual(documentation.schema_name, "public")
        self.assertEqual(documentation.table_name, "orders")
        self.assertEqual(documentation.table_type, "TABLE")
        self.assertEqual(documentation.summary.row_count, 10240)
        self.assertEqual(documentation.summary.column_count, 8)
        self.assertEqual(documentation.summary.nullable_column_count, 4)
        self.assertEqual(documentation.summary.non_nullable_column_count, 4)
        self.assertEqual(documentation.summary.number_column_count, 1)
        self.assertEqual(documentation.summary.decimal_column_count, 1)
        self.assertEqual(documentation.summary.numeric_column_count, 2)
        self.assertEqual(documentation.summary.string_column_count, 1)
        self.assertEqual(documentation.summary.date_column_count, 1)
        self.assertEqual(documentation.summary.datetime_column_count, 1)
        self.assertEqual(documentation.summary.boolean_column_count, 1)
        self.assertEqual(documentation.summary.binary_column_count, 1)
        self.assertEqual(documentation.summary.other_column_count, 1)
        self.assertEqual(
            documentation.summary.nullable_column_count + documentation.summary.non_nullable_column_count,
            documentation.summary.column_count,
        )
        self.assertEqual(
            documentation.summary.number_column_count
            + documentation.summary.decimal_column_count
            + documentation.summary.string_column_count
            + documentation.summary.date_column_count
            + documentation.summary.datetime_column_count
            + documentation.summary.boolean_column_count
            + documentation.summary.binary_column_count
            + documentation.summary.other_column_count,
            documentation.summary.column_count,
        )

    def test_generate_preserves_column_order_profiles_and_categories(self) -> None:
        documentation = self.generator.build_documentation(self.metadata)

        self.assertEqual(
            [column.column_name for column in documentation.columns],
            ["order_id", "amount", "status", "order_date", "created_at", "is_active", "payload", "attributes"],
        )
        self.assertEqual(documentation.columns[0].possible_category, "Identifier")
        self.assertEqual(documentation.columns[1].possible_category, "Financial/Measure")
        self.assertEqual(documentation.columns[3].possible_category, "Date/Time")
        self.assertEqual(documentation.columns[5].possible_category, "Boolean/Flag")
        self.assertEqual(documentation.columns[1].null_count, 10)
        self.assertEqual(documentation.columns[1].distinct_count, 500)
        self.assertEqual(documentation.columns[1].minimum, Decimal("1.50"))
        self.assertEqual(documentation.columns[1].maximum, Decimal("999.99"))
        self.assertEqual(documentation.columns[1].sample_values, [Decimal("1.50"), Decimal("2.00")])

    def test_empty_columns_and_zero_rows_are_supported(self) -> None:
        empty_metadata = TableMetadata(
            source_type="sqlserver",
            database_name="catalog_demo",
            schema_name="dbo",
            table_name="empty_table",
            table_type="TABLE",
            row_count=0,
            columns=[],
        )

        documentation = self.generator.generate(empty_metadata)

        self.assertEqual(documentation.summary.row_count, 0)
        self.assertEqual(documentation.summary.column_count, 0)
        self.assertEqual(documentation.summary.nullable_column_count, 0)
        self.assertEqual(documentation.summary.non_nullable_column_count, 0)
        self.assertEqual(documentation.columns, [])

    def test_same_structure_for_different_sources(self) -> None:
        source_documents = []
        for source_type in ("sqlserver", "postgresql", "snowflake"):
            metadata = self.metadata.model_copy(update={"source_type": source_type})
            source_documents.append(self.generator.generate(metadata))

        for document in source_documents:
            self.assertEqual(document.summary.column_count, 8)
            self.assertEqual(
                document.columns[0].model_dump(exclude={"source_data_type"}),
                source_documents[0].columns[0].model_dump(exclude={"source_data_type"}),
            )
        self.assertEqual([document.source_type for document in source_documents], ["sqlserver", "postgresql", "snowflake"])
