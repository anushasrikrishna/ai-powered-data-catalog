from __future__ import annotations

import unittest

from ui.page_state import load_widget_state, store_widget_state


class TestPageState(unittest.TestCase):
    def test_permanent_value_survives_widget_removal_and_is_restored(self) -> None:
        state = {}
        load_widget_state(state, "catalog_search", "_catalog_search_widget", "")
        state["_catalog_search_widget"] = "customer"
        store_widget_state(state, "catalog_search", "_catalog_search_widget")
        state.pop("_catalog_search_widget")

        load_widget_state(state, "catalog_search", "_catalog_search_widget", "")

        self.assertEqual(state["catalog_search"], "customer")
        self.assertEqual(state["_catalog_search_widget"], "customer")

    def test_invalid_restored_option_resets_only_that_value(self) -> None:
        state = {"catalog_source": "Missing Source", "catalog_search": "customer"}

        load_widget_state(state, "catalog_source", "_catalog_source_widget", "All Sources", ["All Sources", "SQL Server"])

        self.assertEqual(state["catalog_source"], "All Sources")
        self.assertEqual(state["_catalog_source_widget"], "All Sources")
        self.assertEqual(state["catalog_search"], "customer")


if __name__ == "__main__":
    unittest.main()
