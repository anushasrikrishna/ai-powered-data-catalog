from __future__ import annotations

import unittest

from catalog.repository import CatalogEntry, CatalogRepository
from catalog.search import CatalogFilters, CatalogSearch
from documentation.models import ColumnDocumentation, TableDocumentation, TableTechnicalSummary


def entry(source: str, database: str, schema: str, table: str, *, quality: float | None = None, columns: list[tuple[str, str]] | None = None) -> CatalogEntry:
    columns = columns or [("id", "Identifier")]
    documentation = TableDocumentation(
        source_type=source,
        database_name=database,
        schema_name=schema,
        table_name=table,
        table_type="TABLE",
        summary=TableTechnicalSummary(row_count=10, column_count=len(columns)),
        columns=[
            ColumnDocumentation(
                column_name=name,
                source_data_type="STRING",
                normalized_data_type="STRING",
                nullable=True,
                ordinal_position=index,
                possible_category=category,
            )
            for index, (name, category) in enumerate(columns, start=1)
        ],
    )
    return CatalogEntry(documentation=documentation, quality_score=quality)


class TestCatalogSearch(unittest.TestCase):
    def setUp(self) -> None:
        repository = CatalogRepository(
            [
                entry("postgresql", "sales_db", "public", "customer_orders", quality=90, columns=[("customer_id", "Identifier")]),
                entry("sqlserver", "crm", "dbo", "customers", quality=None, columns=[("email", "Contact Information")]),
                entry("snowflake", "analytics", "public", "events", quality=75),
            ]
        )
        self.search = CatalogSearch(repository)

    def test_empty_and_whitespace_queries_browse_deterministically(self) -> None:
        empty = self.search.search("")
        whitespace = self.search.search("   ")

        self.assertEqual([result.entry.documentation.table_name for result in empty], ["customer_orders", "customers", "events"])
        self.assertEqual([result.dataset_id for result in empty], [result.dataset_id for result in whitespace])
        self.assertTrue(all(result.score == 0 for result in empty))

    def test_search_ranks_table_match_and_excludes_zero_matches(self) -> None:
        results = self.search.search("customer order")

        self.assertEqual(results[0].entry.documentation.table_name, "customer_orders")
        self.assertTrue(all(result.score > 0 for result in results))
        self.assertNotIn("events", [result.entry.documentation.table_name for result in results])

    def test_case_normalization_and_filters_use_and_semantics(self) -> None:
        results = self.search.search(
            "CUSTOMER",
            filters=CatalogFilters(
                source_type="POSTGRESQL",
                database_name="SALES_DB",
                schema_name="PUBLIC",
                min_quality_score=80,
                max_quality_score=95,
            ),
        )

        self.assertEqual([result.entry.documentation.table_name for result in results], ["customer_orders"])

    def test_missing_quality_score_is_excluded_only_when_quality_filter_requested(self) -> None:
        without_filter = self.search.search("email")
        with_filter = self.search.search("email", min_quality_score=80)

        self.assertEqual([result.entry.documentation.table_name for result in without_filter], ["customers"])
        self.assertEqual(with_filter, [])

    def test_limit_and_invalid_filters(self) -> None:
        self.assertEqual(len(self.search.search("", limit=1)), 1)
        with self.assertRaises(ValueError):
            self.search.search("", limit=-1)
        with self.assertRaises(ValueError):
            CatalogFilters(min_quality_score=90, max_quality_score=80)
        with self.assertRaises(ValueError):
            CatalogFilters(min_quality_score=101)

    def test_optional_description_and_tags_are_supported(self) -> None:
        custom_entry = entry("postgresql", "sales_db", "public", "archive", quality=None)
        custom_entry.description = "historical customer purchases"
        custom_entry.tags = ["customer", "purchase"]
        self.search.repository.add(custom_entry)

        results = self.search.search("purchase")

        self.assertEqual(results[0].entry.documentation.table_name, "archive")

    def test_quality_score_does_not_change_relevance_order(self) -> None:
        low_quality = entry("postgresql", "sales_db", "public", "customer_orders", quality=10)
        high_quality = entry("sqlserver", "crm", "dbo", "archive", quality=100)
        repository_a = CatalogRepository([high_quality, low_quality])
        repository_b = CatalogRepository([low_quality, high_quality])

        results_a = CatalogSearch(repository_a).search("customer orders")
        results_b = CatalogSearch(repository_b).search("customer orders")

        self.assertEqual(
            [(result.dataset_id, result.score) for result in results_a],
            [(result.dataset_id, result.score) for result in results_b],
        )
        self.assertEqual(results_a[0].entry.documentation.table_name, "customer_orders")

    def test_insertion_order_does_not_change_browse_or_ranked_results(self) -> None:
        entries = self.search.repository.get_all()
        first = CatalogSearch(CatalogRepository(entries)).search("customer")
        second = CatalogSearch(CatalogRepository(reversed(entries))).search("customer")

        self.assertEqual(
            [(result.dataset_id, result.score) for result in first],
            [(result.dataset_id, result.score) for result in second],
        )
