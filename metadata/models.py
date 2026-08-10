from typing import Any
from pydantic import BaseModel, Field


class ColumnMetadata(BaseModel):
    column_name: str
    source_data_type: str
    normalized_data_type: str
    nullable: bool
    ordinal_position: int
    sample_values: list[Any] = Field(default_factory=list)


class TableMetadata(BaseModel):
    source_type: str
    database_name: str
    schema_name: str
    table_name: str
    table_type: str = "BASE TABLE"
    row_count: int | None = None
    columns: list[ColumnMetadata] = Field(default_factory=list)