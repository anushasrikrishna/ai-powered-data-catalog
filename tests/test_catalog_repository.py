from __future__ import annotations

import unittest

from catalog.repository import CatalogEntry, CatalogRepository
from documentation.models import ColumnDocumentation, TableDocumentation, TableTechnicalSummary


def documentation(source: str, database: str, schema: str, table: str) -> TableDocumentation:
    return TableDocumentation(
        source_type=source,
        database_name=database,
        schema_name=schema,
        table_name=table,
        table_type="TABLE",
        summary=TableTechnicalSummary(row_count=1, column_count=1),
        columns=[
            ColumnDocumentation(
                column_name="id",
                source_data_type="INTEGER",
                normalized_data_type="NUMBER",
                nullable=False,
                ordinal_position=1,
                possible_category="Identifier",
            )
        ],
    )


class TestCatalogRepository(unittest.TestCase):
    def test_stable_identity_keeps_same_table_names_distinct(self) -> None:
        repository = CatalogRepository()
        sql_entry = CatalogEntry.from_documentation(documentation("sqlserver", "crm", "dbo", "customers"))
        postgres_entry = CatalogEntry.from_documentation(documentation("postgresql", "sales", "public", "customers"))

        repository.add(sql_entry)
        repository.add(postgres_entry)

        self.assertEqual(len(repository), 2)
        self.assertNotEqual(sql_entry.dataset_id, postgres_entry.dataset_id)
        self.assertIs(repository.get(sql_entry.dataset_id), sql_entry)
        self.assertIs(repository.get_by_identity("postgresql", "sales", "public", "customers"), postgres_entry)

    def test_duplicate_identity_replaces_existing_entry(self) -> None:
        repository = CatalogRepository()
        first = CatalogEntry.from_documentation(documentation("postgresql", "sales", "public", "orders"), tags=["old"])
        replacement = CatalogEntry.from_documentation(documentation("postgresql", "sales", "public", "orders"), tags=["new"])

        repository.add(first)
        repository.add(replacement)

        self.assertEqual(len(repository), 1)
        self.assertEqual(repository.get(first.dataset_id).tags, ["new"])

    def test_get_all_is_deterministic_and_missing_returns_none(self) -> None:
        repository = CatalogRepository(
            [
                CatalogEntry.from_documentation(documentation("postgresql", "sales", "public", "z_table")),
                CatalogEntry.from_documentation(documentation("postgresql", "sales", "public", "a_table")),
            ]
        )

        self.assertEqual([entry.documentation.table_name for entry in repository.get_all()], ["a_table", "z_table"])
        self.assertIsNone(repository.get("missing|database|schema|table"))

    def test_remove_returns_entry_and_missing_remove_returns_none(self) -> None:
        repository = CatalogRepository()
        entry_value = CatalogEntry.from_documentation(documentation("postgresql", "sales", "public", "orders"))
        repository.add(entry_value)

        self.assertIs(repository.remove(entry_value.dataset_id), entry_value)
        self.assertIsNone(repository.get(entry_value.dataset_id))
        self.assertIsNone(repository.remove(entry_value.dataset_id))
