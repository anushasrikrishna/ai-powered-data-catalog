from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from metadata.models import TableMetadata
from quality.dialects.base import QualityDialect
from quality.dialects.postgres import PostgresQualityDialect
from quality.dialects.snowflake import SnowflakeQualityDialect
from quality.dialects.sqlserver import SQLServerQualityDialect
from quality.rule_models import (
    FreshnessRule,
    NumericRangeRule,
    QualityRule,
    StringLengthRule,
    parse_quality_rule,
)


FAILURE_DETAIL_LIMIT = 10


class QualityResult(BaseModel):
    """Factual result for one executed quality rule."""

    model_config = ConfigDict(extra="forbid")
    rule_type: str
    column: str
    rule_config: dict[str, Any] = Field(default_factory=dict)
    total_records: int = 0
    passed_records: int = 0
    failed_records: int = 0
    failure_percentage: float = 0.0
    status: Literal["PASS", "FAIL", "ERROR"]
    error_message: str | None = None


class QualityReport(BaseModel):
    """Serializable aggregate quality evaluation for one table."""

    source_type: str
    database_name: str
    schema_name: str
    table_name: str
    total_rules: int
    passed_rules: int
    failed_rules: int
    error_rules: int
    quality_score: float | None
    results: list[QualityResult] = Field(default_factory=list)


class QualityRuleEngine:
    """Execute validated, explicit quality rules through registered dialects."""

    def __init__(self, dialects: dict[str, QualityDialect] | None = None) -> None:
        self._dialects: dict[str, QualityDialect] = {
            "sqlserver": SQLServerQualityDialect(),
            "postgresql": PostgresQualityDialect(),
            "snowflake": SnowflakeQualityDialect(),
        }
        if dialects:
            for source_type, dialect in dialects.items():
                self.register_dialect(source_type, dialect)

    def register_dialect(self, source_type: str, dialect: QualityDialect) -> None:
        """Register a future source dialect, such as Person 2's Snowflake dialect."""
        self._dialects[self._canonical_source_type(source_type)] = dialect

    def execute_rule(
        self,
        connector: Any,
        table_metadata: TableMetadata,
        rule: QualityRule | dict[str, Any],
    ) -> QualityResult:
        validated_rule = parse_quality_rule(rule)
        self._validate_rule_against_metadata(table_metadata, validated_rule)
        dialect = self._dialect_for(table_metadata.source_type)
        engine = getattr(connector, "engine", None)
        if engine is None:
            raise ValueError("connector must expose a SQLAlchemy engine")

        try:
            statement = dialect.build_check_statement(engine, table_metadata, validated_rule)
            parameters = self._parameters(validated_rule)
            with engine.connect() as connection:
                row = connection.execute(statement, parameters).mappings().one()
            return self._result_from_counts(validated_rule, row)
        except Exception as exc:
            return self._error_result(validated_rule, exc)

    def execute_rules(
        self,
        connector: Any,
        table_metadata: TableMetadata,
        rules: Iterable[QualityRule | dict[str, Any]],
    ) -> QualityReport:
        validated_rules = [parse_quality_rule(rule) for rule in rules]
        results: list[QualityResult] = []
        for rule in validated_rules:
            self._validate_rule_against_metadata(table_metadata, rule)
            results.append(self.execute_rule(connector, table_metadata, rule))

        successful_results = [result for result in results if result.status in {"PASS", "FAIL"}]
        evaluated_records = sum(result.total_records for result in successful_results)
        passed_records = sum(result.passed_records for result in successful_results)
        quality_score = (
            round(passed_records / evaluated_records * 100, 2)
            if evaluated_records
            else None
        )
        return QualityReport(
            source_type=table_metadata.source_type,
            database_name=table_metadata.database_name,
            schema_name=table_metadata.schema_name,
            table_name=table_metadata.table_name,
            total_rules=len(results),
            passed_rules=sum(result.status == "PASS" for result in results),
            failed_rules=sum(result.status == "FAIL" for result in results),
            error_rules=sum(result.status == "ERROR" for result in results),
            quality_score=quality_score,
            results=results,
        )

    def inspect_failed_values(
        self,
        connector: Any,
        table_metadata: TableMetadata,
        rule: QualityRule | dict[str, Any],
        limit: int = FAILURE_DETAIL_LIMIT,
    ) -> list[dict[str, Any]]:
        """Lazily retrieve a small, grouped set of live failure values."""
        validated_rule = parse_quality_rule(rule)
        self._validate_rule_against_metadata(table_metadata, validated_rule)
        dialect = self._dialect_for(table_metadata.source_type)
        engine = getattr(connector, "engine", None)
        if engine is None:
            raise ValueError("connector must expose a SQLAlchemy engine")
        statement = dialect.build_failure_detail_statement(
            engine,
            table_metadata,
            validated_rule,
            max(1, min(int(limit), 20)),
        )
        if statement is None:
            return []
        parameters = self._parameters(validated_rule)
        with engine.connect() as connection:
            rows = connection.execute(statement, parameters).mappings().all()
        return [
            {"failed_value": row.get("failed_value"), "failure_count": int(row.get("failure_count") or 0)}
            for row in rows
        ]

    def _dialect_for(self, source_type: str) -> QualityDialect:
        canonical_source = self._canonical_source_type(source_type)
        try:
            return self._dialects[canonical_source]
        except KeyError as exc:
            raise ValueError(f"No quality dialect is registered for source '{source_type}'.") from exc

    def _validate_rule_against_metadata(
        self,
        table_metadata: TableMetadata,
        rule: QualityRule,
    ) -> None:
        column = next(
            (column for column in table_metadata.columns if column.column_name.lower() == rule.column.lower()),
            None,
        )
        if column is None:
            raise ValueError(f"Column '{rule.column}' was not found in table metadata.")

        normalized_type = column.normalized_data_type.upper()
        if isinstance(rule, NumericRangeRule) and normalized_type not in {"NUMBER", "DECIMAL"}:
            raise ValueError("numeric_range requires a NUMBER or DECIMAL column")
        if isinstance(rule, StringLengthRule) and normalized_type != "STRING":
            raise ValueError("string_length requires a STRING column")
        if isinstance(rule, FreshnessRule) and normalized_type not in {"DATE", "DATETIME"}:
            raise ValueError("freshness requires a DATE or DATETIME column")

    def _parameters(self, rule: QualityRule) -> dict[str, Any]:
        values: dict[str, Any] = {}
        if hasattr(rule, "accepted_values"):
            values["accepted_values"] = rule.accepted_values
        if isinstance(rule, NumericRangeRule):
            if rule.min_value is not None:
                values["min_value"] = rule.min_value
            if rule.max_value is not None:
                values["max_value"] = rule.max_value
        if isinstance(rule, StringLengthRule):
            if rule.min_length is not None:
                values["min_length"] = rule.min_length
            if rule.max_length is not None:
                values["max_length"] = rule.max_length
        if isinstance(rule, FreshnessRule):
            values["max_age_days"] = rule.max_age_days
        return values

    def _result_from_counts(self, rule: QualityRule, row: Any) -> QualityResult:
        total_records = int(row.get("total_records") or 0)
        failed_records = int(row.get("failed_records") or 0)
        if total_records < 0 or failed_records < 0 or failed_records > total_records:
            raise ValueError("Quality aggregate returned invalid record counts")
        passed_records = total_records - failed_records
        failure_percentage = round(
            failed_records / total_records * 100,
            2,
        ) if total_records else 0.0
        return QualityResult(
            rule_type=rule.rule_type,
            column=rule.column,
            rule_config=rule.model_dump(exclude={"rule_type", "column"}),
            total_records=total_records,
            passed_records=passed_records,
            failed_records=failed_records,
            failure_percentage=failure_percentage,
            status="FAIL" if failed_records else "PASS",
        )

    def _error_result(self, rule: QualityRule, exc: Exception) -> QualityResult:
        return QualityResult(
            rule_type=rule.rule_type,
            column=rule.column,
            rule_config=rule.model_dump(exclude={"rule_type", "column"}),
            status="ERROR",
            error_message=str(exc),
        )

    def _canonical_source_type(self, source_type: str) -> str:
        normalized = source_type.strip().lower()
        return {
            "mssql": "sqlserver",
            "sql_server": "sqlserver",
            "postgres": "postgresql",
        }.get(normalized, normalized)


__all__ = ["FAILURE_DETAIL_LIMIT", "QualityReport", "QualityResult", "QualityRuleEngine"]
