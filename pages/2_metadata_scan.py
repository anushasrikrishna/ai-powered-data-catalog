from __future__ import annotations

from typing import Any

import streamlit as st

from auth.session import current_user_id, require_authenticated
from connectors.exceptions import ConnectorError
from metadata.exceptions import MetadataError
from metadata.extractor import MetadataExtractor
from metadata.models import TableMetadata
from storage.repository import MetadataRepository
from ui.components import loading_indicator, render_empty_state, render_get_started_workflow, render_html_table, render_page_header
from ui.connection_workflow import (
    ConnectionWorkflowSelection,
    clear_preview,
    render_connected_metadata_selection,
    render_connected_sources_table,
    render_table_preview,
    run_table_preview,
    safe_connection_error,
    source_display_name,
)


require_authenticated()


SCAN_TARGET_STATE_KEY = "metadata_scan_target"
SCAN_RESULT_STATE_KEY = "metadata_scan_result"
SCAN_RESULT_TARGET_STATE_KEY = "metadata_scan_result_target"
SCAN_SAVED_STATE_KEY = "metadata_scan_saved"

SCAN_CLEAR_KEYS = (
    SCAN_TARGET_STATE_KEY,
    SCAN_RESULT_STATE_KEY,
    SCAN_RESULT_TARGET_STATE_KEY,
    SCAN_SAVED_STATE_KEY,
)


def _clear_scan_result() -> None:
    for key in SCAN_CLEAR_KEYS:
        st.session_state.pop(key, None)


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


def _column_display_rows(table_metadata: TableMetadata) -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []
    for column in sorted(table_metadata.columns, key=lambda item: item.ordinal_position):
        rows.append(
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
        )
    return rows


def _render_summary(title: str, items: list[tuple[str, str]]) -> None:
    st.markdown(f'<div class="section-kicker">{title}</div>', unsafe_allow_html=True)
    columns = st.columns(len(items))
    for column, (label, value) in zip(columns, items):
        with column:
            st.markdown(f"**{label}**")
            st.write(value)


def _scan_target(selection: ConnectionWorkflowSelection) -> dict[str, str]:
    return {
        "source_type": selection.source_type,
        "database_name": selection.database_name,
        "schema_name": selection.schema_name,
        "table_name": selection.table_name,
    }


def _target_is_complete(target: dict[str, str]) -> bool:
    return all(str(target.get(key, "")).strip() for key in ("source_type", "database_name", "schema_name", "table_name"))


def _scan_result_matches_target(target: dict[str, str]) -> bool:
    return (
        st.session_state.get(SCAN_RESULT_TARGET_STATE_KEY) == target
        and isinstance(st.session_state.get(SCAN_RESULT_STATE_KEY), TableMetadata)
    )


def _run_metadata_scan(selection: ConnectionWorkflowSelection) -> None:
    target = _scan_target(selection)
    if not _target_is_complete(target):
        st.error("Scan target is incomplete. Select a schema and table before scanning metadata.")
        return

    try:
        with loading_indicator("Scanning metadata..."):
            extractor = MetadataExtractor(selection.connector)
            result = extractor.extract_table_metadata(
                database_name=target["database_name"],
                schema_name=target["schema_name"],
                table_name=target["table_name"],
            )
            repository = MetadataRepository()
            repository.save_table_metadata(result, current_user_id())
        st.session_state[SCAN_TARGET_STATE_KEY] = target
        st.session_state[SCAN_RESULT_STATE_KEY] = result
        st.session_state[SCAN_RESULT_TARGET_STATE_KEY] = target
        st.session_state[SCAN_SAVED_STATE_KEY] = True
    except (ConnectorError, MetadataError) as exc:
        _clear_scan_result()
        st.error(
            f"Unable to scan metadata for {target.get('schema_name', '<schema>')}."
            f"{target.get('table_name', '<table>')}: {safe_connection_error(str(exc))}"
        )
    except Exception:
        if "result" in locals():
            st.session_state[SCAN_TARGET_STATE_KEY] = target
            st.session_state[SCAN_RESULT_STATE_KEY] = result
            st.session_state[SCAN_RESULT_TARGET_STATE_KEY] = target
            st.session_state[SCAN_SAVED_STATE_KEY] = False
            return
        _clear_scan_result()
        st.error(
            f"Unable to scan metadata for {target.get('schema_name', '<schema>')}."
            f"{target.get('table_name', '<table>')}. Verify table permissions and metadata access."
        )


def _render_scan_result(table_metadata: TableMetadata) -> None:
    st.markdown('<div class="section-kicker">SCAN RESULTS</div>', unsafe_allow_html=True)
    _render_summary(
        "TABLE OVERVIEW",
        [
            ("Source", source_display_name(table_metadata.source_type)),
            ("Database", table_metadata.database_name),
            ("Schema", table_metadata.schema_name),
            ("Table", table_metadata.table_name),
            ("Table Type", table_metadata.table_type),
            ("Row Count", _format_count(table_metadata.row_count)),
        ],
    )

    st.markdown('<div class="section-kicker">COLUMN METADATA</div>', unsafe_allow_html=True)
    column_rows = _column_display_rows(table_metadata)
    if column_rows:
        render_html_table(
            column_rows,
            table_id="scan-column-metadata",
            download_filename="scan_column_metadata.csv",
        )
    else:
        render_empty_state("No columns found", "The metadata scan returned no column metadata.", "catalog")


render_page_header(
    "Metadata Scan",
    "Inspect and standardize metadata from connected data sources.",
    "Connect, preview and scan a table into the persisted metadata catalog.",
    icon="search",
)

render_get_started_workflow(
    [
        ("database", "CONNECT"),
        ("search", "SELECT"),
        ("quality", "SCAN"),
        ("catalog", "CATALOG"),
    ],
    class_name="get-started-workflow metadata-scan-workflow",
)

render_connected_sources_table()
st.markdown('<div class="section-kicker">SELECT DATABASE</div>', unsafe_allow_html=True)
selection = render_connected_metadata_selection(extra_clear_keys=SCAN_CLEAR_KEYS)

if selection is not None:
    action_columns = st.columns([1, 1, 4])
    with action_columns[0]:
        if st.button(
            "Preview Table",
            icon=":material/visibility:",
            key="metadata_scan_preview_button",
            use_container_width=True,
        ):
            _clear_scan_result()
            run_table_preview(selection)
    with action_columns[1]:
        if st.button(
            "Scan Metadata",
            type="primary",
            icon=":material/manage_search:",
            key="metadata_scan_scan_button",
            use_container_width=True,
        ):
            clear_preview()
            _run_metadata_scan(selection)

    render_table_preview(selection)

    scan_target = _scan_target(selection)
    if _scan_result_matches_target(scan_target):
        if st.session_state.get(SCAN_SAVED_STATE_KEY) is True:
            st.success("Metadata scanned and saved successfully.")
        elif st.session_state.get(SCAN_SAVED_STATE_KEY) is False:
            st.warning("Metadata scan completed, but the result could not be saved.")
        _render_scan_result(st.session_state[SCAN_RESULT_STATE_KEY])
