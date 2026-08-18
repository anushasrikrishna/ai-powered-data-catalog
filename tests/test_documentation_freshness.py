from __future__ import annotations

from tempfile import TemporaryDirectory
import unittest
from pathlib import Path

from documentation import MetadataDocumentationGenerator
from metadata.models import ColumnMetadata, TableMetadata
from storage.repository import MetadataRepository


class TestDocumentationFreshness(unittest.TestCase):
    def test_rescan_replaces_the_documentation_projection(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            repository = MetadataRepository(Path(temporary_directory) / "metadata.db")
            generator = MetadataDocumentationGenerator()

            repository.save_table_metadata(
                self._metadata(
                    row_count=5,
                    columns=[
                        self._column("customer_id", "NUMBER", 1),
                        self._column("email", "STRING", 2),
                    ],
                )
            )
            first = generator.generate(
                repository.get_table_metadata("postgresql", "sales", "public", "customers")
            )

            repository.save_table_metadata(
                self._metadata(
                    row_count=12,
                    columns=[
                        self._column("customer_id", "NUMBER", 1),
                        self._column("created_at", "DATETIME", 2),
                        self._column("amount", "DECIMAL", 3),
                    ],
                )
            )
            latest_metadata = repository.get_table_metadata(
                "postgresql", "sales", "public", "customers"
            )
            second = generator.generate(latest_metadata)

            self.assertEqual(first.summary.row_count, 5)
            self.assertEqual(first.summary.column_count, 2)
            self.assertEqual(second.summary.row_count, 12)
            self.assertEqual(second.summary.column_count, 3)
            self.assertEqual(
                [column.column_name for column in second.columns],
                ["customer_id", "created_at", "amount"],
            )
            self.assertEqual(
                [column.possible_category for column in second.columns],
                ["Identifier", "Date/Time", "Financial/Measure"],
            )

    def _metadata(self, row_count: int, columns: list[ColumnMetadata]) -> TableMetadata:
        return TableMetadata(
            source_type="postgresql",
            database_name="sales",
            schema_name="public",
            table_name="customers",
            row_count=row_count,
            columns=columns,
        )

    def _column(self, name: str, normalized_type: str, position: int) -> ColumnMetadata:
        return ColumnMetadata(
            column_name=name,
            source_data_type=normalized_type,
            normalized_data_type=normalized_type,
            nullable=True,
            ordinal_position=position,
        )


if __name__ == "__main__":
    unittest.main()
