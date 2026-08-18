from __future__ import annotations

import unittest

from ui.components import sanitize_table_id, table_to_csv


class TestTableHelpers(unittest.TestCase):
    def test_table_id_is_stable_and_dom_safe(self) -> None:
        self.assertEqual(sanitize_table_id("Catalog Results / 2026"), "Catalog-Results-2026")
        self.assertEqual(sanitize_table_id("!!!"), "table")

    def test_csv_contains_raw_values_without_html_markup(self) -> None:
        csv_text = table_to_csv(
            [
                {"Column": "customer_id", "Possible Category": "Identifier", "Nullable": "No"},
                {"Column": "email", "Possible Category": "Contact Information", "Nullable": "Yes"},
            ]
        )

        self.assertIn("Column,Possible Category,Nullable", csv_text)
        self.assertIn("customer_id,Identifier,No", csv_text)
        self.assertIn("email,Contact Information,Yes", csv_text)
        self.assertNotIn("<span", csv_text)


if __name__ == "__main__":
    unittest.main()
