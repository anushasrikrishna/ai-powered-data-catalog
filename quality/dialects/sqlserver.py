from __future__ import annotations

from typing import Any

from sqlalchemy import bindparam, case, func, literal_column
from sqlalchemy.sql import Select

from metadata.models import TableMetadata
from quality.dialects.base import QualityDialect
from quality.rule_models import (
    AcceptedValuesRule,
    DuplicateRule,
    FreshnessRule,
    NotNullRule,
    NumericRangeRule,
    QualityRule,
    StringLengthRule,
    UniqueRule,
)


class SQLServerQualityDialect(QualityDialect):
    """SQL Server quality SQL using safe reflected identifiers and bound values.

    String-length rules use SQL Server ``LEN``, which ignores trailing spaces.
    """

    def build_check_statement(
        self,
        engine: Any,
        table_metadata: TableMetadata,
        rule: QualityRule,
    ) -> Select[Any]:
        table = self._reflect_table(engine, table_metadata)
        column = self._column(table, rule.column)

        if isinstance(rule, (DuplicateRule, UniqueRule)):
            return self._duplicate_aggregate(table, column)
        if isinstance(rule, NotNullRule):
            return self._aggregate(table, case((column.is_(None), 1), else_=0))
        if isinstance(rule, AcceptedValuesRule):
            predicate = column.is_not(None) & column.not_in(
                bindparam("accepted_values", expanding=True)
            )
            return self._aggregate(table, case((predicate, 1), else_=0))
        if isinstance(rule, NumericRangeRule):
            predicates = []
            if rule.min_value is not None:
                predicates.append(column < bindparam("min_value"))
            if rule.max_value is not None:
                predicates.append(column > bindparam("max_value"))
            predicate = column.is_not(None) & self._or(predicates)
            return self._aggregate(table, case((predicate, 1), else_=0))
        if isinstance(rule, StringLengthRule):
            predicates = []
            if rule.min_length is not None:
                predicates.append(func.len(column) < bindparam("min_length"))
            if rule.max_length is not None:
                predicates.append(func.len(column) > bindparam("max_length"))
            predicate = column.is_not(None) & self._or(predicates)
            return self._aggregate(table, case((predicate, 1), else_=0))
        if isinstance(rule, FreshnessRule):
            cutoff = func.dateadd(
                literal_column("day"),
                -bindparam("max_age_days"),
                func.current_timestamp(),
            )
            predicate = column.is_not(None) & (column < cutoff)
            return self._aggregate(table, case((predicate, 1), else_=0))
        raise TypeError(f"Unsupported quality rule: {type(rule).__name__}")

    def _or(self, predicates: list[Any]) -> Any:
        if len(predicates) == 1:
            return predicates[0]
        return predicates[0] | predicates[1]


__all__ = ["SQLServerQualityDialect"]
