from __future__ import annotations

from pathlib import Path
import inspect
import re
from tempfile import TemporaryDirectory
import unittest

from sqlalchemy import Column, Integer, MetaData, String, Table, create_engine, insert
from sqlalchemy.dialects import mssql, postgresql
from snowflake.sqlalchemy import dialect as snowflake_dialect

from metadata.models import ColumnMetadata, TableMetadata
from quality.rule_engine import QualityReport, QualityRuleEngine, QualityResult
from quality.dialects.postgres import PostgresQualityDialect
from quality.dialects.snowflake import SnowflakeQualityDialect
from quality.dialects.sqlserver import SQLServerQualityDialect
from quality.rule_models import AcceptedValuesRule
from storage.quality_repository import QualityRunRepository
from ui import quality_trend
from ui.quality_trend import build_quality_trend_svg


class TestQualityReviewFoundations(unittest.TestCase):
    def test_trend_svg_is_dependency_free_and_clamps_score_coordinates(self) -> None:
        svg = build_quality_trend_svg([("older", -10), ("middle", 94.3), ("newer", 125)])
        self.assertIsNotNone(svg)
        self.assertNotIn("numpy", inspect.getsource(quality_trend).casefold())
        self.assertNotIn("pandas", inspect.getsource(quality_trend).casefold())
        coordinates = [float(value) for value in re.findall(r'cy="([0-9.]+)"', svg)]
        self.assertEqual(len(coordinates), 3)
        self.assertTrue(all(18.0 <= value <= 182.0 for value in coordinates))
        self.assertIsNone(build_quality_trend_svg([("only", 94.3)]))

    def test_all_quality_dialects_build_bounded_failure_detail(self) -> None:
        engine = create_engine("sqlite+pysqlite://")
        metadata = MetaData()
        table = Table("review_values", metadata, Column("value", String))
        metadata.create_all(engine)
        table_metadata = TableMetadata(
            source_type="postgresql",
            database_name="review",
            schema_name="main",
            table_name="review_values",
            columns=[
                ColumnMetadata(
                    column_name="value",
                    source_data_type="TEXT",
                    normalized_data_type="STRING",
                    nullable=True,
                    ordinal_position=1,
                )
            ],
        )
        rule = AcceptedValuesRule(column="value", accepted_values=["VALID"])
        cases = (
            (SQLServerQualityDialect(), mssql.dialect()),
            (PostgresQualityDialect(), postgresql.dialect()),
            (SnowflakeQualityDialect(), snowflake_dialect()),
        )
        for dialect, compiler in cases:
            statement = dialect.build_failure_detail_statement(engine, table_metadata, rule, 10)
            self.assertIsNotNone(statement)
            self.assertIn("failed_value", str(statement.compile(dialect=compiler)))

    def test_bounded_failure_values_are_grouped_and_limited(self) -> None:
        engine = create_engine("sqlite+pysqlite://")
        metadata = MetaData()
        table = Table("review_values", metadata, Column("value", String), Column("id", Integer))
        metadata.create_all(engine)
        with engine.begin() as connection:
            connection.execute(
                insert(table),
                [{"value": f"INVALID_{index}", "id": index} for index in range(25)]
                + [{"value": "INVALID_0", "id": 100}],
            )
        table_metadata = TableMetadata(
            source_type="postgresql",
            database_name="review",
            schema_name="main",
            table_name="review_values",
            columns=[
                ColumnMetadata(
                    column_name="value",
                    source_data_type="TEXT",
                    normalized_data_type="STRING",
                    nullable=True,
                    ordinal_position=1,
                )
            ],
        )
        connector = type("Connector", (), {"engine": engine})()
        details = QualityRuleEngine().inspect_failed_values(
            connector,
            table_metadata,
            AcceptedValuesRule(column="value", accepted_values=["VALID"]),
            limit=10,
        )
        self.assertEqual(len(details), 10)
        self.assertEqual(details[0], {"failed_value": "INVALID_0", "failure_count": 2})

    def test_quality_run_history_is_transactional_and_dataset_scoped(self) -> None:
        report = QualityReport(
            source_type="sqlserver",
            database_name="quality_db",
            schema_name="dbo",
            table_name="orders",
            total_rules=1,
            passed_rules=0,
            failed_rules=1,
            error_rules=0,
            quality_score=80.0,
            results=[
                QualityResult(
                    rule_type="accepted_values",
                    column="status",
                    rule_config={"accepted_values": ["OPEN", "CLOSED"]},
                    total_records=10,
                    passed_records=8,
                    failed_records=2,
                    failure_percentage=20.0,
                    status="FAIL",
                    error_message=None,
                )
            ],
        )
        with TemporaryDirectory() as directory:
            repository = QualityRunRepository(Path(directory) / "history.db")
            saved = repository.save_quality_run("run-1", report, "2026-08-25T00:00:00+00:00")
            loaded = repository.get_quality_run(saved.run_id)
            listed = repository.list_quality_runs_for_dataset("sqlserver", "quality_db", "dbo", "orders")
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.report.quality_score, 80.0)
            self.assertEqual(loaded.report.results[0].failed_records, 2)
            self.assertEqual([item.run_id for item in listed], ["run-1"])
            self.assertEqual(repository.list_quality_runs_for_dataset("snowflake", "quality_db", "dbo", "orders"), [])

    def test_history_is_newest_first_for_table_and_oldest_first_for_trend_input(self) -> None:
        def report(score: float) -> QualityReport:
            return QualityReport(
                source_type="sqlserver",
                database_name="quality_db",
                schema_name="dbo",
                table_name="orders",
                total_rules=1,
                passed_rules=1,
                failed_rules=0,
                error_rules=0,
                quality_score=score,
                results=[],
            )

        with TemporaryDirectory() as directory:
            repository = QualityRunRepository(Path(directory) / "history.db")
            for index, score in enumerate((91.2, 94.3, 96.1), start=1):
                repository.save_quality_run(f"run-{index}", report(score), f"2026-08-25T00:0{index}:00+00:00")
            runs = repository.list_quality_runs_for_dataset("sqlserver", "quality_db", "dbo", "orders")
            self.assertEqual([run.run_id for run in runs], ["run-3", "run-2", "run-1"])
            self.assertEqual([run.report.quality_score for run in reversed(runs)], [91.2, 94.3, 96.1])

    def test_latest_run_for_user_is_timestamp_ordered_and_isolated(self) -> None:
        def report(score: float) -> QualityReport:
            return QualityReport(
                source_type="sqlserver", database_name="quality_db", schema_name="dbo", table_name="orders",
                total_rules=1, passed_rules=1, failed_rules=0, error_rules=0, quality_score=score, results=[],
            )

        with TemporaryDirectory() as directory:
            repository = QualityRunRepository(Path(directory) / "history.db")
            repository.save_quality_run("run-old", report(90.0), "2026-08-25T00:00:00+00:00", user_id="user-a")
            repository.save_quality_run("run-new", report(96.0), "2026-08-26T00:00:00+00:00", user_id="user-a")
            repository.save_quality_run("run-b", report(83.0), "2026-08-27T00:00:00+00:00", user_id="user-b")
            latest_a = repository.get_latest_run_for_user("user-a")
            latest_b = repository.get_latest_run_for_user("user-b")
            self.assertEqual(latest_a.run_id, "run-new")
            self.assertEqual(latest_a.report.quality_score, 96.0)
            self.assertEqual(latest_b.run_id, "run-b")


if __name__ == "__main__":
    unittest.main()
