from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
import unittest

from sqlalchemy import Column, DateTime, Integer, MetaData, Numeric, String, Table, create_engine, insert, literal, select
from sqlalchemy.pool import StaticPool

from metadata.models import ColumnMetadata, TableMetadata
from quality.dialects.snowflake import SnowflakeQualityDialect
from quality.rule_engine import QualityRuleEngine
from quality.rule_models import (
    AcceptedValuesRule,
    DuplicateRule,
    FreshnessRule,
    NotNullRule,
    NumericRangeRule,
    StringLengthRule,
    UniqueRule,
)


class TestQualityRuleEngine(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        metadata = MetaData()
        self.table = Table(
            "quality_rows",
            metadata,
            Column("id", Integer),
            Column("email", String),
            Column("status", String),
            Column("amount", Numeric(10, 2)),
            Column("name", String),
            Column("updated_at", DateTime),
        )
        metadata.create_all(self.engine)
        now = datetime.now()
        with self.engine.begin() as connection:
            connection.execute(
                insert(self.table),
                [
                    {"id": 1, "email": "A", "status": "ACTIVE", "amount": Decimal("10"), "name": "abc", "updated_at": now},
                    {"id": 1, "email": "A", "status": "ACTIVE", "amount": Decimal("20"), "name": "abcdef", "updated_at": now - timedelta(days=2)},
                    {"id": 2, "email": "B", "status": "UNKNOWN", "amount": Decimal("100"), "name": "abcdefghij", "updated_at": now - timedelta(days=10)},
                    {"id": 3, "email": None, "status": None, "amount": None, "name": None, "updated_at": None},
                    {"id": 4, "email": "C", "status": "INACTIVE", "amount": Decimal("30"), "name": "abcd", "updated_at": now + timedelta(days=1)},
                    {"id": 5, "email": "C", "status": "ACTIVE", "amount": Decimal("40"), "name": "abcde", "updated_at": now},
                    {"id": 6, "email": "C", "status": "ACTIVE", "amount": Decimal("50"), "name": "abcdefghi", "updated_at": now},
                ],
            )

        self.connector = type("Connector", (), {"engine": self.engine})()
        self.table_metadata = TableMetadata(
            source_type="postgresql",
            database_name="quality_db",
            schema_name="",
            table_name="quality_rows",
            columns=[
                ColumnMetadata(column_name="id", source_data_type="INTEGER", normalized_data_type="NUMBER", nullable=True, ordinal_position=1),
                ColumnMetadata(column_name="email", source_data_type="VARCHAR", normalized_data_type="STRING", nullable=True, ordinal_position=2),
                ColumnMetadata(column_name="status", source_data_type="VARCHAR", normalized_data_type="STRING", nullable=True, ordinal_position=3),
                ColumnMetadata(column_name="amount", source_data_type="NUMERIC", normalized_data_type="DECIMAL", nullable=True, ordinal_position=4),
                ColumnMetadata(column_name="name", source_data_type="VARCHAR", normalized_data_type="STRING", nullable=True, ordinal_position=5),
                ColumnMetadata(column_name="updated_at", source_data_type="TIMESTAMP", normalized_data_type="DATETIME", nullable=True, ordinal_position=6),
            ],
        )
        self.engine_under_test = QualityRuleEngine()

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_not_null_result_and_invariants(self) -> None:
        result = self.engine_under_test.execute_rule(
            self.connector, self.table_metadata, NotNullRule(column="email")
        )

        self.assertEqual(result.total_records, 7)
        self.assertEqual(result.failed_records, 1)
        self.assertEqual(result.passed_records, 6)
        self.assertEqual(result.failure_percentage, 14.29)
        self.assertEqual(result.status, "FAIL")
        self.assertEqual(result.passed_records + result.failed_records, result.total_records)

    def test_duplicate_and_unique_count_duplicate_group_records(self) -> None:
        for rule_type in (DuplicateRule, UniqueRule):
            with self.subTest(rule_type=rule_type.__name__):
                result = self.engine_under_test.execute_rule(
                    self.connector, self.table_metadata, rule_type(column="email")
                )
                self.assertEqual(result.total_records, 7)
                self.assertEqual(result.failed_records, 5)
                self.assertEqual(result.passed_records, 2)
                self.assertEqual(result.status, "FAIL")

    def test_accepted_values_ignores_null(self) -> None:
        result = self.engine_under_test.execute_rule(
            self.connector,
            self.table_metadata,
            AcceptedValuesRule(column="status", accepted_values=["ACTIVE", "INACTIVE"]),
        )

        self.assertEqual(result.total_records, 7)
        self.assertEqual(result.failed_records, 1)
        self.assertEqual(result.passed_records, 6)

    def test_failed_records_are_complete_and_match_rule_counts(self) -> None:
        cases = [
            (NotNullRule(column="email"), 1),
            (UniqueRule(column="email"), 5),
            (AcceptedValuesRule(column="status", accepted_values=["ACTIVE", "INACTIVE"]), 1),
            (NumericRangeRule(column="amount", min_value=10, max_value=50), 1),
            (StringLengthRule(column="name", min_length=3, max_length=8), 2),
        ]
        for rule, expected_count in cases:
            with self.subTest(rule=rule.rule_type):
                result = self.engine_under_test.execute_rule(self.connector, self.table_metadata, rule)
                records = self.engine_under_test.inspect_failed_records(
                    self.connector, self.table_metadata, rule, limit=None
                )
                self.assertEqual(result.failed_records, expected_count)
                self.assertEqual(len(records), result.failed_records)
                self.assertEqual(list(records[0]), [column.column_name for column in self.table_metadata.columns])

        null_record = self.engine_under_test.inspect_failed_records(
            self.connector, self.table_metadata, NotNullRule(column="email"), limit=None
        )[0]
        self.assertIsNone(null_record["email"])

    def test_failed_record_view_limit_does_not_change_complete_result(self) -> None:
        rule = UniqueRule(column="email")
        visible = self.engine_under_test.inspect_failed_records(
            self.connector, self.table_metadata, rule, limit=2
        )
        complete = self.engine_under_test.inspect_failed_records(
            self.connector, self.table_metadata, rule, limit=None
        )
        self.assertEqual(len(visible), 2)
        self.assertEqual(len(complete), 5)

    def test_all_failed_records_are_unique_with_combined_reasons(self) -> None:
        report = self.engine_under_test.execute_rules(
            self.connector,
            self.table_metadata,
            [
                UniqueRule(column="email"),
                AcceptedValuesRule(column="status", accepted_values=["ACTIVE", "INACTIVE"]),
                NumericRangeRule(column="amount", min_value=10, max_value=50),
                StringLengthRule(column="name", min_length=3, max_length=8),
            ],
        )
        records = self.engine_under_test.inspect_all_failed_records(
            self.connector, self.table_metadata, report.results
        )

        self.assertEqual(len(records), 5)
        self.assertEqual(
            list(records[0]),
            [column.column_name for column in self.table_metadata.columns] + ["Failed Reason"],
        )
        row_with_multiple_failures = next(record for record in records if record["id"] == 2)
        self.assertIn("email: Unique", row_with_multiple_failures["Failed Reason"])
        self.assertIn("status: Accepted Values", row_with_multiple_failures["Failed Reason"])
        self.assertIn("amount: Numeric Range", row_with_multiple_failures["Failed Reason"])
        self.assertIn("name: String Length", row_with_multiple_failures["Failed Reason"])

    def test_numeric_range_is_inclusive_and_ignores_null(self) -> None:
        result = self.engine_under_test.execute_rule(
            self.connector,
            self.table_metadata,
            NumericRangeRule(column="amount", min_value=10, max_value=50),
        )

        self.assertEqual(result.total_records, 7)
        self.assertEqual(result.failed_records, 1)
        self.assertEqual(result.passed_records, 6)

    def test_string_length_is_inclusive_and_ignores_null(self) -> None:
        result = self.engine_under_test.execute_rule(
            self.connector,
            self.table_metadata,
            StringLengthRule(column="name", min_length=3, max_length=8),
        )

        self.assertEqual(result.total_records, 7)
        self.assertEqual(result.failed_records, 2)
        self.assertEqual(result.passed_records, 5)

    def test_execute_rules_calculates_weighted_score(self) -> None:
        report = self.engine_under_test.execute_rules(
            self.connector,
            self.table_metadata,
            [
                NotNullRule(column="email"),
                AcceptedValuesRule(column="status", accepted_values=["ACTIVE", "INACTIVE"]),
            ],
        )

        self.assertEqual(report.total_rules, 2)
        self.assertEqual(report.passed_rules, 0)
        self.assertEqual(report.failed_rules, 2)
        self.assertEqual(report.error_rules, 0)
        self.assertEqual(report.quality_score, 85.71)

    def test_quality_score_uses_record_weighted_formula(self) -> None:
        class FixedCountsDialect:
            def build_check_statement(self, engine, table_metadata, rule):
                failed = 10 if rule.column == "first" else 20
                return select(
                    literal(100).label("total_records"),
                    literal(failed).label("failed_records"),
                )

        score_engine = QualityRuleEngine({"postgresql": FixedCountsDialect()})
        score_metadata = self.table_metadata.model_copy(
            update={
                "columns": [
                    ColumnMetadata(column_name="first", source_data_type="INTEGER", normalized_data_type="NUMBER", nullable=True, ordinal_position=1),
                    ColumnMetadata(column_name="second", source_data_type="INTEGER", normalized_data_type="NUMBER", nullable=True, ordinal_position=2),
                ]
            }
        )
        report = score_engine.execute_rules(
            self.connector,
            score_metadata,
            [NotNullRule(column="first"), NotNullRule(column="second")],
        )

        self.assertEqual(report.quality_score, 85.0)

    def test_invalid_column_and_incompatible_type_are_rejected_before_execution(self) -> None:
        with self.assertRaises(ValueError):
            self.engine_under_test.execute_rule(
                self.connector, self.table_metadata, NotNullRule(column="missing")
            )
        with self.assertRaises(ValueError):
            self.engine_under_test.execute_rule(
                self.connector, self.table_metadata, NumericRangeRule(column="name", min_value=0)
            )

    def test_database_error_becomes_error_result_and_does_not_improve_score(self) -> None:
        broken_engine = create_engine("sqlite+pysqlite://")
        broken_connector = type("Connector", (), {"engine": broken_engine})()
        result = self.engine_under_test.execute_rule(
            broken_connector, self.table_metadata, NotNullRule(column="email")
        )
        broken_engine.dispose()
        self.assertEqual(result.status, "ERROR")
        self.assertEqual(result.total_records, 0)
        self.assertIsNotNone(result.error_message)

    def test_malformed_aggregate_counts_become_error_result(self) -> None:
        class BadConnection:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return None

            def execute(self, statement, parameters):
                return type("Result", (), {"mappings": lambda self: self, "one": lambda self: {"total_records": 1, "failed_records": 2}})()

        class BadEngine:
            def connect(self):
                return BadConnection()

        bad_connector = type("Connector", (), {"engine": BadEngine()})()
        result = self.engine_under_test.execute_rule(
            bad_connector, self.table_metadata, NotNullRule(column="email")
        )

        self.assertEqual(result.status, "ERROR")
        self.assertIsNotNone(result.error_message)

    def test_registered_dialect_and_unknown_source(self) -> None:
        class FakeDialect:
            def build_check_statement(self, engine, table_metadata, rule):
                return None

        self.engine_under_test.register_dialect("snowflake", FakeDialect())
        snowflake_metadata = self.table_metadata.model_copy(update={"source_type": "snowflake"})
        self.assertIsInstance(self.engine_under_test._dialect_for("snowflake"), FakeDialect)
        with self.assertRaises(ValueError):
            self.engine_under_test.execute_rule(
                self.connector,
                self.table_metadata.model_copy(update={"source_type": "oracle"}),
                NotNullRule(column="email"),
            )

    def test_snowflake_dialect_is_registered_by_default(self) -> None:
        self.assertIsInstance(self.engine_under_test._dialect_for("snowflake"), SnowflakeQualityDialect)

    def test_empty_table_success_has_zero_counts_and_no_score(self) -> None:
        with self.engine.begin() as connection:
            connection.execute(self.table.delete())
        result = self.engine_under_test.execute_rule(
            self.connector, self.table_metadata, NotNullRule(column="email")
        )
        report = self.engine_under_test.execute_rules(
            self.connector, self.table_metadata, [NotNullRule(column="email")]
        )

        self.assertEqual(result.total_records, 0)
        self.assertEqual(result.passed_records, 0)
        self.assertEqual(result.failed_records, 0)
        self.assertEqual(result.failure_percentage, 0.0)
        self.assertEqual(result.status, "PASS")
        self.assertIsNone(report.quality_score)

    def test_zero_rules_and_json_serialization(self) -> None:
        report = self.engine_under_test.execute_rules(self.connector, self.table_metadata, [])
        self.assertEqual(report.total_rules, 0)
        self.assertIsNone(report.quality_score)
        self.assertIn('"quality_score":null', report.model_dump_json())
