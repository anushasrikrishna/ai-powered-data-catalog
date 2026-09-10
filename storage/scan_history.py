from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from metadata.models import ColumnMetadata


@dataclass(frozen=True)
class ScanSnapshot:
    scan_id: int
    source_type: str
    database_name: str
    schema_name: str
    table_name: str
    table_type: str
    scanned_at: str
    row_count: int | None
    columns: tuple[ColumnMetadata, ...] = field(default_factory=tuple)

    @property
    def column_count(self) -> int:
        return len(self.columns)


@dataclass(frozen=True)
class ScanComparison:
    previous: ScanSnapshot
    current: ScanSnapshot
    net_row_change: int | None
    growth_percent: float | None
    column_change: int
    added_columns: tuple[str, ...]
    removed_columns: tuple[str, ...]
    type_changes: tuple[dict[str, str], ...]
    nullability_changes: tuple[dict[str, str], ...]
    null_count_changes: tuple[dict[str, str], ...]
    distinct_count_changes: tuple[dict[str, str], ...]

    @property
    def schema_change_count(self) -> int:
        return (
            len(self.added_columns)
            + len(self.removed_columns)
            + len(self.type_changes)
            + len(self.nullability_changes)
        )


def compare_snapshots(previous: ScanSnapshot, current: ScanSnapshot) -> ScanComparison:
    previous_rows = previous.row_count
    current_rows = current.row_count
    net_row_change = None if previous_rows is None or current_rows is None else current_rows - previous_rows
    growth_percent = None
    if previous_rows not in (None, 0) and current_rows is not None:
        growth_percent = (current_rows - previous_rows) / previous_rows * 100

    previous_columns = {column.column_name: column for column in previous.columns}
    current_columns = {column.column_name: column for column in current.columns}
    added = tuple(sorted(set(current_columns) - set(previous_columns)))
    removed = tuple(sorted(set(previous_columns) - set(current_columns)))
    type_changes: list[dict[str, str]] = []
    nullability_changes: list[dict[str, str]] = []
    null_count_changes: list[dict[str, str]] = []
    distinct_count_changes: list[dict[str, str]] = []

    for name in sorted(set(previous_columns) & set(current_columns)):
        old = previous_columns[name]
        new = current_columns[name]
        if old.normalized_data_type != new.normalized_data_type or old.source_data_type != new.source_data_type:
            type_changes.append({"column": name, "from": old.normalized_data_type, "to": new.normalized_data_type})
        if old.nullable != new.nullable:
            nullability_changes.append({"column": name, "from": "Nullable" if old.nullable else "Required", "to": "Nullable" if new.nullable else "Required"})
        if old.null_count != new.null_count:
            null_count_changes.append({"column": name, "from": _format_value(old.null_count), "to": _format_value(new.null_count)})
        if old.distinct_count != new.distinct_count:
            distinct_count_changes.append({"column": name, "from": _format_value(old.distinct_count), "to": _format_value(new.distinct_count)})

    return ScanComparison(
        previous=previous,
        current=current,
        net_row_change=net_row_change,
        growth_percent=growth_percent,
        column_change=current.column_count - previous.column_count,
        added_columns=added,
        removed_columns=removed,
        type_changes=tuple(type_changes),
        nullability_changes=tuple(nullability_changes),
        null_count_changes=tuple(null_count_changes),
        distinct_count_changes=tuple(distinct_count_changes),
    )


def _format_value(value: Any) -> str:
    return "—" if value is None else f"{value:,}" if isinstance(value, int) else str(value)


__all__ = ["ScanComparison", "ScanSnapshot", "compare_snapshots"]
