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


class SQLServerConnector(BaseConnector):
	"""SQL Server connector for metadata browsing and sample row retrieval."""

	def __init__(
		self,
		host: str,
		database: str,
		username: str | None = None,
		password: str | None = None,
		port: int | None = 1433,
		driver: str = "ODBC Driver 18 for SQL Server",
		encrypt: str = "yes",
		trust_server_certificate: str = "yes",
		windows_auth: bool = False,
		engine: Engine | None = None,
	) -> None:
		self.host = host
		self.port = port
		self.database = database
		self.username = username
		self.password = password
		self.driver = driver
		self.encrypt = encrypt
		self.trust_server_certificate = trust_server_certificate
		self.windows_auth = windows_auth
		self.engine = engine or self._create_engine()

	def _is_localdb_host(self) -> bool:
		return self.host.strip().lower().startswith("(localdb)\\")

	def _build_url(self) -> URL:
		query = {
			"driver": self.driver,
			"Encrypt": self.encrypt,
			"TrustServerCertificate": self.trust_server_certificate,
		}
		if self.windows_auth:
			query["Trusted_Connection"] = "yes"
			port = None if self._is_localdb_host() else self.port
			return URL.create(
				"mssql+pyodbc",
				host=self.host,
				port=port,
				database=self.database,
				query=query,
			)
		return URL.create(
			"mssql+pyodbc",
			username=self.username,
			password=self.password,
			host=self.host,
			port=self.port,
			database=self.database,
			query=query,
		)

	def _connection_error_message(self) -> str:
		if self.windows_auth and self._is_localdb_host():
			return "Unable to connect to SQL Server LocalDB. Verify the LocalDB instance name, database, ODBC driver, Windows permissions, and that the LocalDB instance is running."
		if self.windows_auth:
			return "Unable to connect to SQL Server using Windows Authentication. Verify host, port, database, Windows access, and ODBC driver."
		return "Unable to connect to SQL Server. Verify host, port, credentials, database, and ODBC driver."

	def _create_engine(self) -> Engine:
		try:
			return create_engine(self._build_url(), pool_pre_ping=True)
		except SQLAlchemyError as exc:
			raise ConnectionFailedError(
				"Unable to initialize SQL Server connection. Verify that the configured ODBC driver is installed."
			) from exc

	def dispose(self) -> None:
		self.engine.dispose()

	def _is_connection_error(self, exc: Exception) -> bool:
		message = str(exc).lower()
		connection_markers = (
			"login failed",
			"timeout",
			"could not open a connection",
			"server does not exist",
			"name or service not known",
			"odbc",
			"network-related",
			"invalid connection string",
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
				self._connection_error_message()
			) from exc

	def list_databases(self) -> list[str]:
		query = text(
			"""
			SELECT name
			FROM sys.databases
			WHERE state_desc = 'ONLINE'
			  AND HAS_DBACCESS(name) = 1
			ORDER BY name
			"""
		)
		try:
			with self.engine.connect() as connection:
				rows = connection.execute(query).scalars().all()
			return [str(name) for name in rows]
		except Exception as exc:
			if self._is_connection_error(exc):
				raise ConnectionFailedError(
					self._connection_error_message()
				) from exc
			raise

	def list_schemas(self, database_name: str | None = None) -> list[str]:
		if database_name and database_name != self.database:
			raise DatabaseNotFoundError(
				f"Database '{database_name}' is not the active database for this connector instance."
			)

		query = text(
			"""
			SELECT name
			FROM sys.schemas
			WHERE name NOT IN ('sys', 'INFORMATION_SCHEMA')
			ORDER BY name
			"""
		)
		try:
			with self.engine.connect() as connection:
				rows = connection.execute(query).scalars().all()
			return [str(name) for name in rows]
		except Exception as exc:
			if self._is_connection_error(exc):
				raise ConnectionFailedError(
					self._connection_error_message()
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
					self._connection_error_message()
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
					self._connection_error_message()
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
					self._connection_error_message()
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
					self._connection_error_message()
				) from exc
			raise
