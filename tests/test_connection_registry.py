from __future__ import annotations

import unittest

from core.connection_registry import ConnectionRegistry


class FakeConnector:
    def __init__(self) -> None:
        self.disposed = False
        self.engine = object()

    def dispose(self) -> None:
        self.disposed = True


def settings(source: str, database: str, host: str) -> dict[str, object]:
    if source == "snowflake":
        return {"account": host, "database": database, "username": "analyst", "password": "secret"}
    return {"host": host, "port": 5432, "database": database, "username": "analyst", "password": "secret"}


class TestConnectionRegistry(unittest.TestCase):
    def test_registry_starts_empty_and_supports_multiple_sources(self) -> None:
        registry = ConnectionRegistry()
        self.assertEqual(registry.entries(), [])

        sql = registry.register("sqlserver", settings("sqlserver", "booking", "sql-host"), FakeConnector())
        postgres = registry.register("postgresql", settings("postgresql", "orders", "pg-host"), FakeConnector())
        snowflake = registry.register("snowflake", settings("snowflake", "analytics", "account"), FakeConnector())

        self.assertEqual({entry.status for entry in registry.entries()}, {"CONNECTED"})
        self.assertEqual(len(registry.entries()), 3)
        self.assertEqual(registry.get(sql.connection_id).database_name, "booking")
        self.assertEqual(registry.get(postgres.connection_id).database_name, "orders")
        self.assertEqual(registry.get(snowflake.connection_id).database_name, "analytics")

    def test_disconnect_removes_entry_and_is_scoped_to_one_connection(self) -> None:
        registry = ConnectionRegistry()
        first_connector = FakeConnector()
        second_connector = FakeConnector()
        first = registry.register("sqlserver", settings("sqlserver", "booking", "sql-host"), first_connector)
        second = registry.register("postgresql", settings("postgresql", "orders", "pg-host"), second_connector)

        registry.disconnect(first.connection_id)
        self.assertIsNone(registry.get(first.connection_id))
        self.assertTrue(first_connector.disposed)
        self.assertTrue(registry.get(second.connection_id).connected)

        registry.disconnect(second.connection_id)
        self.assertEqual(registry.entries(), [])
        self.assertTrue(second_connector.disposed)

    def test_duplicate_logical_connection_reuses_entry_id(self) -> None:
        registry = ConnectionRegistry()
        first = registry.register("PostgreSQL", settings("postgresql", "orders", "pg-host"), FakeConnector())
        second = registry.register("postgresql", settings("postgresql", "orders", "pg-host"), FakeConnector())

        self.assertEqual(first.connection_id, second.connection_id)
        self.assertEqual(len(registry.entries()), 1)
        self.assertEqual(registry.get(first.connection_id).status, "CONNECTED")


if __name__ == "__main__":
    unittest.main()
