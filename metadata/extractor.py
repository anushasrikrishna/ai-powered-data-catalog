from __future__ import annotations

from connectors.base_connector import BaseConnector
from metadata.exceptions import MetadataExtractionError
from metadata.models import ColumnMetadata, TableMetadata
from metadata.normalizer import MetadataNormalizer
from metadata.profiler import MetadataProfiler


class MetadataExtractor:
    """Extract, normalize, and profile metadata through the shared connector abstraction."""

    def __init__(
        self,
        connector: BaseConnector,
        normalizer: MetadataNormalizer | None = None,
        profiler: MetadataProfiler | None = None,
        sample_value_limit: int = 5,
    ) -> None:
        self.connector = connector
        self.normalizer = normalizer or MetadataNormalizer()
        self.profiler = profiler or MetadataProfiler(connector, sample_value_limit=sample_value_limit)

    def extract_table_metadata(
        self,
        database_name: str,
        schema_name: str,
        table_name: str,
    ) -> TableMetadata:
        """Return normalized, profiled table metadata for the requested table."""
        raw_columns = self.connector.get_columns(schema_name, table_name)
        columns = [self._build_column_metadata(raw_column, ordinal_index) for ordinal_index, raw_column in enumerate(raw_columns, start=1)]

        table_metadata = TableMetadata(
            source_type=self._resolve_source_type(),
            database_name=database_name,
            schema_name=schema_name,
            table_name=table_name,
            table_type="TABLE",
            columns=columns,
        )

        table_metadata = self.normalizer.normalize_table_metadata(table_metadata)
        return self.profiler.profile_table(table_metadata)

    def _build_column_metadata(self, raw_column: dict[str, object], fallback_ordinal: int) -> ColumnMetadata:
        column_name = self._pick_value(raw_column, ("name", "column_name"))
        source_data_type = str(self._pick_value(raw_column, ("data_type", "source_data_type")))
        nullable = bool(raw_column.get("nullable", True))
        ordinal_position = int(raw_column.get("ordinal_position") or fallback_ordinal)

        return ColumnMetadata(
            column_name=str(column_name),
            source_data_type=source_data_type,
            normalized_data_type=self.normalizer.normalize_data_type(source_data_type),
            nullable=nullable,
            ordinal_position=ordinal_position,
        )

    def _resolve_source_type(self) -> str:
        explicit_source_type = getattr(self.connector, "source_type", None)
        if isinstance(explicit_source_type, str) and explicit_source_type.strip():
            return self._canonical_source_name(explicit_source_type)

        engine = getattr(self.connector, "engine", None)
        drivername = getattr(getattr(engine, "url", None), "drivername", "") or getattr(
            getattr(engine, "dialect", None),
            "name",
            "",
        )
        canonical_driver = str(drivername).lower()
        if canonical_driver.startswith("mssql"):
            return "sqlserver"
        if canonical_driver.startswith("postgresql"):
            return "postgresql"
        if canonical_driver.startswith("snowflake"):
            return "snowflake"
        if canonical_driver.startswith("sqlite"):
            return "sqlite"
        if canonical_driver:
            return self._canonical_source_name(canonical_driver.split("+", 1)[0])

        fallback_name = self.connector.__class__.__name__.replace("Connector", "")
        return self._canonical_source_name(fallback_name)

    def _canonical_source_name(self, source_name: str) -> str:
        normalized = source_name.strip().lower()
        alias_map = {
            "mssql": "sqlserver",
            "sql_server": "sqlserver",
            "sqlserver": "sqlserver",
            "postgres": "postgresql",
            "postgresql": "postgresql",
            "snowflake": "snowflake",
        }
        return alias_map.get(normalized, normalized)

    def _pick_value(self, raw_column: dict[str, object], keys: tuple[str, ...]) -> object:
        for key in keys:
            if key in raw_column:
                return raw_column[key]
        raise MetadataExtractionError(f"Column metadata is missing required keys: {keys!r}.")