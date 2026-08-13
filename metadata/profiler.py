from __future__ import annotations

from typing import Any

from sqlalchemy import MetaData, Table, distinct, func, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import NoSuchTableError, SQLAlchemyError

from connectors.base_connector import BaseConnector
from connectors.exceptions import TableNotFoundError
from metadata.exceptions import MetadataProfilingError
from metadata.models import ColumnMetadata, TableMetadata


class MetadataProfiler:
    """Calculate deterministic table and column profile metrics using database-side queries."""

    def __init__(self, connector: BaseConnector, sample_value_limit: int = 5) -> None:
        self.connector = connector
        self.sample_value_limit = max(1, int(sample_value_limit))
        self.engine = self._resolve_engine(connector)

    def profile_table(self, table_metadata: TableMetadata) -> TableMetadata:
        """Populate table-level and column-level profile metrics in place and return the table metadata."""
        table = self._reflect_table(table_metadata.database_name, table_metadata.schema_name, table_metadata.table_name)

        try:
            with self.engine.connect() as connection:
                row_count = int(connection.execute(select(func.count()).select_from(table)).scalar_one())
                table_metadata.row_count = row_count

                for column_metadata in table_metadata.columns:
                    self._profile_column(connection, table, column_metadata, row_count)

            return table_metadata
        except MetadataProfilingError:
            raise
        except SQLAlchemyError as exc:
            raise MetadataProfilingError(
                f"Unable to profile table '{table_metadata.table_name}' in schema '{table_metadata.schema_name}'."
            ) from exc

    def _profile_column(
        self,
        connection: Any,
        table: Table,
        column_metadata: ColumnMetadata,
        row_count: int,
    ) -> None:
        column = self._resolve_column(table, column_metadata.column_name)

        if row_count == 0:
            column_metadata.null_count = 0
            column_metadata.distinct_count = 0
            column_metadata.minimum = None
            column_metadata.maximum = None
            column_metadata.sample_values = []
            return

        non_null_count = self._scalar(
            connection,
            select(func.count(column)).select_from(table),
            default=None,
        )
        if non_null_count is None:
            column_metadata.null_count = None
        else:
            column_metadata.null_count = max(row_count - int(non_null_count), 0)

        distinct_count = self._scalar(
            connection,
            select(func.count(distinct(column))).select_from(table),
            default=0,
        )
        column_metadata.distinct_count = int(distinct_count) if distinct_count is not None else 0

        if self._is_comparable(column_metadata.normalized_data_type):
            minimum, maximum = self._scalar_row(
                connection,
                select(func.min(column), func.max(column)).select_from(table),
                default=(None, None),
            )
            column_metadata.minimum = minimum
            column_metadata.maximum = maximum

            sample_stmt = (
                select(column)
                .select_from(table)
                .where(column.is_not(None))
                .distinct()
                .order_by(column.asc())
                .limit(self.sample_value_limit)
            )
            sample_rows = self._rows(connection, sample_stmt, default=[])
            column_metadata.sample_values = [row[0] for row in sample_rows]
        else:
            column_metadata.minimum = None
            column_metadata.maximum = None
            column_metadata.sample_values = []

    def _reflect_table(self, database_name: str, schema_name: str, table_name: str) -> Table:
        metadata = MetaData()
        reflected_schema = schema_name or None
        try:
            return Table(
                table_name,
                metadata,
                schema=reflected_schema,
                autoload_with=self.engine,
            )
        except NoSuchTableError as exc:
            raise TableNotFoundError(
                f"Table '{table_name}' was not found in schema '{schema_name or '<default>'}'."
            ) from exc
        except SQLAlchemyError as exc:
            raise MetadataProfilingError(
                f"Unable to reflect table '{table_name}' in schema '{schema_name or '<default>'}'."
            ) from exc

    def _resolve_engine(self, connector: BaseConnector) -> Engine:
        engine = getattr(connector, "engine", None)
        if engine is None:
            raise MetadataProfilingError("Connector does not expose a SQLAlchemy engine.")
        return engine

    def _resolve_column(self, table: Table, column_name: str):
        if column_name in table.c:
            return table.c[column_name]

        lower_map = {column.name.lower(): column for column in table.columns}
        if column_name.lower() in lower_map:
            return lower_map[column_name.lower()]

        raise MetadataProfilingError(f"Column '{column_name}' was not found in reflected table metadata.")

    def _is_comparable(self, normalized_data_type: str) -> bool:
        return normalized_data_type in {"NUMBER", "DECIMAL", "STRING", "DATE", "DATETIME", "BOOLEAN"}

    def _scalar(self, connection: Any, statement: Any, default: Any) -> Any:
        try:
            value = connection.execute(statement).scalar_one()
        except Exception:
            return default
        return value

    def _scalar_row(self, connection: Any, statement: Any, default: tuple[Any, Any]) -> tuple[Any, Any]:
        try:
            row = connection.execute(statement).one()
        except Exception:
            return default
        return row[0], row[1]

    def _rows(self, connection: Any, statement: Any, default: list[tuple[Any, ...]]) -> list[tuple[Any, ...]]:
        try:
            return list(connection.execute(statement).all())
        except Exception:
            return default