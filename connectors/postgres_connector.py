from __future__ import annotations

from typing import Any

from sqlalchemy import MetaData, Table, create_engine, inspect, select, text
from sqlalchemy.engine import Engine, URL
from sqlalchemy.exc import NoSuchTableError, SQLAlchemyError

from connectors.base_connector import BaseConnector
from connectors.exceptions import (
	ConnectionFailedError,
	DatabaseNotFoundError,
	SchemaNotFoundError,
	TableNotFoundError,
)


class PostgresConnector(BaseConnector):
	"""PostgreSQL connector for metadata browsing and sample row retrieval."""

	def __init__(
		self,
		host: str,
		database: str,
		username: str,
		password: str,
		port: int = 5432,
		engine: Engine | None = None,
	) -> None:
		self.host = host
		self.port = port
		self.database = database
		self.username = username
		self.password = password
		self.engine = engine or self._create_engine()

	def _build_url(self) -> URL:
		return URL.create(
			"postgresql+psycopg",
			username=self.username,
			password=self.password,
			host=self.host,
			port=self.port,
			database=self.database,
		)

	def _create_engine(self) -> Engine:
		try:
			return create_engine(self._build_url(), pool_pre_ping=True)
		except SQLAlchemyError as exc:
			raise ConnectionFailedError(
				"Unable to initialize PostgreSQL connection. Verify SQLAlchemy and psycopg installation."
			) from exc

	def dispose(self) -> None:
		self.engine.dispose()

	def _is_connection_error(self, exc: Exception) -> bool:
		message = str(exc).lower()
		connection_markers = (
			"password authentication failed",
			"connection refused",
			"could not translate host name",
			"timeout",
			"database \"",
			"does not exist",
			"could not connect",
		)
		return any(marker in message for marker in connection_markers)

	def _validate_schema(self, schema_name: str) -> None:
		schemas = self.list_schemas()
		if schema_name not in schemas:
			raise SchemaNotFoundError(f"Schema '{schema_name}' was not found.")

	def _validate_table(self, schema_name: str, table_name: str) -> None:
		tables = self.list_tables(schema_name)
		if table_name not in tables:
			raise TableNotFoundError(
				f"Table '{table_name}' was not found in schema '{schema_name}'."
			)

	def test_connection(self) -> bool:
		try:
			with self.engine.connect() as connection:
				connection.execute(text("SELECT 1"))
			return True
		except Exception as exc:
			raise ConnectionFailedError(
				"Unable to connect to PostgreSQL. Verify host, port, database, username, and password."
			) from exc

	def list_databases(self) -> list[str]:
		query = text(
			"""
			SELECT datname
			FROM pg_database
			WHERE datallowconn = true
			  AND datistemplate = false
			ORDER BY datname
			"""
		)
		try:
			with self.engine.connect() as connection:
				rows = connection.execute(query).scalars().all()
			return [str(name) for name in rows]
		except Exception as exc:
			if self._is_connection_error(exc):
				raise ConnectionFailedError(
					"Unable to connect to PostgreSQL. Verify host, port, database, username, and password."
				) from exc
			raise

	def list_schemas(self, database_name: str | None = None) -> list[str]:
		if database_name and database_name != self.database:
			raise DatabaseNotFoundError(
				f"Database '{database_name}' is not the active database for this connector instance."
			)

		try:
			inspector = inspect(self.engine)
			all_schemas = inspector.get_schema_names()
			excluded_prefixes = ("pg_toast", "pg_temp", "pg_catalog", "pg_internal")
			filtered_schemas = [
				schema
				for schema in all_schemas
				if schema not in {"information_schema", "pg_toast"}
				and not schema.startswith(excluded_prefixes)
			]
			return sorted(str(schema) for schema in filtered_schemas)
		except Exception as exc:
			if self._is_connection_error(exc):
				raise ConnectionFailedError(
					"Unable to connect to PostgreSQL. Verify host, port, database, username, and password."
				) from exc
			raise

	def list_tables(self, schema_name: str) -> list[str]:
		self._validate_schema(schema_name)
		try:
			inspector = inspect(self.engine)
			tables = inspector.get_table_names(schema=schema_name)
			return sorted(str(name) for name in tables)
		except Exception as exc:
			if self._is_connection_error(exc):
				raise ConnectionFailedError(
					"Unable to connect to PostgreSQL. Verify host, port, database, username, and password."
				) from exc
			raise

	def get_columns(self, schema_name: str, table_name: str) -> list[dict[str, Any]]:
		self._validate_schema(schema_name)
		self._validate_table(schema_name, table_name)
		try:
			inspector = inspect(self.engine)
			columns = inspector.get_columns(table_name, schema=schema_name)
			normalized_columns: list[dict[str, Any]] = []
			for idx, column in enumerate(columns, start=1):
				source_type = str(column.get("type", ""))
				normalized_columns.append(
					{
						"name": str(column["name"]),
						"data_type": source_type,
						"nullable": bool(column.get("nullable", True)),
						"ordinal_position": int(column.get("ordinal_position") or idx),
					}
				)
			return normalized_columns
		except Exception as exc:
			if self._is_connection_error(exc):
				raise ConnectionFailedError(
					"Unable to connect to PostgreSQL. Verify host, port, database, username, and password."
				) from exc
			raise

	def get_sample_rows(
		self,
		schema_name: str,
		table_name: str,
		limit: int = 5,
	) -> list[dict[str, Any]]:
		self._validate_schema(schema_name)
		self._validate_table(schema_name, table_name)
		effective_limit = max(1, int(limit))

		metadata = MetaData()
		try:
			table = Table(
				table_name,
				metadata,
				schema=schema_name,
				autoload_with=self.engine,
			)
		except NoSuchTableError as exc:
			raise TableNotFoundError(
				f"Table '{table_name}' was not found in schema '{schema_name}'."
			) from exc
		except Exception as exc:
			if self._is_connection_error(exc):
				raise ConnectionFailedError(
					"Unable to connect to PostgreSQL. Verify host, port, database, username, and password."
				) from exc
			raise

		statement = select(table).limit(effective_limit)
		try:
			with self.engine.connect() as connection:
				rows = connection.execute(statement).mappings().all()
			return [dict(row) for row in rows]
		except Exception as exc:
			if self._is_connection_error(exc):
				raise ConnectionFailedError(
					"Unable to connect to PostgreSQL. Verify host, port, database, username, and password."
				) from exc
			raise
