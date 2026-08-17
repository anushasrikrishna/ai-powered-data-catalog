from __future__ import annotations

import unittest

from catalog.ranking import CatalogRanker, CatalogTokenizer
from catalog.repository import CatalogEntry
from documentation.models import ColumnDocumentation, TableDocumentation, TableTechnicalSummary


def entry(table: str, columns: list[tuple[str, str, str]], *, description: str | None = None, tags: list[str] | None = None) -> CatalogEntry:
    return CatalogEntry(
        documentation=TableDocumentation(
            source_type="postgresql",
            database_name="sales_db",
            schema_name="public",
            table_name=table,
            table_type="TABLE",
            summary=TableTechnicalSummary(row_count=10, column_count=len(columns)),
            columns=[
                ColumnDocumentation(
                    column_name=name,
                    source_data_type=normalized,
                    normalized_data_type=normalized,
                    nullable=True,
                    ordinal_position=index,
                    possible_category=category,
                )
                for index, (name, normalized, category) in enumerate(columns, start=1)
            ],
        ),
        description=description,
        tags=tags or [],
    )


class TestCatalogRanking(unittest.TestCase):
    def setUp(self) -> None:
        self.ranker = CatalogRanker()

    def test_tokenizer_handles_query_and_identifiers(self) -> None:
        expected = ("customer", "orders")
        self.assertEqual(CatalogTokenizer.tokenize(" CustomerOrders "), expected)
        self.assertEqual(CatalogTokenizer.tokenize("CUSTOMER_ORDERS"), expected)
        self.assertEqual(CatalogTokenizer.tokenize("customer-orders"), expected)

    def test_table_name_match_outranks_column_only_match(self) -> None:
        direct = entry("customer_orders", [("id", "NUMBER", "Identifier")])
        columns = entry(
            "transactions",
            [("customer_id", "NUMBER", "Identifier"), ("customer_name", "STRING", "Name")],
        )

        direct_score = self.ranker.rank(direct, ("customer", "order"))
        column_score = self.ranker.rank(columns, ("customer", "order"))

        self.assertGreater(direct_score.score, column_score.score)
        self.assertIn("table_name", direct_score.matched_fields)

    def test_category_description_and_tags_are_searchable(self) -> None:
        category_entry = entry(
            "customers",
            [("email", "STRING", "Contact Information")],
            description="current customer directory",
            tags=["customer", "contact"],
        )

        contact = self.ranker.rank(category_entry, ("contact",))
        customer = self.ranker.rank(category_entry, ("customer",))

        self.assertIn("category", contact.matched_fields)
        self.assertIn("tag", contact.matched_fields)
        self.assertIn("description", customer.matched_fields)
        self.assertGreater(contact.score, 0)
        self.assertGreater(customer.score, 0)

    def test_column_contribution_is_capped(self) -> None:
        many_columns = entry(
            "events",
            [(f"customer_{index}", "STRING", "Other") for index in range(20)],
        )

        breakdown = self.ranker.rank(many_columns, ("customer",))

        self.assertLessEqual(breakdown.components["column_name"], self.ranker.COLUMN_SCORE_CAP)

    def test_direct_table_match_beats_many_matching_columns(self) -> None:
        direct = entry("customers", [])
        many_columns = entry(
            "transactions",
            [(f"customer_{index}", "STRING", "Other") for index in range(20)],
        )

        direct_score = self.ranker.rank(direct, ("customer",))
        many_column_score = self.ranker.rank(many_columns, ("customer",))

        self.assertGreater(direct_score.score, many_column_score.score)
        self.assertLessEqual(many_column_score.components["column_name"], self.ranker.COLUMN_SCORE_CAP)

    def test_duplicate_query_terms_do_not_inflate_score(self) -> None:
        entry_value = entry("customer_orders", [])

        unique = self.ranker.rank(entry_value, ("customer", "order"))
        repeated = self.ranker.rank(entry_value, ("customer", "customer", "order", "order"))

        self.assertEqual(unique.score, repeated.score)

    def test_plural_matching_and_coverage(self) -> None:
        both = entry("customer_orders", [])
        one = entry("customers", [])

        both_score = self.ranker.rank(both, ("customer", "order"))
        one_score = self.ranker.rank(one, ("customer", "order"))

        self.assertGreater(both_score.score, one_score.score)
        self.assertIn("customer", both_score.matched_terms)
        self.assertIn("order", both_score.matched_terms)
