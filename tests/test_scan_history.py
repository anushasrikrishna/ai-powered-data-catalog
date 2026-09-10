from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from metadata.models import ColumnMetadata, TableMetadata
from storage.repository import MetadataRepository
from storage.scan_history import compare_snapshots


class TestScanHistory(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repository = MetadataRepository(Path(self.temp_dir.name) / "history.sqlite")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _metadata(self, rows: int, columns: list[ColumnMetadata]) -> TableMetadata:
        return TableMetadata(
            source_type="postgresql",
            database_name="sales",
            schema_name="public",
            table_name="orders",
            row_count=rows,
            columns=columns,
        )

    def _column(self, name: str, data_type: str = "INTEGER", *, nullable: bool = False, null_count: int = 0) -> ColumnMetadata:
        return ColumnMetadata(
            column_name=name,
            source_data_type=data_type,
            normalized_data_type="NUMBER" if data_type == "INTEGER" else "STRING",
            nullable=nullable,
            ordinal_position=1,
            null_count=null_count,
            distinct_count=10,
        )

    def test_first_scan_has_no_previous_comparison(self) -> None:
        self.repository.save_table_metadata(self._metadata(100, [self._column("id")]), scanned_at="2026-09-07T10:00:00+00:00")
        history = self.repository.list_scan_history("postgresql", "sales", "public", "orders")
        self.assertEqual(len(history), 1)
        self.assertIsNone(self.repository.get_scan_comparison("postgresql", "sales", "public", "orders"))

    def test_second_scan_returns_previous_and_current_values(self) -> None:
        self.repository.save_table_metadata(self._metadata(100, [self._column("id")]), scanned_at="2026-09-07T10:00:00+00:00")
        self.repository.save_table_metadata(self._metadata(120, [self._column("id"), self._column("status", "VARCHAR", nullable=True)]), scanned_at="2026-09-07T11:00:00+00:00")
        comparison = self.repository.get_scan_comparison("postgresql", "sales", "public", "orders")
        assert comparison is not None
        self.assertEqual(comparison.previous.row_count, 100)
        self.assertEqual(comparison.current.row_count, 120)
        self.assertEqual(comparison.net_row_change, 20)
        self.assertEqual(comparison.growth_percent, 20.0)
        self.assertEqual(comparison.added_columns, ("status",))
        self.assertEqual(comparison.column_change, 1)

    def test_decrease_and_zero_baseline_are_safe(self) -> None:
        self.repository.save_table_metadata(self._metadata(100, [self._column("id")]), scanned_at="2026-09-07T10:00:00+00:00")
        self.repository.save_table_metadata(self._metadata(80, [self._column("id")]), scanned_at="2026-09-07T11:00:00+00:00")
        comparison = self.repository.get_scan_comparison("postgresql", "sales", "public", "orders")
        assert comparison is not None
        self.assertEqual(comparison.net_row_change, -20)
        self.assertEqual(comparison.growth_percent, -20.0)

        zero_previous = self.repository.list_scan_history("postgresql", "sales", "public", "orders")[0]
        zero_current = zero_previous.__class__(
            scan_id=999,
            source_type=zero_previous.source_type,
            database_name=zero_previous.database_name,
            schema_name=zero_previous.schema_name,
            table_name=zero_previous.table_name,
            table_type=zero_previous.table_type,
            scanned_at=zero_previous.scanned_at,
            row_count=10,
            columns=zero_previous.columns,
        )
        zero_base = zero_previous.__class__(**{**zero_current.__dict__, "row_count": 0})
        self.assertIsNone(compare_snapshots(zero_base, zero_current).growth_percent)

    def test_type_nullability_and_removed_columns_are_detected(self) -> None:
        previous = self._metadata(10, [self._column("id"), self._column("legacy")])
        current = self._metadata(10, [self._column("id", "VARCHAR", nullable=True, null_count=2)])
        self.repository.save_table_metadata(previous, scanned_at="2026-09-07T10:00:00+00:00")
        self.repository.save_table_metadata(current, scanned_at="2026-09-07T11:00:00+00:00")
        comparison = self.repository.get_scan_comparison("postgresql", "sales", "public", "orders")
        assert comparison is not None
        self.assertEqual(comparison.removed_columns, ("legacy",))
        self.assertEqual(comparison.type_changes[0]["column"], "id")
        self.assertEqual(comparison.nullability_changes[0]["column"], "id")

    def test_history_is_newest_first_and_bounded(self) -> None:
        for hour in (10, 11, 12):
            self.repository.save_table_metadata(self._metadata(hour, [self._column("id")]), scanned_at=f"2026-09-07T{hour:02d}:00:00+00:00")
        history = self.repository.list_scan_history("postgresql", "sales", "public", "orders", limit=2)
        self.assertEqual([item.row_count for item in history], [12, 11])


if __name__ == "__main__":
    unittest.main()
