from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

from auth.session import current_user_id, require_authenticated
from documentation import MetadataDocumentationGenerator
from documentation.models import TableDocumentation
from catalog.repository import CatalogEntry, CatalogRepository
from catalog.search import CatalogFilters, CatalogSearch, CatalogSearchResult
from metadata.models import TableMetadata
from storage.repository import MetadataRepository
from storage.scan_history import ScanComparison, ScanSnapshot, compare_snapshots
from ui.components import (
    render_count_chips,
    render_empty_state,
    render_html_table,
    render_page_header,
    render_workspace_status,
)
from ui.page_state import load_widget_state, store_widget_state
from ui.metadata_trends import build_dataset_growth_trend_svg, build_schema_evolution_trend_svg


require_authenticated()


ALL_SOURCES = "All Sources"
ALL_DATABASES = "All Databases"
ALL_SCHEMAS = "All Schemas"
CHOOSE_DATASET = "Choose a dataset"
CATALOG_SELECTED_DATASET_KEY = "catalog_selected_dataset"
CATALOG_DETAIL_KEY = "catalog_selected_dataset_detail"
CATALOG_SEARCH_KEY = "catalog_search"
CATALOG_SOURCE_KEY = "catalog_source"
CATALOG_DATABASE_KEY = "catalog_database"
CATALOG_SCHEMA_KEY = "catalog_schema"
CATALOG_SEARCH_WIDGET_KEY = "_catalog_search_widget"
CATALOG_SOURCE_WIDGET_KEY = "_catalog_source_widget"
CATALOG_DATABASE_WIDGET_KEY = "_catalog_database_widget"
CATALOG_SCHEMA_WIDGET_KEY = "_catalog_schema_widget"
CATALOG_DATASET_WIDGET_KEY = "_catalog_dataset_widget"
CATALOG_LAST_SOURCE_KEY = "catalog_last_source"
CATALOG_LAST_DATABASE_KEY = "catalog_last_database"
CATALOG_LAST_SCHEMA_KEY = "catalog_last_schema"

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
        return repository.list_tables(current_user_id()), None
    except Exception as exc:
        return [], exc


def _catalog_entry(table_metadata: TableMetadata) -> CatalogEntry:
    documentation = MetadataDocumentationGenerator().generate(table_metadata)
    return CatalogEntry.from_documentation(documentation)


def _build_catalog_search(
    catalog: list[TableMetadata],
) -> tuple[CatalogSearch, dict[str, TableMetadata]]:
    entries = [_catalog_entry(table_metadata) for table_metadata in catalog]
    repository = CatalogRepository(entries)
    metadata_by_dataset_id = {
        entry.dataset_id: table_metadata
        for entry, table_metadata in zip(entries, catalog)
    }
    return CatalogSearch(repository), metadata_by_dataset_id


def _selectbox_with_persistence(label: str, options: list[str], permanent_key: str, widget_key: str) -> str:
    load_widget_state(st.session_state, permanent_key, widget_key, options[0], options)
    return st.selectbox(
        label,
        options,
        key=widget_key,
        on_change=store_widget_state,
        args=(st.session_state, permanent_key, widget_key),
    )


def _render_catalog_summary(catalog: list[TableMetadata]) -> None:
    source_count = len({_source_display_name(table.source_type) for table in catalog})
    database_count = len({table.database_name for table in catalog})
    column_count = sum(len(table.columns) for table in catalog)

    with st.container(key="catalog-summary-grid"):
        render_workspace_status(
            [
                ("catalog", "Cataloged Datasets", f"{len(catalog):,}", "Available in catalog"),
                ("database", "Sources", f"{source_count:,}", "Source platforms"),
                ("dashboard", "Databases", f"{database_count:,}", "Database contexts"),
                ("search", "Total Columns", f"{column_count:,}", "Cataloged columns"),
            ],
            compact=True,
            show_detail=False,
            decorations=["data-grid", "data-nodes", "data-nodes", "data-grid"],
        )


def _catalog_rows(results: list[CatalogSearchResult]) -> list[dict[str, str | int]]:
    return [
        {
            "Source": _source_display_name(result.entry.documentation.source_type),
            "Database": result.entry.documentation.database_name,
            "Schema": result.entry.documentation.schema_name,
            "Table": result.entry.documentation.table_name,
            "Type": result.entry.documentation.table_type,
            "Rows": _format_count(result.entry.documentation.summary.row_count),
            "Columns": result.entry.documentation.summary.column_count,
        }
        for result in results
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


def _render_documentation_summary_cards(documentation: TableDocumentation) -> None:
    summary = documentation.summary
    render_workspace_status(
        [
            ("dashboard", "Rows", _format_count(summary.row_count), "Source records"),
            ("catalog", "Columns", f"{summary.column_count:,}", "Documented fields"),
            ("search", "Nullable", f"{summary.nullable_column_count:,}", "Allow null values"),
            ("quality", "Non-Nullable", f"{summary.non_nullable_column_count:,}", "Required fields"),
        ],
        decorations=["data-grid", "data-grid", "data-nodes", "quality-signal"],
    )

def _render_documentation_breakdowns(documentation: TableDocumentation) -> None:
    summary = documentation.summary
    st.markdown('<div class="documentation-summary-gap" aria-hidden="true"></div>', unsafe_allow_html=True)
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
    distribution_column, classification_column = st.columns(2, gap="large")
    with distribution_column:
        render_count_chips("DATA TYPE DISTRIBUTION", meaningful_counts, footer="Column types across this dataset", decoration="data-grid")

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
    with classification_column:
        render_count_chips(
            "COLUMN CLASSIFICATIONS",
            [(category, category_counts[category]) for category in category_order if category_counts[category]],
            kind="category",
            footer="Detected column categories",
            decoration="data-nodes",
        )


def _format_timestamp(value: str) -> str:
    try:
        from datetime import datetime

        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone().strftime("%d %b %Y %H:%M")
    except ValueError:
        return value


def _signed_count(value: int | None) -> str:
    if value is None:
        return "—"
    return f"{value:+,}"


def _signed_percent(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:+.2f}%"


def _render_dataset_evolution(comparison: ScanComparison) -> None:
    st.markdown('<div class="documentation-subsection-title">DATASET EVOLUTION</div>', unsafe_allow_html=True)
    st.caption(
        f"Current Scan: {_format_timestamp(comparison.current.scanned_at)} · "
        f"Compared With: {_format_timestamp(comparison.previous.scanned_at)}"
    )
    render_workspace_status(
        [
            ("dashboard", "Previous Rows", _format_count(comparison.previous.row_count), "Previous scan"),
            ("dashboard", "Current Rows", _format_count(comparison.current.row_count), "Latest scan"),
            ("quality", "Net Row Change", _signed_count(comparison.net_row_change), "Current minus previous"),
            ("search", "Data Growth %", _signed_percent(comparison.growth_percent), "Compared with previous"),
            ("catalog", "Column Change", _signed_count(comparison.column_change), "Current minus previous"),
            ("quality", "Schema Changes", f"{comparison.schema_change_count:,}", "Added, removed, or modified"),
        ],
        compact=True,
        show_detail=True,
        decorations=["data-grid", "data-grid", "quality-signal", "quality-signal", "data-nodes", "data-grid"],
    )


def _render_evolution_trends(history: list[ScanSnapshot]) -> None:
    chronological = list(reversed(history))
    growth_points: list[tuple[str, int | None, int | None, float | None]] = []
    schema_points: list[tuple[str, int, int | None, int, int, int]] = []
    for index, snapshot in enumerate(chronological):
        comparison = compare_snapshots(chronological[index - 1], snapshot) if index else None
        growth_points.append(
            (_format_timestamp(snapshot.scanned_at), snapshot.row_count,
             comparison.net_row_change if comparison else None,
             comparison.growth_percent if comparison else None)
        )
        schema_points.append(
            (_format_timestamp(snapshot.scanned_at), snapshot.column_count,
             comparison.schema_change_count if comparison else None,
             len(comparison.added_columns) if comparison else 0,
             len(comparison.removed_columns) if comparison else 0,
             (len(comparison.type_changes) + len(comparison.nullability_changes) if comparison else 0))
        )
    growth_svg = build_dataset_growth_trend_svg(growth_points)
    schema_svg = build_schema_evolution_trend_svg(schema_points)
    if not growth_svg or not schema_svg:
        return
    st.markdown('<div class="documentation-subsection-title">EVOLUTION TRENDS</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="metadata-evolution-trends">'
        f'<section class="metadata-evolution-trend-card"><div class="metadata-evolution-trend-title">'
        f'DATASET GROWTH TREND</div>{growth_svg}</section>'
        f'<section class="metadata-evolution-trend-card"><div class="metadata-evolution-trend-title">'
        f'SCHEMA EVOLUTION</div>{schema_svg}</section></div>',
        unsafe_allow_html=True,
    )


def _change_summary_rows(comparison: ScanComparison) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    rows.extend({"Change": "COLUMN ADDED", "Column": name, "Details": "+ Added"} for name in comparison.added_columns)
    rows.extend({"Change": "COLUMN REMOVED", "Column": name, "Details": "− Removed"} for name in comparison.removed_columns)
    rows.extend(
        {"Change": "DATA TYPE CHANGED", "Column": item["column"], "Details": f'{item["from"]} → {item["to"]}'}
        for item in comparison.type_changes
    )
    rows.extend(
        {"Change": "NULLABILITY CHANGED", "Column": item["column"], "Details": f'{item["from"]} → {item["to"]}'}
        for item in comparison.nullability_changes
    )
    rows.extend(
        {"Change": "NULL COUNT CHANGED", "Column": item["column"], "Details": f'{item["from"]} → {item["to"]}'}
        for item in comparison.null_count_changes
    )
    rows.extend(
        {"Change": "DISTINCT COUNT CHANGED", "Column": item["column"], "Details": f'{item["from"]} → {item["to"]}'}
        for item in comparison.distinct_count_changes
    )
    return rows


def _render_change_summary(comparison: ScanComparison) -> None:
    rows = _change_summary_rows(comparison)
    st.markdown('<div class="documentation-subsection-title">CHANGE SUMMARY</div>', unsafe_allow_html=True)
    if not rows:
        st.caption("No metadata or schema changes detected between the latest scans.")
        return
    render_html_table(rows, table_id="catalog-change-summary", download_filename="catalog_change_summary.csv")


def _render_scan_history(history: list[ScanSnapshot]) -> None:
    st.markdown('<div class="documentation-subsection-title">SCAN HISTORY</div>', unsafe_allow_html=True)
    rows: list[dict[str, str | int]] = []
    for index, snapshot in enumerate(history):
        comparison = compare_snapshots(history[index + 1], snapshot) if index + 1 < len(history) else None
        rows.append(
            {
                "Scan Date": _format_timestamp(snapshot.scanned_at),
                "Rows": _format_count(snapshot.row_count),
                "Columns": snapshot.column_count,
                "Net Change": _signed_count(comparison.net_row_change if comparison else None),
                "Growth": _signed_percent(comparison.growth_percent if comparison else None),
                "Schema Changes": comparison.schema_change_count if comparison else "—",
            }
        )
    render_html_table(
        rows,
        table_id="catalog-scan-history",
        download_filename="catalog_scan_history.csv",
        column_widths=[28, 12, 12, 14, 14, 20],
        max_visible_rows=5,
        sticky_header=True,
        scrollable=True,
    )


def _render_ranking_explanation(result: CatalogSearchResult) -> None:
    with st.expander("WHY THIS RESULT MATCHED", expanded=True):
        st.markdown(
            f'<div class="ranking-score"><span>Relevance Score</span><strong>{result.score}</strong></div>',
            unsafe_allow_html=True,
        )

        if result.matched_fields:
            fields = "".join(
                f'<span class="ranking-chip">{escape(field)}</span>' for field in result.matched_fields
            )
            st.markdown(f"**Matched Fields**<div class=\"ranking-chips\">{fields}</div>", unsafe_allow_html=True)

        if result.matched_terms:
            terms = "".join(
                f'<span class="ranking-chip ranking-chip--accent">{escape(term)}</span>'
                for term in result.matched_terms
            )
            st.markdown(f"**Matched Terms**<div class=\"ranking-chips\">{terms}</div>", unsafe_allow_html=True)

        contributions = [(name, value) for name, value in result.score_breakdown.items() if value]
        if contributions:
            breakdown = "".join(
                f'<div class="ranking-breakdown-row"><span>{escape(name)}</span><strong>{value}</strong></div>'
                for name, value in contributions
            )
            st.markdown(
                f"**Score Breakdown**<div class=\"ranking-breakdown\">{breakdown}</div>",
                unsafe_allow_html=True,
            )


def _render_selected_dataset_documentation(
    table_metadata: TableMetadata,
    documentation: TableDocumentation | None = None,
    scan_history: list[ScanSnapshot] | None = None,
) -> None:
    if scan_history is None:
        scan_history = MetadataRepository().list_scan_history(
            table_metadata.source_type,
            table_metadata.database_name,
            table_metadata.schema_name,
            table_metadata.table_name,
            current_user_id(),
        )
    if documentation is None:
        try:
            documentation = MetadataDocumentationGenerator().generate(table_metadata)
        except Exception:
            st.warning("Unable to generate dataset documentation.")

    if documentation is not None:
        st.markdown('<div class="section-kicker">DOCUMENTATION</div>', unsafe_allow_html=True)
        st.markdown('<div class="documentation-subsection-title">TECHNICAL SUMMARY</div>', unsafe_allow_html=True)
        _render_documentation_summary_cards(documentation)
        if len(scan_history) >= 2:
            comparison = compare_snapshots(scan_history[1], scan_history[0])
            _render_dataset_evolution(comparison)
            _render_evolution_trends(scan_history)
            _render_change_summary(comparison)
        _render_documentation_breakdowns(documentation)
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

    if len(scan_history) >= 2:
        _render_scan_history(scan_history)


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

try:
    catalog_search, metadata_by_dataset_id = _build_catalog_search(catalog)
except Exception:
    st.error("Unable to prepare the metadata catalog for search.")
    st.stop()

_render_catalog_summary(catalog)

with st.container(key="catalog-filter-row"):
    search_column, source_column, database_column, schema_column = st.columns([2, 1, 1, 1], gap="medium")

    with search_column:
        load_widget_state(st.session_state, CATALOG_SEARCH_KEY, CATALOG_SEARCH_WIDGET_KEY, "")
        search_query = st.text_input(
            "Search catalog",
            placeholder="Search by source, database, schema, table or column",
            key=CATALOG_SEARCH_WIDGET_KEY,
            on_change=store_widget_state,
            args=(st.session_state, CATALOG_SEARCH_KEY, CATALOG_SEARCH_WIDGET_KEY),
        ).strip()

    source_options = [ALL_SOURCES] + sorted({_source_display_name(table.source_type) for table in catalog})
    with source_column:
        selected_source = _selectbox_with_persistence("Source", source_options, CATALOG_SOURCE_KEY, CATALOG_SOURCE_WIDGET_KEY)
        previous_source = st.session_state.get(CATALOG_LAST_SOURCE_KEY)
        if previous_source is not None and selected_source != previous_source:
            for key in (
                CATALOG_DATABASE_KEY,
                CATALOG_SCHEMA_KEY,
                CATALOG_SELECTED_DATASET_KEY,
                CATALOG_DETAIL_KEY,
                CATALOG_DATABASE_WIDGET_KEY,
                CATALOG_SCHEMA_WIDGET_KEY,
                CATALOG_DATASET_WIDGET_KEY,
            ):
                st.session_state.pop(key, None)
        st.session_state[CATALOG_LAST_SOURCE_KEY] = selected_source

    source_scoped_catalog = [
        table for table in catalog if selected_source == ALL_SOURCES or _source_display_name(table.source_type) == selected_source
    ]
    database_options = [ALL_DATABASES] + sorted({table.database_name for table in source_scoped_catalog})
    with database_column:
        selected_database = _selectbox_with_persistence("Database", database_options, CATALOG_DATABASE_KEY, CATALOG_DATABASE_WIDGET_KEY)
        previous_database = st.session_state.get(CATALOG_LAST_DATABASE_KEY)
        if previous_database is not None and selected_database != previous_database:
            for key in (CATALOG_SCHEMA_KEY, CATALOG_SELECTED_DATASET_KEY, CATALOG_DETAIL_KEY, CATALOG_SCHEMA_WIDGET_KEY, CATALOG_DATASET_WIDGET_KEY):
                st.session_state.pop(key, None)
        st.session_state[CATALOG_LAST_DATABASE_KEY] = selected_database

    database_scoped_catalog = [
        table
        for table in source_scoped_catalog
        if selected_database == ALL_DATABASES or table.database_name == selected_database
    ]
    schema_options = [ALL_SCHEMAS] + sorted({table.schema_name for table in database_scoped_catalog})
    with schema_column:
        selected_schema = _selectbox_with_persistence("Schema", schema_options, CATALOG_SCHEMA_KEY, CATALOG_SCHEMA_WIDGET_KEY)
        previous_schema = st.session_state.get(CATALOG_LAST_SCHEMA_KEY)
        if previous_schema is not None and selected_schema != previous_schema:
            for key in (CATALOG_SELECTED_DATASET_KEY, CATALOG_DETAIL_KEY, CATALOG_DATASET_WIDGET_KEY):
                st.session_state.pop(key, None)
        st.session_state[CATALOG_LAST_SCHEMA_KEY] = selected_schema
source_filter = None
if selected_source != ALL_SOURCES:
    source_filter = [
        table.source_type
        for table in catalog
        if _source_display_name(table.source_type) == selected_source
    ]

try:
    search_results = catalog_search.search(
        search_query,
        filters=CatalogFilters(
            source_type=source_filter,
            database_name=None if selected_database == ALL_DATABASES else selected_database,
            schema_name=None if selected_schema == ALL_SCHEMAS else selected_schema,
        ),
    )
except Exception:
    st.error("Unable to search the metadata catalog.")
    st.stop()

search_results = sorted(
    search_results,
    key=lambda result: str(getattr(metadata_by_dataset_id[result.dataset_id], "scanned_at", "") or ""),
    reverse=True,
)

st.markdown('<div class="section-kicker">CATALOG RESULTS</div>', unsafe_allow_html=True)
if not search_results:
    st.session_state.pop(CATALOG_SELECTED_DATASET_KEY, None)
    st.session_state.pop(CATALOG_DETAIL_KEY, None)
    render_empty_state(
        "No datasets match your search and filters.",
        "Clear the search or adjust the selected filters to browse cataloged metadata.",
        "search",
    )
    st.stop()

render_html_table(
    _catalog_rows(search_results),
    table_id="catalog-results",
    download_filename="catalog_results.csv",
    max_visible_rows=5,
    sticky_header=True,
    scrollable=True,
)

selected_dataset_by_identity = {
    result.dataset_id: metadata_by_dataset_id[result.dataset_id]
    for result in search_results
}
dataset_options = [result.dataset_id for result in search_results]
dataset_options = [CHOOSE_DATASET] + dataset_options
restored_catalog_dataset = st.session_state.get(CATALOG_DETAIL_KEY) or st.session_state.get(CATALOG_SELECTED_DATASET_KEY)
if st.session_state.get(CATALOG_SELECTED_DATASET_KEY) not in dataset_options:
    st.session_state[CATALOG_SELECTED_DATASET_KEY] = (
        restored_catalog_dataset if restored_catalog_dataset in selected_dataset_by_identity else CHOOSE_DATASET
    )

load_widget_state(
    st.session_state,
    CATALOG_SELECTED_DATASET_KEY,
    CATALOG_DATASET_WIDGET_KEY,
    CHOOSE_DATASET,
    dataset_options,
)
selected_dataset_identity = st.selectbox(
    "Select dataset",
    dataset_options,
    key=CATALOG_DATASET_WIDGET_KEY,
    on_change=store_widget_state,
    args=(st.session_state, CATALOG_SELECTED_DATASET_KEY, CATALOG_DATASET_WIDGET_KEY),
    format_func=lambda identity: CHOOSE_DATASET if identity == CHOOSE_DATASET else _dataset_label(selected_dataset_by_identity[identity]),
)

if selected_dataset_identity == CHOOSE_DATASET:
    st.session_state.pop(CATALOG_DETAIL_KEY, None)
    st.caption("Choose a dataset to view its documentation and ranking explanation.")
    st.stop()

selected_dataset = selected_dataset_by_identity[selected_dataset_identity]
selected_result = {result.dataset_id: result for result in search_results}[selected_dataset_identity]
st.session_state[CATALOG_DETAIL_KEY] = selected_dataset_identity

if search_query:
    _render_ranking_explanation(selected_result)

_render_selected_dataset_documentation(selected_dataset, selected_result.entry.documentation)
