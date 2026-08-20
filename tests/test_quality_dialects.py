from __future__ import annotations

import unittest

from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, create_engine
from sqlalchemy.dialects import mssql, postgresql

from metadata.models import ColumnMetadata, TableMetadata
from quality.dialects.postgres import PostgresQualityDialect
from quality.dialects.sqlserver import SQLServerQualityDialect
from quality.rule_models import (
    AcceptedValuesRule,
    FreshnessRule,
    NotNullRule,
    NumericRangeRule,
    StringLengthRule,
)


class TestQualityDialects(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite+pysqlite://")
        metadata = MetaData()
        Table(
            "quality_rows",
            metadata,
            Column("id", Integer),
            Column("status", String),
            Column("updated_at", DateTime),
        )
        metadata.create_all(self.engine)
        self.table_metadata = TableMetadata(
            source_type="postgresql",
            database_name="db",
            schema_name="",
            table_name="quality_rows",
            columns=[
                ColumnMetadata(column_name="id", source_data_type="INTEGER", normalized_data_type="NUMBER", nullable=True, ordinal_position=1),
                ColumnMetadata(column_name="status", source_data_type="VARCHAR", normalized_data_type="STRING", nullable=True, ordinal_position=2),
                ColumnMetadata(column_name="updated_at", source_data_type="TIMESTAMP", normalized_data_type="DATETIME", nullable=True, ordinal_position=3),
            ],
        )

    def tearDown(self) -> None:
        self.engine.dispose()

    def test_sqlserver_functions_and_bound_parameters(self) -> None:
        dialect = SQLServerQualityDialect()
        for rule in (
            NotNullRule(column="status"),
            AcceptedValuesRule(column="status", accepted_values=["O'Reilly"]),
            NumericRangeRule(column="id", min_value=1, max_value=10),
            StringLengthRule(column="status", max_length=10),
            FreshnessRule(column="updated_at", max_age_days=30),
        ):
            statement = dialect.build_check_statement(self.engine, self.table_metadata, rule)
            compiled = str(statement.compile(dialect=mssql.dialect()))
            self.assertIn("total_records", compiled)
            self.assertIn("failed_records", compiled)
        accepted = dialect.build_check_statement(
            self.engine,
            self.table_metadata,
            AcceptedValuesRule(column="status", accepted_values=["O'Reilly"]),
        )
        self.assertIn("accepted_values", accepted.compile().params)
        self.assertNotIn("O'Reilly", str(accepted))

    def test_postgres_functions_and_bound_parameters(self) -> None:
        dialect = PostgresQualityDialect()
        for rule in (
            NotNullRule(column="status"),
            AcceptedValuesRule(column="status", accepted_values=["O'Reilly"]),
            NumericRangeRule(column="id", min_value=1, max_value=10),
            StringLengthRule(column="status", max_length=10),
            FreshnessRule(column="updated_at", max_age_days=30),
        ):
            statement = dialect.build_check_statement(self.engine, self.table_metadata, rule)
            compiled = str(statement.compile(dialect=postgresql.dialect()))
            self.assertIn("total_records", compiled)
            self.assertIn("failed_records", compiled)
        freshness = dialect.build_check_statement(
            self.engine,
            self.table_metadata,
            FreshnessRule(column="updated_at", max_age_days=30),
        )
        self.assertIn("max_age_days", freshness.compile().params)
        self.assertEqual(freshness.compile().params["max_age_days"], 30)
