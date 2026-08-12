from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from connectors.exceptions import (
    ConnectionFailedError,
    DatabaseNotFoundError,
    SchemaNotFoundError,
    TableNotFoundError,
)
from connectors.snowflake_connector import SnowflakeConnector


class TestSnowflakeConnectorUnit(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = MagicMock()
        self.connector = SnowflakeConnector(
            account="account.example",
            username="user",
            password="secret",
            warehouse="COMPUTE_WH",
            database="CATALOG",
            schema="PUBLIC",
            role="ANALYST",
            engine=self.engine,
        )

    def _result(self, rows: list[dict[str, object]]) -> MagicMock:
        result = MagicMock()
        result.mappings.return_value.all.return_value = rows
        return result

    def test_connector_implements_base_contract(self) -> None:
        self.assertIsInstance(self.connector, SnowflakeConnector)
        self.assertTrue(hasattr(self.connector, "test_connection"))
        self.assertTrue(hasattr(self.connector, "list_databases"))
        self.assertTrue(hasattr(self.connector, "list_schemas"))
        self.assertTrue(hasattr(self.connector, "list_tables"))
        self.assertTrue(hasattr(self.connector, "get_columns"))
        self.assertTrue(hasattr(self.connector, "get_sample_rows"))

    def test_test_connection_returns_true(self) -> None:
        connection = MagicMock()
        self.engine.connect.return_value.__enter__.return_value = connection
        self.assertTrue(self.connector.test_connection())
        connection.execute.assert_called_once()

    def test_test_connection_translates_errors_without_password(self) -> None:
        self.engine.connect.side_effect = Exception("authentication failed for secret")
        with self.assertRaises(ConnectionFailedError) as raised:
            self.connector.test_connection()
        self.assertNotIn("secret", str(raised.exception))

    def test_list_databases_returns_sorted_names(self) -> None:
        self.engine.connect.return_value.__enter__.return_value.execute.return_value = self._result(
            [{"name": "ZETA"}, {"name": "ALPHA"}]
        )
        self.assertEqual(self.connector.list_databases(), ["ALPHA", "ZETA"])

    def test_list_schemas_filters_information_schema(self) -> None:
        connection = self.engine.connect.return_value.__enter__.return_value
        connection.execute.side_effect = [
            self._result([{"name": "CATALOG"}]),
            self._result([{"schema_name": "PUBLIC"}, {"schema_name": "ANALYTICS"}]),
        ]
        self.assertEqual(self.connector.list_schemas(), ["ANALYTICS", "PUBLIC"])
        self.assertEqual(self.connector.active_database, "CATALOG")

    def test_default_database_remains_active_initially(self) -> None:
        self.assertEqual(self.connector.database, "CATALOG")
        self.assertEqual(self.connector.active_database, "CATALOG")

    def test_explicit_schema_database_switches_active_context(self) -> None:
        connection = self.engine.connect.return_value.__enter__.return_value
        connection.execute.side_effect = [
            self._result([{"name": "DATABASE_B"}]),
            self._result([{"schema_name": "PUBLIC"}]),
        ]

        self.assertEqual(self.connector.list_schemas("DATABASE_B"), ["PUBLIC"])
        self.assertEqual(self.connector.active_database, "DATABASE_B")

    def test_invalid_database_raises(self) -> None:
        connection = self.engine.connect.return_value.__enter__.return_value
        connection.execute.return_value = self._result([{"name": "CATALOG"}])
        with self.assertRaises(DatabaseNotFoundError):
            self.connector.list_schemas("MISSING")
        self.assertEqual(self.connector.active_database, "CATALOG")

    def test_list_tables_validates_schema_and_sorts(self) -> None:
        self.connector.list_schemas = MagicMock(return_value=["PUBLIC"])
        connection = self.engine.connect.return_value.__enter__.return_value
        connection.execute.return_value = self._result(
            [{"table_name": "Z_TABLE"}, {"table_name": "A_TABLE"}]
        )
        self.assertEqual(self.connector.list_tables("PUBLIC"), ["A_TABLE", "Z_TABLE"])

    def test_list_tables_uses_selected_database(self) -> None:
        self.connector.active_database = "DATABASE_B"
        self.connector.list_schemas = MagicMock(return_value=["PUBLIC"])
        connection = self.engine.connect.return_value.__enter__.return_value
        connection.execute.return_value = self._result([{"table_name": "CUSTOMERS"}])

        self.connector.list_tables("PUBLIC")

        executed_query = str(connection.execute.call_args.args[0])
        self.assertIn('"DATABASE_B".INFORMATION_SCHEMA.TABLES', executed_query)

    def test_invalid_schema_raises(self) -> None:
        self.connector.list_schemas = MagicMock(return_value=["PUBLIC"])
        with self.assertRaises(SchemaNotFoundError):
            self.connector.list_tables("MISSING")

    def test_get_columns_returns_common_shape(self) -> None:
        self.connector.list_schemas = MagicMock(return_value=["PUBLIC"])
        self.connector.list_tables = MagicMock(return_value=["CUSTOMERS"])
        connection = self.engine.connect.return_value.__enter__.return_value
        connection.execute.return_value = self._result(
            [{
                "column_name": "ID",
                "data_type": "NUMBER",
                "is_nullable": "NO",
                "ordinal_position": 1,
            }]
        )
        self.assertEqual(
            self.connector.get_columns("PUBLIC", "CUSTOMERS"),
            [{"name": "ID", "data_type": "NUMBER", "nullable": False, "ordinal_position": 1}],
        )

    def test_get_columns_uses_selected_database(self) -> None:
        self.connector.active_database = "DATABASE_B"
        self.connector.list_schemas = MagicMock(return_value=["PUBLIC"])
        self.connector.list_tables = MagicMock(return_value=["CUSTOMERS"])
        connection = self.engine.connect.return_value.__enter__.return_value
        connection.execute.return_value = self._result([])

        self.connector.get_columns("PUBLIC", "CUSTOMERS")

        executed_query = str(connection.execute.call_args.args[0])
        self.assertIn('"DATABASE_B".INFORMATION_SCHEMA.COLUMNS', executed_query)

    def test_invalid_table_raises(self) -> None:
        self.connector.list_schemas = MagicMock(return_value=["PUBLIC"])
        self.connector.list_tables = MagicMock(return_value=["CUSTOMERS"])
        with self.assertRaises(TableNotFoundError):
            self.connector.get_columns("PUBLIC", "MISSING")

    def test_get_sample_rows_uses_minimum_limit(self) -> None:
        self.connector.list_schemas = MagicMock(return_value=["PUBLIC"])
        self.connector.list_tables = MagicMock(return_value=["CUSTOMERS"])
        connection = self.engine.connect.return_value.__enter__.return_value
        connection.execute.return_value.mappings.return_value.all.return_value = [{"ID": 1}]
        self.assertEqual(self.connector.get_sample_rows("PUBLIC", "CUSTOMERS", limit=0), [{"ID": 1}])
        self.assertEqual(connection.execute.call_args.args[1], {"row_limit": 1})

    def test_get_sample_rows_uses_selected_database(self) -> None:
        self.connector.active_database = "DATABASE_B"
        self.connector.list_schemas = MagicMock(return_value=["PUBLIC"])
        self.connector.list_tables = MagicMock(return_value=["CUSTOMERS"])
        connection = self.engine.connect.return_value.__enter__.return_value
        result = self._result([])
        connection.execute.return_value = result

        self.connector.get_sample_rows("PUBLIC", "CUSTOMERS")

        executed_query = str(connection.execute.call_args.args[0])
        self.assertIn('"DATABASE_B"."PUBLIC"."CUSTOMERS"', executed_query)

    def test_dispose_closes_engine(self) -> None:
        self.connector.dispose()
        self.engine.dispose.assert_called_once()


if __name__ == "__main__":
    unittest.main()
