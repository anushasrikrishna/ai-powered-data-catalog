from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy.engine import URL

from connectors.exceptions import ConnectionFailedError, SchemaNotFoundError, TableNotFoundError
from connectors.postgres_connector import PostgresConnector


class TestPostgresConnectorUnit(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = MagicMock()
        self.connector = PostgresConnector(
            host="localhost",
            port=5432,
            database="catalog_demo",
            username="user",
            password="pass",
            engine=self.engine,
        )

    def test_build_url_uses_sqlalchemy_url_create(self) -> None:
        url = self.connector._build_url()
        self.assertIsInstance(url, URL)
        self.assertEqual(url.drivername, "postgresql+psycopg")
        self.assertEqual(url.host, "localhost")
        self.assertEqual(url.port, 5432)
        self.assertEqual(url.database, "catalog_demo")

    def test_test_connection_returns_true(self) -> None:
        connection = MagicMock()
        self.engine.connect.return_value.__enter__.return_value = connection

        self.assertTrue(self.connector.test_connection())
        connection.execute.assert_called_once()

    def test_test_connection_translates_errors(self) -> None:
        self.engine.connect.side_effect = Exception("password authentication failed")

        with self.assertRaises(ConnectionFailedError):
            self.connector.test_connection()

    @patch("connectors.postgres_connector.inspect")
    def test_list_schemas_filters_system_schemas(self, mock_inspect: MagicMock) -> None:
        inspector = MagicMock()
        inspector.get_schema_names.return_value = [
            "public",
            "information_schema",
            "pg_catalog",
            "pg_toast",
            "sales",
        ]
        mock_inspect.return_value = inspector

        schemas = self.connector.list_schemas()

        self.assertEqual(schemas, ["public", "sales"])

    @patch("connectors.postgres_connector.inspect")
    def test_list_tables_invalid_schema_raises(self, mock_inspect: MagicMock) -> None:
        inspector = MagicMock()
        inspector.get_table_names.return_value = ["orders"]
        mock_inspect.return_value = inspector

        self.connector.list_schemas = MagicMock(return_value=["public"])
        with self.assertRaises(SchemaNotFoundError):
            self.connector.list_tables("finance")

    @patch("connectors.postgres_connector.inspect")
    def test_get_columns_returns_dict_structure(self, mock_inspect: MagicMock) -> None:
        inspector = MagicMock()
        inspector.get_columns.return_value = [
            {
                "name": "order_id",
                "type": "INTEGER",
                "nullable": False,
                "ordinal_position": 1,
            },
        ]
        mock_inspect.return_value = inspector
        self.connector.list_schemas = MagicMock(return_value=["public"])
        self.connector.list_tables = MagicMock(return_value=["orders"])

        columns = self.connector.get_columns("public", "orders")

        self.assertEqual(len(columns), 1)
        self.assertIsInstance(columns[0], dict)
        self.assertEqual(columns[0]["name"], "order_id")
        self.assertEqual(columns[0]["data_type"], "INTEGER")
        self.assertFalse(columns[0]["nullable"])
        self.assertEqual(columns[0]["ordinal_position"], 1)
        self.assertEqual(
            set(columns[0].keys()),
            {"name", "data_type", "nullable", "ordinal_position"},
        )

    @patch("connectors.postgres_connector.Table")
    @patch("connectors.postgres_connector.select")
    def test_get_sample_rows_returns_list_of_dicts(
        self,
        mock_select: MagicMock,
        mock_table: MagicMock,
    ) -> None:
        table_obj = MagicMock()
        statement = MagicMock()
        statement.limit.return_value = statement
        mock_table.return_value = table_obj
        mock_select.return_value = statement

        connection = MagicMock()
        result = MagicMock()
        result.mappings.return_value.all.return_value = [
            {"order_id": 1, "customer_id": 101},
            {"order_id": 2, "customer_id": 102},
        ]
        connection.execute.return_value = result
        self.engine.connect.return_value.__enter__.return_value = connection

        self.connector.list_schemas = MagicMock(return_value=["public"])
        self.connector.list_tables = MagicMock(return_value=["orders"])

        rows = self.connector.get_sample_rows("public", "orders", limit=2)

        self.assertEqual(
            rows,
            [
                {"order_id": 1, "customer_id": 101},
                {"order_id": 2, "customer_id": 102},
            ],
        )

    def test_get_sample_rows_invalid_table_raises(self) -> None:
        self.connector.list_schemas = MagicMock(return_value=["public"])
        self.connector.list_tables = MagicMock(return_value=["orders"])

        with self.assertRaises(TableNotFoundError):
            self.connector.get_sample_rows("public", "missing")


@unittest.skipUnless(
    os.getenv("RUN_POSTGRES_INTEGRATION_TESTS") == "1",
    "PostgreSQL integration tests are disabled. Set RUN_POSTGRES_INTEGRATION_TESTS=1.",
)
class TestPostgresConnectorIntegration(unittest.TestCase):
    def test_connection_smoke(self) -> None:
        connector = PostgresConnector(
            host=os.environ["POSTGRES_HOST"],
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.environ["POSTGRES_DATABASE"],
            username=os.environ["POSTGRES_USERNAME"],
            password=os.environ["POSTGRES_PASSWORD"],
        )
        self.assertTrue(connector.test_connection())

    def test_metadata_smoke(self) -> None:
        schema_name = os.getenv("POSTGRES_TEST_SCHEMA")
        table_name = os.getenv("POSTGRES_TEST_TABLE")
        if not schema_name or not table_name:
            self.skipTest(
                "Set POSTGRES_TEST_SCHEMA and POSTGRES_TEST_TABLE to run metadata smoke checks."
            )

        connector = PostgresConnector(
            host=os.environ["POSTGRES_HOST"],
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            database=os.environ["POSTGRES_DATABASE"],
            username=os.environ["POSTGRES_USERNAME"],
            password=os.environ["POSTGRES_PASSWORD"],
        )

        databases = connector.list_databases()
        schemas = connector.list_schemas()
        tables = connector.list_tables(schema_name)
        columns = connector.get_columns(schema_name, table_name)
        rows = connector.get_sample_rows(schema_name, table_name, limit=2)

        self.assertIsInstance(databases, list)
        self.assertTrue(all(isinstance(name, str) for name in databases))
        self.assertIsInstance(schemas, list)
        self.assertTrue(all(isinstance(name, str) for name in schemas))
        self.assertIsInstance(tables, list)
        self.assertTrue(all(isinstance(name, str) for name in tables))
        self.assertIsInstance(columns, list)
        if columns:
            self.assertIsInstance(columns[0], dict)
            self.assertEqual(
                set(columns[0].keys()),
                {"name", "data_type", "nullable", "ordinal_position"},
            )
        self.assertIsInstance(rows, list)
        if rows:
            self.assertIsInstance(rows[0], dict)
