from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy import MetaData, Table, func, select
from sqlalchemy.sql import Select

from metadata.models import TableMetadata
from quality.rule_models import QualityRule


class QualityDialect(ABC):
    """Database-specific builder for explicit read-only quality aggregates."""

    @abstractmethod
    def build_check_statement(
        self,
        engine: Any,
        table_metadata: TableMetadata,
        rule: QualityRule,
    ) -> Select[Any]:
        """Build one aggregate SELECT returning total_records and failed_records."""
        raise NotImplementedError

    def _reflect_table(self, engine: Any, table_metadata: TableMetadata) -> Table:
        return Table(
            table_metadata.table_name,
            MetaData(),
            schema=table_metadata.schema_name or None,
            autoload_with=engine,
        )

    def _aggregate(self, table: Table, failure_predicate: Any) -> Select[Any]:
        return select(
            func.count().label("total_records"),
            func.coalesce(
                func.sum(failure_predicate),
                0,
            ).label("failed_records"),
        ).select_from(table)

    def _duplicate_aggregate(self, table: Table, column: Any) -> Select[Any]:
        duplicate_groups = (
            select(column.label("duplicate_value"), func.count().label("group_count"))
            .select_from(table)
            .where(column.is_not(None))
            .group_by(column)
            .having(func.count() > 1)
            .subquery()
        )
        failed_records = select(
            func.coalesce(func.sum(duplicate_groups.c.group_count), 0)
        ).scalar_subquery()
        return select(
            func.count().label("total_records"),
            failed_records.label("failed_records"),
        ).select_from(table)

    def build_failure_detail_statement(
        self,
        engine: Any,
        table_metadata: TableMetadata,
        rule: QualityRule,
        limit: int,
    ) -> Select[Any] | None:
        """Return a bounded grouped failure-value query when the dialect supports it."""
        return None

    def _grouped_failure_detail(self, table: Table, column: Any, predicate: Any, limit: int) -> Select[Any]:
        count = func.count().label("failure_count")
        return (
            select(column.label("failed_value"), count)
            .select_from(table)
            .where(predicate)
            .group_by(column)
            .order_by(count.desc())
            .limit(max(1, min(int(limit), 20)))
        )

    def _duplicate_failure_detail(self, table: Table, column: Any, limit: int) -> Select[Any]:
        duplicate_values = (
            select(column.label("duplicate_value"))
            .select_from(table)
            .where(column.is_not(None))
            .group_by(column)
            .having(func.count() > 1)
            .subquery()
        )
        return self._grouped_failure_detail(
            table,
            column,
            column.in_(select(duplicate_values.c.duplicate_value)),
            limit,
        )

    def _column(self, table: Table, column_name: str) -> Any:
        if column_name in table.c:
            return table.c[column_name]
        lower_columns = {column.name.lower(): column for column in table.columns}
        if column_name.lower() in lower_columns:
            return lower_columns[column_name.lower()]
        raise KeyError(f"Column '{column_name}' was not found in table metadata.")
