from __future__ import annotations

from typing import Any

import streamlit as st

from documentation import MetadataDocumentationGenerator
from documentation.models import TableDocumentation
from metadata.models import TableMetadata
from storage.repository import MetadataRepository
from ui.components import (
    render_count_chips,
    render_empty_state,
    render_html_table,
    render_page_header,
    render_workspace_status,
)


ALL_SOURCES = "All Sources"
ALL_DATABASES = "All Databases"
ALL_SCHEMAS = "All Schemas"

SOURCE_DISPLAY_NAME_BY_TYPE = {
    "sqlserver": "SQL Server",
    "postgresql": "PostgreSQL",
    "snowflake": "Snowflake",
}


def _source_display_name(source_value: str) -> str:
    normalized = source_value.strip().lower()
    return SOURCE_DISPLAY_NAME_BY_TYPE.get(normalized, source_value)


def _format_optional(value: Any) -> str:
    if value is None:
        return "-"
    if value == "":
        return "-"
    return str(value)


def _format_count(value: int | None) -> str:
    if value is None:
        return "-"
    return f"{value:,}"


def _format_sample_values(values: list[Any]) -> str:
    if not values:
        return "-"
    return ", ".join(_format_optional(value) for value in values[:5])


def _dataset_identity(table_metadata: TableMetadata) -> tuple[str, str, str, str]:
    return (
        table_metadata.source_type,
        table_metadata.database_name,
        table_metadata.schema_name,
        table_metadata.table_name,
    )


def _dataset_label(table_metadata: TableMetadata) -> str:
    return (
        f"{_source_display_name(table_metadata.source_type)} / "
        f"{table_metadata.database_name} / "
        f"{table_metadata.schema_name} / "
        f"{table_metadata.table_name}"
    )


def _load_catalog() -> tuple[list[TableMetadata], Exception | None]:
    try:
        repository = MetadataRepository()
        return repository.list_tables(), None
    except Exception as exc:
        return [], exc


def _matches_search(table_metadata: TableMetadata, query: str) -> bool:
    if not query:
        return True

    searchable_text = " ".join(
        [
            _source_display_name(table_metadata.source_type),
            table_metadata.source_type,
            table_metadata.database_name,
            table_metadata.schema_name,
            table_metadata.table_name,
            table_metadata.table_type,
            *[column.column_name for column in table_metadata.columns],
            *[column.source_data_type for column in table_metadata.columns],
            *[column.normalized_data_type for column in table_metadata.columns],
        ]
    ).casefold()
    return query.casefold() in searchable_text


def _filter_catalog(
    catalog: list[TableMetadata],
    search_query: str,
    source_filter: str,
    database_filter: str,
    schema_filter: str,
) -> list[TableMetadata]:
    return [
        table_metadata
        for table_metadata in catalog
        if _matches_search(table_metadata, search_query)
        and (source_filter == ALL_SOURCES or _source_display_name(table_metadata.source_type) == source_filter)
        and (database_filter == ALL_DATABASES or table_metadata.database_name == database_filter)
        and (schema_filter == ALL_SCHEMAS or table_metadata.schema_name == schema_filter)
    ]


def _selectbox_with_reset(label: str, options: list[str], key: str) -> str:
    if st.session_state.get(key) not in options:
        st.session_state[key] = options[0]
    return st.selectbox(label, options, key=key)


def _render_catalog_summary(catalog: list[TableMetadata]) -> None:
    source_count = len({_source_display_name(table.source_type) for table in catalog})
    database_count = len({table.database_name for table in catalog})
    column_count = sum(len(table.columns) for table in catalog)

    render_workspace_status(
        [
            ("catalog", "Cataloged Datasets", f"{len(catalog):,}", "Persisted metadata entries"),
            ("database", "Sources", f"{source_count:,}", "Connected platform types"),
            ("dashboard", "Databases", f"{database_count:,}", "Cataloged database contexts"),
            ("search", "Total Columns", f"{column_count:,}", "Stored column definitions"),
        ]
    )


def _catalog_rows(catalog: list[TableMetadata]) -> list[dict[str, str | int]]:
    return [
        {
            "Source": _source_display_name(table.source_type),
            "Database": table.database_name,
            "Schema": table.schema_name,
            "Table": table.table_name,
            "Type": table.table_type,
            "Rows": _format_count(table.row_count),
            "Columns": len(table.columns),
        }
        for table in catalog
    ]


def _column_rows(table_metadata: TableMetadata) -> list[dict[str, str | int]]:
    return [
        {
            "Column": column.column_name,
            "Source Type": column.source_data_type,
            "Normalized Type": column.normalized_data_type,
            "Nullable": "Yes" if column.nullable else "No",
            "Position": column.ordinal_position,
            "Null Count": _format_count(column.null_count),
            "Distinct Count": _format_count(column.distinct_count),
            "Minimum": _format_optional(column.minimum),
            "Maximum": _format_optional(column.maximum),
            "Sample Values": _format_sample_values(column.sample_values),
        }
        for column in sorted(table_metadata.columns, key=lambda item: item.ordinal_position)
    ]


def _documentation_column_rows(documentation: TableDocumentation) -> list[dict[str, Any]]:
    return [
        {
            "Column": column.column_name,
            "Source Type": column.source_data_type,
            "Normalized Type": column.normalized_data_type,
            "Possible Category": column.possible_category,
            "Nullable": "Yes" if column.nullable else "No",
            "Position": column.ordinal_position,
            "Null Count": _format_count(column.null_count),
            "Distinct Count": _format_count(column.distinct_count),
            "Minimum": _format_optional(column.minimum),
            "Maximum": _format_optional(column.maximum),
            "Sample Values": _format_sample_values(column.sample_values),
        }
        for column in sorted(documentation.columns, key=lambda item: item.ordinal_position)
    ]


def _render_documentation_summary(documentation: TableDocumentation) -> None:
    summary = documentation.summary
    render_workspace_status(
        [
            ("dashboard", "Rows", _format_count(summary.row_count), "Persisted source row count"),
            ("catalog", "Columns", f"{summary.column_count:,}", "Documented columns"),
            ("search", "Nullable", f"{summary.nullable_column_count:,}", "Columns allowing nulls"),
            ("quality", "Non-Nullable", f"{summary.non_nullable_column_count:,}", "Required columns"),
        ]
    )

    type_counts = [
        ("Number", summary.number_column_count),
        ("Decimal", summary.decimal_column_count),
        ("String", summary.string_column_count),
        ("Date", summary.date_column_count),
        ("Datetime", summary.datetime_column_count),
        ("Boolean", summary.boolean_column_count),
        ("Binary", summary.binary_column_count),
        ("Other", summary.other_column_count),
    ]
    meaningful_counts = [(label, count) for label, count in type_counts if count]
    render_count_chips("DATA TYPE DISTRIBUTION", meaningful_counts)

    category_order = [
        "Identifier",
        "Name",
        "Contact Information",
        "Location",
        "Date/Time",
        "Financial/Measure",
        "Quantity/Measure",
        "Boolean/Flag",
        "Text/Description",
        "Other",
    ]
    category_counts = {category: 0 for category in category_order}
    for column in documentation.columns:
        if column.possible_category in category_counts:
            category_counts[column.possible_category] += 1
    render_count_chips(
        "COLUMN CLASSIFICATIONS",
        [(category, category_counts[category]) for category in category_order if category_counts[category]],
        "Categories are inferred deterministically from column names and normalized data types.",
        kind="category",
    )


def _render_selected_dataset_documentation(table_metadata: TableMetadata) -> None:
    documentation = None
    try:
        documentation = MetadataDocumentationGenerator().generate(table_metadata)
    except Exception:
        st.warning("Unable to generate dataset documentation.")

    if documentation is not None:
        st.markdown('<div class="section-kicker">DOCUMENTATION</div>', unsafe_allow_html=True)
        st.markdown('<div class="documentation-subsection-title">TECHNICAL SUMMARY</div>', unsafe_allow_html=True)
        _render_documentation_summary(documentation)
        column_rows = _documentation_column_rows(documentation)
    else:
        column_rows = _column_rows(table_metadata)

    st.markdown('<div class="section-kicker">COLUMN METADATA</div>', unsafe_allow_html=True)
    if column_rows:
        render_html_table(
            column_rows,
            table_id="catalog-column-metadata",
            download_filename="selected_column_metadata.csv",
        )
    elif documentation is not None:
        render_empty_state(
            "No column documentation",
            "No column documentation is available for this dataset.",
            "catalog",
        )
    else:
        render_empty_state("No columns found", "This cataloged dataset has no stored column metadata.", "catalog")


render_page_header(
    "Data Catalog",
    "Browse persisted metadata from successful scans.",
    "Search and filter cataloged datasets without reconnecting to the source system.",
    icon="catalog",
)

catalog, catalog_error = _load_catalog()
if catalog_error is not None:
    st.error("Unable to load the metadata catalog.")
    st.stop()

if not catalog:
    render_empty_state(
        "No cataloged datasets yet",
        "Scan metadata from a connected data source to populate the catalog.",
        "catalog",
    )
    st.page_link(
        "pages/2_metadata_scan.py",
        label="Go to Metadata Scan",
        icon=":material/manage_search:",
    )
    st.stop()

_render_catalog_summary(catalog)

st.markdown('<div class="toolbar-panel">', unsafe_allow_html=True)
search_column, source_column, database_column, schema_column = st.columns([2, 1, 1, 1])

with search_column:
    search_query = st.text_input(
        "Search catalog",
        placeholder="Search by source, database, schema, table or column",
        key="catalog_search_query",
    ).strip()

source_options = [ALL_SOURCES] + sorted({_source_display_name(table.source_type) for table in catalog})
with source_column:
    selected_source = _selectbox_with_reset("Source", source_options, "catalog_source_filter")

source_scoped_catalog = [
    table for table in catalog if selected_source == ALL_SOURCES or _source_display_name(table.source_type) == selected_source
]
database_options = [ALL_DATABASES] + sorted({table.database_name for table in source_scoped_catalog})
with database_column:
    selected_database = _selectbox_with_reset("Database", database_options, "catalog_database_filter")

database_scoped_catalog = [
    table
    for table in source_scoped_catalog
    if selected_database == ALL_DATABASES or table.database_name == selected_database
]
schema_options = [ALL_SCHEMAS] + sorted({table.schema_name for table in database_scoped_catalog})
with schema_column:
    selected_schema = _selectbox_with_reset("Schema", schema_options, "catalog_schema_filter")
st.markdown("</div>", unsafe_allow_html=True)

filtered_catalog = _filter_catalog(catalog, search_query, selected_source, selected_database, selected_schema)

st.markdown('<div class="section-kicker">CATALOG RESULTS</div>', unsafe_allow_html=True)
if not filtered_catalog:
    render_empty_state("No matching datasets", "Adjust the search text or filters to find cataloged metadata.", "search")
    st.stop()

render_html_table(
    _catalog_rows(filtered_catalog),
    table_id="catalog-results",
    download_filename="catalog_results.csv",
)

selected_dataset_by_identity = {_dataset_identity(table): table for table in filtered_catalog}
dataset_options = list(selected_dataset_by_identity)
if st.session_state.get("catalog_selected_dataset") not in dataset_options:
    st.session_state["catalog_selected_dataset"] = dataset_options[0]

selected_dataset_identity = st.selectbox(
    "Select dataset",
    dataset_options,
    key="catalog_selected_dataset",
    format_func=lambda identity: _dataset_label(selected_dataset_by_identity[identity]),
)
selected_dataset = selected_dataset_by_identity[selected_dataset_identity]

_render_selected_dataset_documentation(selected_dataset)
