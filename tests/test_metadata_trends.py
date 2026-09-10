import unittest

from ui.metadata_trends import build_dataset_growth_trend_svg, build_schema_evolution_trend_svg


class MetadataTrendTests(unittest.TestCase):
    def test_trends_are_hidden_until_two_snapshots_exist(self) -> None:
        self.assertIsNone(build_dataset_growth_trend_svg([("01 Jan 2026", 10, None, None)]))
        self.assertIsNone(build_schema_evolution_trend_svg([("01 Jan 2026", 2, None, 0, 0, 0)]))

    def test_growth_trend_contains_rows_and_change_tooltips(self) -> None:
        svg = build_dataset_growth_trend_svg(
            [("01 Jan 2026", 43, None, None), ("02 Jan 2026", 43, 0, 0), ("03 Jan 2026", 46, 3, 6.98)]
        )
        self.assertIsNotNone(svg)
        self.assertIn("Dataset growth trend", svg)
        self.assertIn("46 rows", svg)
        self.assertIn("+3", svg)
        self.assertIn("+6.98%", svg)

    def test_schema_trend_contains_change_breakdown_tooltip(self) -> None:
        svg = build_schema_evolution_trend_svg(
            [("01 Jan 2026", 2, None, 0, 0, 0), ("02 Jan 2026", 3, 2, 1, 0, 1)]
        )
        self.assertIsNotNone(svg)
        self.assertIn("metadata-trend-bar", svg)
        self.assertIn("Added: 1", svg)
        self.assertIn("Schema changes: 2", svg)


if __name__ == "__main__":
    unittest.main()
