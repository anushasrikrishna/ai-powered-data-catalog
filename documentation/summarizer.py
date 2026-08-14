from __future__ import annotations

from collections import Counter

from documentation.classifier import ColumnClassifier
from documentation.models import (
    ColumnDocumentation,
    TableDocumentation,
    TableTechnicalSummary,
)
from metadata.models import ColumnMetadata, TableMetadata


class MetadataDocumentationGenerator:
    """Transform Phase 3 metadata into deterministic structured documentation."""

    NORMALIZED_TYPES = (
        "NUMBER",
        "DECIMAL",
        "STRING",
        "DATE",
        "DATETIME",
        "BOOLEAN",
        "BINARY",
        "OTHER",
    )

    def __init__(self, classifier: ColumnClassifier | None = None) -> None:
        self.classifier = classifier or ColumnClassifier()

    def generate(self, table_metadata: TableMetadata) -> TableDocumentation:
        """Generate documentation without database access or profile recalculation."""
        columns = [self._document_column(column) for column in table_metadata.columns]
        summary = self._build_summary(table_metadata, columns)
        return TableDocumentation(
            source_type=table_metadata.source_type,
            database_name=table_metadata.database_name,
            schema_name=table_metadata.schema_name,
            table_name=table_metadata.table_name,
            table_type=table_metadata.table_type,
            summary=summary,
            columns=columns,
        )

    def build_documentation(self, table_metadata: TableMetadata) -> TableDocumentation:
        """Alias for callers that prefer a build-oriented API name."""
        return self.generate(table_metadata)

    def _document_column(self, column: ColumnMetadata) -> ColumnDocumentation:
        return ColumnDocumentation(
            column_name=column.column_name,
            source_data_type=column.source_data_type,
            normalized_data_type=column.normalized_data_type,
            nullable=column.nullable,
            ordinal_position=column.ordinal_position,
            possible_category=self.classifier.classify(column),
            null_count=column.null_count,
            distinct_count=column.distinct_count,
            minimum=column.minimum,
            maximum=column.maximum,
            sample_values=list(column.sample_values),
        )

    def _build_summary(
        self,
        table_metadata: TableMetadata,
        columns: list[ColumnDocumentation],
    ) -> TableTechnicalSummary:
        type_counts = Counter(column.normalized_data_type.upper() for column in columns)
        number_count = type_counts["NUMBER"]
        decimal_count = type_counts["DECIMAL"]
        return TableTechnicalSummary(
            row_count=table_metadata.row_count,
            column_count=len(columns),
            nullable_column_count=sum(column.nullable for column in columns),
            non_nullable_column_count=sum(not column.nullable for column in columns),
            numeric_column_count=number_count + decimal_count,
            number_column_count=number_count,
            decimal_column_count=decimal_count,
            string_column_count=type_counts["STRING"],
            date_column_count=type_counts["DATE"],
            datetime_column_count=type_counts["DATETIME"],
            boolean_column_count=type_counts["BOOLEAN"],
            binary_column_count=type_counts["BINARY"],
            other_column_count=type_counts["OTHER"],
        )


MetadataDocumenter = MetadataDocumentationGenerator
