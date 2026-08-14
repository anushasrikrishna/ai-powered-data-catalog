from __future__ import annotations

from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, URL
from sqlalchemy.exc import SQLAlchemyError

from connectors.base_connector import BaseConnector
from connectors.exceptions import (
    ConnectionFailedError,
    DatabaseNotFoundError,
    SchemaNotFoundError,
    TableNotFoundError,
)


class SnowflakeConnector(BaseConnector):
    """Snowflake connector for database and metadata browsing."""

    def __init__(
        self,
        account: str,
        username: str,
        password: str,
        warehouse: str,
        database: str,
        schema: str | None = None,
        role: str = "",
        engine: Engine | None = None,
    ) -> None:
        self.account = account
        self.username = username
        self.password = password
        self.warehouse = warehouse
        self.database = database
        self.active_database = database
        self.schema = schema or ""
        self.role = role
        self.engine = engine or self._create_engine()

    def _build_url(self) -> URL:
        query = {
            "warehouse": self.warehouse,
            "role": self.role,
        }
        if self.schema:
            query["schema"] = self.schema
        return URL.create(
            "snowflake",
            username=self.username,
            password=self.password,
            host=self.account,
            database=self.database,
            query=query,
        )

    def _create_engine(self) -> Engine:
        try:
            return create_engine(self._build_url(), pool_pre_ping=True)
        except SQLAlchemyError as exc:
            raise ConnectionFailedError(
                "Unable to initialize Snowflake connection. Verify the account, credentials, and driver installation."
            ) from exc

    def dispose(self) -> None:
        self.engine.dispose()

    @staticmethod
    def _quote_identifier(identifier: str) -> str:
        """Quote a Snowflake identifier after rejecting unsafe input."""
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError("Snowflake identifiers must be non-empty strings.")
        if '"' in identifier or ";" in identifier or "\x00" in identifier:
            raise ValueError("Invalid Snowflake identifier.")
        return '"' + identifier.replace('"', '""') + '"'

    @staticmethod
    def _row_value(row: Any, *names: str) -> Any:
        if hasattr(row, "_mapping"):
            row = row._mapping
        if hasattr(row, "keys"):
            values = {str(key).lower(): value for key, value in row.items()}
            for name in names:
                if name.lower() in values:
                    return values[name.lower()]
        for name in names:
            if hasattr(row, name):
                return getattr(row, name)
        return None

    @classmethod
    def _values_from_result(cls, result: Any, *names: str) -> list[str]:
        return [
            str(value)
            for row in result.mappings().all()
            if (value := cls._row_value(row, *names)) is not None
        ]

    def _connection_failed(self) -> ConnectionFailedError:
        return ConnectionFailedError(
            "Unable to connect to Snowflake. Verify account, warehouse, database, role, and credentials."
        )

    def _validate_database(self, database_name: str) -> None:
        if database_name not in self.list_databases():
            raise DatabaseNotFoundError(f"Database '{database_name}' was not found.")

    def _validate_schema(self, schema_name: str) -> None:
        if schema_name not in self.list_schemas():
            raise SchemaNotFoundError(f"Schema '{schema_name}' was not found.")

    def _validate_table(self, schema_name: str, table_name: str) -> None:
        if table_name not in self.list_tables(schema_name):
            raise TableNotFoundError(
                f"Table '{table_name}' was not found in schema '{schema_name}'."
            )

    def test_connection(self) -> bool:
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return True
        except Exception as exc:
            raise self._connection_failed() from exc

    def list_databases(self) -> list[str]:
        try:
            with self.engine.connect() as connection:
                result = connection.execute(text("SHOW DATABASES"))
                databases = self._values_from_result(result, "name", "database_name")
            return sorted(databases)
        except Exception as exc:
            raise self._connection_failed() from exc

    def list_schemas(self, database_name: str | None = None) -> list[str]:
        selected_database = database_name or self.active_database
        self._validate_database(selected_database)
        database_identifier = self._quote_identifier(selected_database)
        query = text(
            f"SELECT SCHEMA_NAME FROM {database_identifier}.INFORMATION_SCHEMA.SCHEMATA "
            "WHERE SCHEMA_NAME <> 'INFORMATION_SCHEMA' ORDER BY SCHEMA_NAME"
        )
        try:
            with self.engine.connect() as connection:
                result = connection.execute(query)
                schemas = self._values_from_result(result, "schema_name")
            if database_name is not None:
                self.active_database = selected_database
            return sorted(schemas)
        except (DatabaseNotFoundError, ConnectionFailedError):
            raise
        except Exception as exc:
            raise self._connection_failed() from exc

    def list_tables(self, schema_name: str) -> list[str]:
        self._validate_schema(schema_name)
        database_identifier = self._quote_identifier(self.active_database)
        query = text(
            f"SELECT TABLE_NAME FROM {database_identifier}.INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_SCHEMA = :schema_name AND TABLE_TYPE = 'BASE TABLE' "
            "ORDER BY TABLE_NAME"
        )
        try:
            with self.engine.connect() as connection:
                result = connection.execute(query, {"schema_name": schema_name})
                tables = self._values_from_result(result, "table_name")
            return sorted(tables)
        except (SchemaNotFoundError, ConnectionFailedError):
            raise
        except Exception as exc:
            raise self._connection_failed() from exc

    def get_columns(self, schema_name: str, table_name: str) -> list[dict[str, Any]]:
        self._validate_schema(schema_name)
        self._validate_table(schema_name, table_name)
        database_identifier = self._quote_identifier(self.active_database)
        query = text(
            f"SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, ORDINAL_POSITION "
            f"FROM {database_identifier}.INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = :schema_name AND TABLE_NAME = :table_name "
            "ORDER BY ORDINAL_POSITION"
        )
        try:
            with self.engine.connect() as connection:
                rows = connection.execute(
                    query,
                    {"schema_name": schema_name, "table_name": table_name},
                ).mappings().all()
            return [
                {
                    "name": str(self._row_value(row, "column_name")),
                    "data_type": str(self._row_value(row, "data_type")),
                    "nullable": str(self._row_value(row, "is_nullable")).upper() == "YES",
                    "ordinal_position": int(self._row_value(row, "ordinal_position")),
                }
                for row in rows
            ]
        except (SchemaNotFoundError, TableNotFoundError, ConnectionFailedError):
            raise
        except Exception as exc:
            raise self._connection_failed() from exc

    def get_sample_rows(
        self,
        schema_name: str,
        table_name: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        self._validate_schema(schema_name)
        self._validate_table(schema_name, table_name)
        effective_limit = max(1, int(limit))
        database_identifier = self._quote_identifier(self.active_database)
        schema_identifier = self._quote_identifier(schema_name)
        table_identifier = self._quote_identifier(table_name)
        statement = text(
            f"SELECT * FROM {database_identifier}.{schema_identifier}.{table_identifier} "
            "LIMIT :row_limit"
        )
        try:
            with self.engine.connect() as connection:
                rows = connection.execute(
                    statement,
                    {"row_limit": effective_limit},
                ).mappings().all()
            return [dict(row) for row in rows]
        except (TableNotFoundError, ConnectionFailedError):
            raise
        except Exception as exc:
            raise self._connection_failed() from exc
