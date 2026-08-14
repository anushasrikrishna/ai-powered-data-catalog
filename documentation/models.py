from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class TableTechnicalSummary(BaseModel):
    """Deterministic factual counts derived from Phase 3 table metadata."""

    row_count: int | None = None
    column_count: int = 0
    nullable_column_count: int = 0
    non_nullable_column_count: int = 0
    numeric_column_count: int = 0
    number_column_count: int = 0
    decimal_column_count: int = 0
    string_column_count: int = 0
    date_column_count: int = 0
    datetime_column_count: int = 0
    boolean_column_count: int = 0
    binary_column_count: int = 0
    other_column_count: int = 0


class ColumnDocumentation(BaseModel):
    """Structured documentation for one Phase 3 column."""

    column_name: str
    source_data_type: str
    normalized_data_type: str
    nullable: bool
    ordinal_position: int
    possible_category: str
    null_count: int | None = None
    distinct_count: int | None = None
    minimum: Any | None = None
    maximum: Any | None = None
    sample_values: list[Any] = Field(default_factory=list)


class TableDocumentation(BaseModel):
    """Serializable Phase 4 documentation for one table."""

    source_type: str
    database_name: str
    schema_name: str
    table_name: str
    table_type: str
    summary: TableTechnicalSummary
    columns: list[ColumnDocumentation] = Field(default_factory=list)
