from __future__ import annotations

import re

from metadata.exceptions import NormalizationError
from metadata.models import ColumnMetadata, TableMetadata


class MetadataNormalizer:
    """Normalize source-specific datatypes into the application's shared taxonomy."""

    NUMBER_TYPES = {
        "INT",
        "INTEGER",
        "BIGINT",
        "SMALLINT",
        "TINYINT",
        "MEDIUMINT",
    }
    DECIMAL_TYPES = {
        "DECIMAL",
        "NUMERIC",
        "MONEY",
        "SMALLMONEY",
        "REAL",
        "FLOAT",
        "DOUBLE",
        "DOUBLE PRECISION",
        "SINGLE",
        "SINGLE PRECISION",
    }
    STRING_TYPES = {
        "VARCHAR",
        "NVARCHAR",
        "CHAR",
        "NCHAR",
        "TEXT",
        "NTEXT",
        "CHARACTER",
        "CHARACTER VARYING",
        "STRING",
        "CLOB",
        "LONGTEXT",
        "MEDIUMTEXT",
        "TINYTEXT",
        "ENUM",
        "SET",
    }
    DATE_TYPES = {"DATE"}
    DATETIME_TYPES = {
        "DATETIME",
        "DATETIME2",
        "SMALLDATETIME",
        "TIMESTAMP",
        "TIMESTAMP_NTZ",
        "TIMESTAMP_LTZ",
        "TIMESTAMP_TZ",
        "TIMESTAMPTZ",
        "TIMESTAMP WITH TIME ZONE",
        "TIMESTAMP WITHOUT TIME ZONE",
    }
    BOOLEAN_TYPES = {"BOOLEAN", "BOOL", "BIT"}
    BINARY_TYPES = {
        "BINARY",
        "VARBINARY",
        "IMAGE",
        "BYTEA",
        "BLOB",
        "LONGBLOB",
        "MEDIUMBLOB",
        "TINYBLOB",
    }

    def normalize_data_type(self, source_data_type: str) -> str:
        """Return one of NUMBER, DECIMAL, STRING, DATE, DATETIME, BOOLEAN, BINARY, OTHER."""
        if not isinstance(source_data_type, str):
            raise NormalizationError("Source datatype must be a string.")

        canonical_type, parameters = self._canonicalize(source_data_type)

        if canonical_type in self.BOOLEAN_TYPES:
            return "BOOLEAN"

        if canonical_type in self.DATE_TYPES:
            return "DATE"

        if canonical_type in self.DATETIME_TYPES or canonical_type.startswith("TIMESTAMP"):
            return "DATETIME"

        if canonical_type in self.BINARY_TYPES:
            return "BINARY"

        if canonical_type in self.STRING_TYPES:
            return "STRING"

        if canonical_type in self.NUMBER_TYPES:
            return "NUMBER"

        if canonical_type == "NUMBER":
            scale = self._extract_scale(parameters)
            if scale is not None and scale > 0:
                return "DECIMAL"
            return "NUMBER"

        if canonical_type in self.DECIMAL_TYPES:
            return "DECIMAL"

        return "OTHER"

    def normalize_column(self, column_metadata: ColumnMetadata) -> ColumnMetadata:
        """Normalize the source datatype on a single column metadata model."""
        column_metadata.normalized_data_type = self.normalize_data_type(column_metadata.source_data_type)
        return column_metadata

    def normalize_table_metadata(self, table_metadata: TableMetadata) -> TableMetadata:
        """Normalize every column in a table metadata model in place and return it."""
        for column_metadata in table_metadata.columns:
            self.normalize_column(column_metadata)
        return table_metadata

    def _canonicalize(self, source_data_type: str) -> tuple[str, str | None]:
        cleaned = re.sub(r"\s+", " ", source_data_type.strip().upper())
        cleaned = re.sub(r"\s+COLLATE\b.*$", "", cleaned).strip()
        cleaned = cleaned.replace("`", "").replace('"', "")
        match = re.match(r"^(?P<base>[^()]+?)(?:\((?P<params>.*)\))?$", cleaned)
        if not match:
            return cleaned, None

        base = match.group("base").strip()
        parameters = match.group("params")
        return base, parameters

    def _extract_scale(self, parameters: str | None) -> int | None:
        if not parameters:
            return None

        parts = [part.strip() for part in parameters.split(",") if part.strip()]
        if len(parts) < 2:
            return 0

        try:
            return int(parts[1])
        except ValueError:
            return None