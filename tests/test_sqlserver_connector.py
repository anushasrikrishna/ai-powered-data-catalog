from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy.engine import URL

from connectors.exceptions import ConnectionFailedError, SchemaNotFoundError, TableNotFoundError
from connectors.sqlserver_connector import SQLServerConnector


class TestSQLServerConnectorUnit(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = MagicMock()
        self.connector = SQLServerConnector(
            host="localhost",
            port=1433,
            database="catalog_demo",
            username="user",
            password="pass",
            driver="ODBC Driver 18 for SQL Server",
            engine=self.engine,
        )

    def test_build_url_uses_sqlalchemy_url_create(self) -> None:
        url = self.connector._build_url()
        self.assertIsInstance(url, URL)
        self.assertEqual(url.drivername, "mssql+pyodbc")
        self.assertEqual(url.host, "localhost")
        self.assertEqual(url.port, 1433)
        self.assertEqual(url.database, "catalog_demo")
        self.assertEqual(url.query.get("driver"), "ODBC Driver 18 for SQL Server")

    def test_test_connection_returns_true(self) -> None:
        connection = MagicMock()
        self.engine.connect.return_value.__enter__.return_value = connection

        self.assertTrue(self.connector.test_connection())
        connection.execute.assert_called_once()

    def test_test_connection_translates_errors(self) -> None:
        self.engine.connect.side_effect = Exception("login failed")

        with self.assertRaises(ConnectionFailedError):
            self.connector.test_connection()

    @patch("connectors.sqlserver_connector.inspect")
    def test_list_tables_invalid_schema_raises(self, mock_inspect: MagicMock) -> None:
        inspector = MagicMock()
        inspector.get_table_names.return_value = ["customers"]
        mock_inspect.return_value = inspector

        self.connector.list_schemas = MagicMock(return_value=["dbo"])
        with self.assertRaises(SchemaNotFoundError):
            self.connector.list_tables("sales")

    @patch("connectors.sqlserver_connector.inspect")
    def test_get_columns_returns_dict_structure(self, mock_inspect: MagicMock) -> None:
        inspector = MagicMock()
        inspector.get_columns.return_value = [
            {
                "name": "CUSTOMER_ID",
                "type": "INT",
                "nullable": False,
                "ordinal_position": 1,
            },
            {
                "name": "EMAIL",
                "type": "VARCHAR",
                "nullable": True,
                "ordinal_position": 2,
            },
        ]
        mock_inspect.return_value = inspector
        self.connector.list_schemas = MagicMock(return_value=["dbo"])
        self.connector.list_tables = MagicMock(return_value=["CUSTOMERS"])

        columns = self.connector.get_columns("dbo", "CUSTOMERS")

        self.assertEqual(len(columns), 2)
        self.assertTrue(all(isinstance(col, dict) for col in columns))
        self.assertEqual(columns[0]["name"], "CUSTOMER_ID")
        self.assertEqual(columns[0]["data_type"], "INT")
        self.assertFalse(columns[0]["nullable"])
        self.assertEqual(columns[0]["ordinal_position"], 1)
        self.assertEqual(
            set(columns[0].keys()),
            {"name", "data_type", "nullable", "ordinal_position"},
        )

    @patch("connectors.sqlserver_connector.Table")
    @patch("connectors.sqlserver_connector.select")
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
            {"CUSTOMER_ID": 1, "NAME": "Alice"},
            {"CUSTOMER_ID": 2, "NAME": "Bob"},
        ]
        connection.execute.return_value = result
        self.engine.connect.return_value.__enter__.return_value = connection

        self.connector.list_schemas = MagicMock(return_value=["dbo"])
        self.connector.list_tables = MagicMock(return_value=["CUSTOMERS"])

        rows = self.connector.get_sample_rows("dbo", "CUSTOMERS", limit=2)

        self.assertEqual(
            rows,
            [
                {"CUSTOMER_ID": 1, "NAME": "Alice"},
                {"CUSTOMER_ID": 2, "NAME": "Bob"},
            ],
        )

    def test_get_sample_rows_invalid_table_raises(self) -> None:
        self.connector.list_schemas = MagicMock(return_value=["dbo"])
        self.connector.list_tables = MagicMock(return_value=["CUSTOMERS"])

        with self.assertRaises(TableNotFoundError):
            self.connector.get_sample_rows("dbo", "ORDERS")


@unittest.skipUnless(
    os.getenv("RUN_SQLSERVER_INTEGRATION_TESTS") == "1",
    "SQL Server integration tests are disabled. Set RUN_SQLSERVER_INTEGRATION_TESTS=1.",
)
class TestSQLServerConnectorIntegration(unittest.TestCase):
    def test_connection_smoke(self) -> None:
        connector = SQLServerConnector(
            host=os.environ["SQLSERVER_SERVER"],
            port=int(os.getenv("SQLSERVER_PORT", "1433")),
            database=os.environ["SQLSERVER_DATABASE"],
            username=os.environ["SQLSERVER_USERNAME"],
            password=os.environ["SQLSERVER_PASSWORD"],
            driver=os.getenv("SQLSERVER_DRIVER", "ODBC Driver 18 for SQL Server"),
        )
        self.assertTrue(connector.test_connection())

    def test_metadata_smoke(self) -> None:
        schema_name = os.getenv("SQLSERVER_TEST_SCHEMA")
        table_name = os.getenv("SQLSERVER_TEST_TABLE")
        if not schema_name or not table_name:
            self.skipTest(
                "Set SQLSERVER_TEST_SCHEMA and SQLSERVER_TEST_TABLE to run metadata smoke checks."
            )

        connector = SQLServerConnector(
            host=os.environ["SQLSERVER_SERVER"],
            port=int(os.getenv("SQLSERVER_PORT", "1433")),
            database=os.environ["SQLSERVER_DATABASE"],
            username=os.environ["SQLSERVER_USERNAME"],
            password=os.environ["SQLSERVER_PASSWORD"],
            driver=os.getenv("SQLSERVER_DRIVER", "ODBC Driver 18 for SQL Server"),
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
