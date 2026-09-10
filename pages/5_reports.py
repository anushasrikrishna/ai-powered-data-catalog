from __future__ import annotations

from datetime import datetime
from html import escape

import streamlit as st

from auth.session import current_user_id, require_authenticated
from documentation import MetadataDocumentationGenerator
from metadata.models import TableMetadata
from storage.quality_repository import QualityRunRepository, StoredQualityRun
from storage.repository import MetadataRepository
from storage.scan_history import compare_snapshots
from ui.components import render_count_chips, render_get_started_workflow, render_html_table, render_page_header, render_workspace_status
from ui.report_export import build_export_filename, render_html_report, render_markdown_report, render_pdf_report
from ui.report_view import CatalogReportContext, build_catalog_report_context, build_column_profiles, build_metadata_summary, build_report_context, failed_results, format_profile_value, quality_health
from ui.quality_trend import build_quality_trend_svg
from ui.metadata_trends import build_dataset_growth_trend_svg, build_schema_evolution_trend_svg
from ui.page_state import load_widget_state, store_widget_state


require_authenticated()


REPORT_DATASET_KEY = "reports_selected_dataset"
REPORT_RUN_KEY = "reports_selected_run"
REPORT_PREVIEW_KEY = "reports_preview_context"
REPORT_PREVIEW_DATASET_KEY = "reports_preview_dataset"
REPORT_PREVIEW_RUN_KEY = "reports_preview_run"
REPORT_DATASET_WIDGET_KEY = "_reports_dataset_widget"
REPORT_RUN_WIDGET_KEY = "_reports_quality_run_widget"
REPORT_TYPE_KEY = "reports_report_type"
REPORT_CATALOG_DATASET_KEY = "reports_catalog_dataset"
REPORT_CATALOG_DATASET_WIDGET_KEY = "_reports_catalog_dataset_widget"
REPORT_TYPE_QUALITY = "Data Quality Report"
REPORT_TYPE_CATALOG = "Data Catalog Report"
CHOOSE_DATASET = "Choose a dataset"
CHOOSE_RUN = "Choose a quality run"


def _dataset_id(table: TableMetadata) -> str:
    return "|".join(part.strip().lower() for part in (table.source_type, table.database_name, table.schema_name, table.table_name))


def _source_name(source_type: str) -> str:
    return {"sqlserver": "SQL Server", "postgresql": "PostgreSQL", "snowflake": "Snowflake"}.get(source_type.strip().lower(), source_type)


def _dataset_label(table: TableMetadata) -> str:
    return f"{_source_name(table.source_type)} / {table.database_name} / {table.schema_name} / {table.table_name}"


def _history_timestamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone().strftime("%d %b %Y, %I:%M %p").lstrip("0")
    except (TypeError, ValueError):
        return value


def _scan_history_timestamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone().strftime("%d %b %Y %H:%M")
    except (TypeError, ValueError):
        return value


def _scan_history_growth(value: float | None) -> str:
    return "—" if value is None else f"{value:+.2f}%"


def _run_label(run: StoredQualityRun) -> str:
    score = "—" if run.report.quality_score is None else f"{run.report.quality_score:g}%"
    return f"{_history_timestamp(run.executed_at)} · Score {score} · {run.report.total_rules:,} checks"


def _quality_rule_label(rule_type: str) -> str:
    return {"not_null": "Not Null", "unique": "Unique", "duplicate": "Duplicate", "accepted_values": "Accepted Values", "numeric_range": "Numeric Range", "string_length": "String Length", "freshness": "Freshness"}.get(rule_type, rule_type.replace("_", " ").title())


def _format_percent(value: float) -> str:
    return f"{value:g}%"


def _quality_status_cell(value: object, _row: dict[object, object]) -> str:
    status = str(value)
    return f'<span class="quality-result-status quality-result-status--{status.casefold()}">{escape(status)}</span>'


def _format_value(value: object) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.2%}"
    return str(value)


def _render_dataset_overview(documentation: object, latest_scan: str | None = None) -> None:
    fields = [
        ("Source", _source_name(documentation.source_type)),
        ("Database", documentation.database_name),
        ("Schema", documentation.schema_name),
        ("Table", documentation.table_name),
        ("Rows", "—" if documentation.summary.row_count is None else f"{documentation.summary.row_count:,}"),
        ("Columns", f"{documentation.summary.column_count:,}"),
    ]
    if latest_scan:
        fields.append(("Latest Scan", _history_timestamp(latest_scan)))
    columns = st.columns(len(fields))
    for column, (label, value) in zip(columns, fields):
        with column:
            decoration = "data-nodes" if label in {"Source", "Database"} else "data-grid"
            st.markdown(f'<div class="quality-context-item card-decoration-{decoration}"><div class="card-content"><span>{escape(label)}</span><strong>{escape(value)}</strong></div></div>', unsafe_allow_html=True)


def _render_metadata_summary(documentation: object) -> None:
    summary = build_metadata_summary(documentation)
    st.markdown('<div class="section-kicker reports-section-kicker">METADATA SUMMARY</div>', unsafe_allow_html=True)
    render_workspace_status([
        ("catalog", "Total Columns", f"{summary.total_columns:,}", "Persisted metadata"),
        ("quality", "Required Columns", f"{summary.non_nullable_columns:,}", "Non-nullable columns"),
        ("catalog", "Nullable Columns", f"{summary.nullable_columns:,}", "Allow null values"),
        ("quality", "Numeric Columns", f"{summary.numeric_columns:,}", "Number and decimal types"),
        ("report", "Date / Datetime", f"{summary.date_datetime_columns:,}", "Date and datetime types"),
    ], compact=True, show_detail=False, decorations=["data-grid", "quality-signal", "data-nodes", "data-grid", "data-nodes"])
    st.markdown('<div class="section-kicker reports-section-kicker">COLUMN PROFILE</div>', unsafe_allow_html=True)
    profile_rows = build_column_profiles(documentation)
    if not profile_rows:
        st.info("No column profile is available for this dataset.")
        return
    render_html_table(
        profile_rows,
        table_id="reports-column-profile",
        download=False,
        column_widths=[18, 13, 10, 12, 13, 12, 11, 11],
        table_class="quality-result-table",
        cell_renderers={
            "Column": lambda value, _row: f'<span class="html-table-column-name">{escape(str(value))}</span>',
            "Distinct Ratio": lambda value, _row: f'<span class="html-table-secondary">{escape(_format_value(value))}</span>',
            "Min": lambda value, row: f'<span class="html-table-secondary">{escape(format_profile_value(value, row.get("Type", "")))}</span>',
            "Max": lambda value, row: f'<span class="html-table-secondary">{escape(format_profile_value(value, row.get("Type", "")))}</span>',
        },
    )


def _render_failed_checks(report: object) -> None:
    failures = failed_results(report)
    st.markdown('<div class="section-kicker reports-section-kicker">FAILED CHECKS</div>', unsafe_allow_html=True)
    if not failures:
        st.info("No failed or error checks in this run.")
        return
    failed_occurrences = sum(result.failed_records for result in failures)
    render_workspace_status([
        ("quality", "Failed Checks", f"{report.failed_rules:,}", "Persisted FAIL results"),
        ("quality", "Error Checks", f"{report.error_rules:,}", "Persisted ERROR results"),
        ("quality", "Failed Record Occurrences", f"{failed_occurrences:,}", "May overlap across rules"),
    ], compact=True, show_detail=False)
    rows = [
        {
            "Rule": _quality_rule_label(result.rule_type),
            "Column / Scope": result.column,
            "Status": result.status,
            "Failed Records": "—" if result.status == "ERROR" else f"{result.failed_records:,}",
            "Failure %": _format_percent(result.failure_percentage),
            "Message": result.error_message or "—",
        }
        for result in failures
    ]
    render_html_table(
        rows,
        table_id="reports-failed-checks",
        download=False,
        column_widths=[16, 19, 12, 15, 13, 25],
        table_class="quality-result-table",
        cell_renderers={
            "Rule": lambda value, _row: f'<span class="html-table-badge html-table-badge--rule">{escape(str(value))}</span>',
            "Column / Scope": lambda value, _row: f'<span class="html-table-column-name">{escape(str(value))}</span>',
            "Status": _quality_status_cell,
            "Message": lambda value, _row: f'<span class="html-table-secondary">{escape(str(value))}</span>',
        },
    )


def _catalog_history_rows(context: CatalogReportContext) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for index, snapshot in enumerate(context.scan_history):
        comparison = compare_snapshots(context.scan_history[index + 1], snapshot) if index + 1 < len(context.scan_history) else None
        rows.append({
            "Scan Date": _scan_history_timestamp(snapshot.scanned_at),
            "Rows": "—" if snapshot.row_count is None else f"{snapshot.row_count:,}",
            "Columns": snapshot.column_count,
            "Net Change": "—" if comparison is None else f"{comparison.net_row_change:+,}",
            "Growth": "—" if comparison is None else _scan_history_growth(comparison.growth_percent),
            "Schema Changes": "—" if comparison is None else comparison.schema_change_count,
        })
    return rows


def _render_catalog_report_preview(context: CatalogReportContext) -> None:
    documentation = context.documentation
    summary = documentation.summary
    st.markdown('<div class="section-kicker reports-preview-heading">REPORT PREVIEW</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-kicker reports-section-kicker">DATASET OVERVIEW</div>', unsafe_allow_html=True)
    _render_dataset_overview(documentation, context.scan_history[0].scanned_at if context.scan_history else None)

    st.markdown('<div class="section-kicker reports-section-kicker">METADATA SUMMARY</div>', unsafe_allow_html=True)
    metadata = build_metadata_summary(documentation)
    render_workspace_status([
        ("catalog", "Total Columns", f"{metadata.total_columns:,}", "Persisted metadata"),
        ("quality", "Required Columns", f"{metadata.non_nullable_columns:,}", "Non-nullable columns"),
        ("catalog", "Nullable Columns", f"{metadata.nullable_columns:,}", "Allow null values"),
        ("quality", "Numeric Columns", f"{metadata.numeric_columns:,}", "Number and decimal types"),
        ("report", "Date / Datetime", f"{metadata.date_datetime_columns:,}", "Date and datetime types"),
    ], compact=True, show_detail=False, decorations=["data-grid", "quality-signal", "data-nodes", "data-grid", "data-nodes"])

    render_count_chips("DATA TYPE DISTRIBUTION", [(label, count) for label, count in [
        ("Number", summary.number_column_count), ("Decimal", summary.decimal_column_count),
        ("String", summary.string_column_count), ("Date", summary.date_column_count),
        ("Datetime", summary.datetime_column_count), ("Boolean", summary.boolean_column_count),
        ("Binary", summary.binary_column_count), ("Other", summary.other_column_count)] if count], decoration="data-grid")
    categories: dict[str, int] = {}
    for column in documentation.columns:
        categories[column.possible_category] = categories.get(column.possible_category, 0) + 1
    render_count_chips("COLUMN CLASSIFICATIONS", sorted(categories.items()), kind="category", decoration="data-nodes")

    st.markdown('<div class="section-kicker reports-section-kicker">COLUMN METADATA</div>', unsafe_allow_html=True)
    column_rows = [{
        "Column": column.column_name, "Source Type": column.source_data_type,
        "Normalized Type": column.normalized_data_type, "Possible Category": column.possible_category,
        "Nullable": "Yes" if column.nullable else "No", "Position": column.ordinal_position,
        "Null Count": column.null_count, "Distinct Count": column.distinct_count,
        "Minimum": format_profile_value(column.minimum, column.normalized_data_type),
        "Maximum": format_profile_value(column.maximum, column.normalized_data_type),
    } for column in documentation.columns]
    if column_rows:
        render_html_table(column_rows, table_id="reports-catalog-column-metadata", download=False,
                          column_widths=[14, 12, 13, 14, 8, 8, 9, 10, 6, 6])

    if context.comparison is not None:
        comparison = context.comparison
        chronological = list(reversed(context.scan_history))
        growth_points = []
        schema_points = []
        for index, snapshot in enumerate(chronological):
            prior = compare_snapshots(chronological[index - 1], snapshot) if index else None
            growth_points.append((_history_timestamp(snapshot.scanned_at), snapshot.row_count, prior.net_row_change if prior else None, prior.growth_percent if prior else None))
            schema_points.append((_history_timestamp(snapshot.scanned_at), snapshot.column_count, prior.schema_change_count if prior else None, len(prior.added_columns) if prior else 0, len(prior.removed_columns) if prior else 0, (len(prior.type_changes) + len(prior.nullability_changes)) if prior else 0))
        growth_svg = build_dataset_growth_trend_svg(growth_points)
        schema_svg = build_schema_evolution_trend_svg(schema_points)
        if growth_svg and schema_svg:
            st.markdown('<div class="section-kicker reports-section-kicker">EVOLUTION TRENDS</div>', unsafe_allow_html=True)
            trend_columns = st.columns(2, gap="large")
            with trend_columns[0]:
                st.markdown(f'<div class="quality-visual-panel"><div class="quality-history-panel-title">DATASET GROWTH TREND</div>{growth_svg}</div>', unsafe_allow_html=True)
            with trend_columns[1]:
                st.markdown(f'<div class="quality-visual-panel"><div class="quality-history-panel-title">SCHEMA EVOLUTION</div>{schema_svg}</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-kicker reports-section-kicker">DATASET EVOLUTION</div>', unsafe_allow_html=True)
        render_workspace_status([
            ("dashboard", "Previous Rows", "—" if comparison.previous.row_count is None else f"{comparison.previous.row_count:,}", "Previous scan"),
            ("dashboard", "Current Rows", "—" if comparison.current.row_count is None else f"{comparison.current.row_count:,}", "Latest scan"),
            ("quality", "Net Row Change", f"{comparison.net_row_change:+,}", "Current minus previous"),
            ("search", "Data Growth %", _format_percent(comparison.growth_percent), "Compared with previous"),
            ("catalog", "Column Change", f"{comparison.column_change:+,}", "Current minus previous"),
            ("quality", "Schema Changes", f"{comparison.schema_change_count:,}", "Added, removed, or modified"),
        ], compact=True, show_detail=True, decorations=["data-grid", "data-grid", "quality-signal", "quality-signal", "data-nodes", "data-grid"])
        st.markdown('<div class="section-kicker reports-section-kicker">CHANGE SUMMARY</div>', unsafe_allow_html=True)
        change_rows = [{"Change": "COLUMN ADDED", "Column": name, "Details": "+ Added"} for name in comparison.added_columns]
        change_rows += [{"Change": "COLUMN REMOVED", "Column": name, "Details": "- Removed"} for name in comparison.removed_columns]
        change_rows += [{"Change": "DATA TYPE CHANGED", "Column": item["column"], "Details": f'{item["from"]} -> {item["to"]}'} for item in comparison.type_changes]
        change_rows += [{"Change": "NULLABILITY CHANGED", "Column": item["column"], "Details": f'{item["from"]} -> {item["to"]}'} for item in comparison.nullability_changes]
        change_rows += [{"Change": "NULL COUNT CHANGED", "Column": item["column"], "Details": f'{item["from"]} -> {item["to"]}'} for item in comparison.null_count_changes]
        change_rows += [{"Change": "DISTINCT COUNT CHANGED", "Column": item["column"], "Details": f'{item["from"]} -> {item["to"]}'} for item in comparison.distinct_count_changes]
        if change_rows:
            render_html_table(change_rows, table_id="reports-catalog-change-summary", download=False)
        else:
            st.caption("No metadata or schema changes detected between the latest scans.")
        st.markdown('<div class="section-kicker reports-section-kicker">SCAN HISTORY</div>', unsafe_allow_html=True)
        render_html_table(_catalog_history_rows(context), table_id="reports-catalog-scan-history", download=False,
                          column_widths=[28, 12, 12, 14, 14, 20], max_visible_rows=5,
                          sticky_header=True, scrollable=True)

    st.markdown('<div class="section-kicker reports-section-kicker">EXPORT REPORT</div>', unsafe_allow_html=True)
    try:
        html_export, markdown_export, pdf_export = render_html_report(context), render_markdown_report(context), render_pdf_report(context)
    except Exception:
        st.error("Unable to prepare the catalog report export.")
        return
    export_columns = st.columns(3, gap="medium")
    with export_columns[0]:
        st.download_button("HTML", data=html_export, file_name=build_export_filename(context, "html"), mime="text/html", icon=":material/description:", key="reports-export-catalog-html")
    with export_columns[1]:
        st.download_button("Markdown", data=markdown_export, file_name=build_export_filename(context, "md"), mime="text/markdown", icon=":material/article:", key="reports-export-catalog-markdown")
    with export_columns[2]:
        st.download_button("PDF", data=pdf_export, file_name=build_export_filename(context, "pdf"), mime="application/pdf", icon=":material/picture_as_pdf:", key="reports-export-catalog-pdf")


def _render_report_preview(table: TableMetadata, run: StoredQualityRun | None, all_runs: list[StoredQualityRun]) -> None:
    context = None
    if run is not None and (
        st.session_state.get(REPORT_PREVIEW_DATASET_KEY) == _dataset_id(table)
        and st.session_state.get(REPORT_PREVIEW_RUN_KEY) == run.run_id
    ):
        cached_context = st.session_state.get(REPORT_PREVIEW_KEY)
        if cached_context is not None:
            context = cached_context
    if context is None and run is not None:
        context = build_report_context(table, run, all_runs)
        st.session_state[REPORT_PREVIEW_KEY] = context
        st.session_state[REPORT_PREVIEW_DATASET_KEY] = _dataset_id(table)
        st.session_state[REPORT_PREVIEW_RUN_KEY] = run.run_id
    documentation = context.documentation if context is not None else MetadataDocumentationGenerator().generate(table)
    st.markdown('<div class="section-kicker reports-preview-heading">REPORT PREVIEW</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-kicker reports-section-kicker">DATASET OVERVIEW</div>', unsafe_allow_html=True)
    _render_dataset_overview(documentation)
    _render_metadata_summary(documentation)
    if run is None:
        st.markdown('<div class="section-kicker reports-section-kicker">QUALITY OVERVIEW</div>', unsafe_allow_html=True)
        st.info("No quality runs are available for this dataset yet.")
        return
    report = context.report
    st.markdown('<div class="section-kicker reports-section-kicker">QUALITY OVERVIEW</div>', unsafe_allow_html=True)
    render_workspace_status([
        ("quality", "Quality Score", "—" if report.quality_score is None else _format_percent(report.quality_score), "Persisted run score"),
        ("quality", "Passed Checks", f"{report.passed_rules:,}", "Rules with PASS status"),
        ("quality", "Failed Checks", f"{report.failed_rules:,}", "Rules with FAIL status"),
        ("quality", "Error Checks", f"{report.error_rules:,}", "Rules with ERROR status"),
        ("quality", "Total Checks", f"{report.total_rules:,}", "All persisted results"),
    ], decorations=["quality-signal", "quality-signal", "quality-signal", "quality-signal", "data-grid"])
    health = quality_health(report.quality_score)
    if health:
        st.caption(f"Quality health: {health}")
    with st.container(key="reports-preview-summary"):
        preview_columns = st.columns(2, gap="large")
        with preview_columns[0]:
            with st.container(key="reports-quality-trend"):
                st.markdown('<div class="quality-history-panel-title">QUALITY SCORE TREND</div>', unsafe_allow_html=True)
                trend_svg = build_quality_trend_svg([(_history_timestamp(executed_at), item.quality_score) for executed_at, item in context.historical_runs if item.quality_score is not None])
                if trend_svg:
                    st.markdown(trend_svg, unsafe_allow_html=True)
                else:
                    st.info("Run quality checks again to build a quality trend.")
        with preview_columns[1]:
            summary_rows = [("Dataset", _dataset_label(table)), ("Executed At", _history_timestamp(context.executed_at)), ("Quality Score", _format_percent(report.quality_score) if report.quality_score is not None else "—"), ("Total Checks", f"{report.total_rules:,}"), ("Passed", f"{report.passed_rules:,}"), ("Failed", f"{report.failed_rules:,}"), ("Errors", f"{report.error_rules:,}"), ("Run ID", context.run_id)]
            summary_html = "".join(f'<div class="quality-history-latest-row"><span>{escape(label)}</span><strong>{escape(value)}</strong></div>' for label, value in summary_rows)
            st.markdown(f'<div class="quality-history-latest card-decoration-data-grid"><div class="card-content"><div class="quality-history-panel-title">DATASET / RUN SUMMARY</div>{summary_html}</div></div>', unsafe_allow_html=True)
    _render_failed_checks(report)
    result_rows = [{"Rule": _quality_rule_label(result.rule_type), "Column / Scope": result.column, "Status": result.status, "Passed": f"{result.passed_records:,}", "Failed": f"{result.failed_records:,}", "Failure %": _format_percent(result.failure_percentage)} for result in report.results]
    st.markdown('<div class="section-kicker reports-section-kicker">RULE RESULTS</div>', unsafe_allow_html=True)
    if result_rows:
        render_html_table(result_rows, table_id="reports-rule-results", download=False, column_widths=[17, 23, 15, 15, 15, 15], table_class="quality-result-table", cell_renderers={
            "Rule": lambda value, _row: f'<span class="html-table-badge html-table-badge--rule">{escape(str(value))}</span>',
            "Column / Scope": lambda value, _row: f'<span class="html-table-column-name">{escape(str(value))}</span>',
            "Status": _quality_status_cell,
            "Failure %": lambda value, _row: f'<span class="html-table-secondary">{escape(str(value))}</span>',
        })
    else:
        st.info("No rule results were persisted for this quality run.")
    st.markdown('<div class="section-kicker reports-section-kicker">EXPORT REPORT</div>', unsafe_allow_html=True)
    try:
        html_export = render_html_report(context)
        markdown_export = render_markdown_report(context)
        pdf_export = render_pdf_report(context)
    except Exception:
        st.error("Unable to prepare the report export.")
        return
    export_columns = st.columns(3, gap="medium")
    with export_columns[0]:
        st.download_button("HTML", data=html_export, file_name=build_export_filename(context, "html"), mime="text/html", icon=":material/description:", key="reports-export-html")
    with export_columns[1]:
        st.download_button("Markdown", data=markdown_export, file_name=build_export_filename(context, "md"), mime="text/markdown", icon=":material/article:", key="reports-export-markdown")
    with export_columns[2]:
        st.download_button("PDF", data=pdf_export, file_name=build_export_filename(context, "pdf"), mime="application/pdf", icon=":material/picture_as_pdf:", key="reports-export-pdf")


render_page_header("Reports", "Review and export persisted catalog metadata and data-quality findings.", "Generate documentation and historical reports without reconnecting to the source system.", icon="report")
if REPORT_TYPE_KEY not in st.session_state:
    st.session_state[REPORT_TYPE_KEY] = REPORT_TYPE_QUALITY
st.markdown('<div class="section-kicker reports-section-kicker">REPORT TYPE</div>', unsafe_allow_html=True)
report_type = st.radio("Report Type", [REPORT_TYPE_QUALITY, REPORT_TYPE_CATALOG], key=REPORT_TYPE_KEY, horizontal=True, label_visibility="collapsed")
if report_type == REPORT_TYPE_CATALOG:
    render_get_started_workflow([("catalog", "SELECT DATASET"), ("report", "PREVIEW"), ("report", "EXPORT")], class_name="get-started-workflow metadata-scan-workflow")
else:
    render_get_started_workflow([("catalog", "SELECT DATASET"), ("quality", "SELECT RUN"), ("report", "PREVIEW"), ("report", "EXPORT")], class_name="get-started-workflow metadata-scan-workflow")

try:
    catalog = MetadataRepository().list_tables(current_user_id())
except Exception:
    st.error("Unable to load persisted catalog datasets.")
    st.stop()

table_options = {_dataset_id(table): table for table in catalog}

if report_type == REPORT_TYPE_CATALOG:
    catalog_dataset_options = [CHOOSE_DATASET] + list(table_options)
    load_widget_state(st.session_state, REPORT_CATALOG_DATASET_KEY, REPORT_CATALOG_DATASET_WIDGET_KEY, CHOOSE_DATASET, catalog_dataset_options)
    st.markdown('<div class="section-kicker reports-section-kicker">SELECT DATASET</div>', unsafe_allow_html=True)
    catalog_dataset_id = st.selectbox(
        "Catalog Dataset", catalog_dataset_options, key=REPORT_CATALOG_DATASET_WIDGET_KEY,
        on_change=store_widget_state, args=(st.session_state, REPORT_CATALOG_DATASET_KEY, REPORT_CATALOG_DATASET_WIDGET_KEY),
        format_func=lambda value: CHOOSE_DATASET if value == CHOOSE_DATASET else _dataset_label(table_options[value]),
    )
    if catalog_dataset_id == CHOOSE_DATASET:
        st.caption("Choose a persisted catalog dataset to preview its documentation.")
        st.stop()
    catalog_table = table_options[catalog_dataset_id]
    try:
        catalog_history = MetadataRepository().list_scan_history(catalog_table.source_type, catalog_table.database_name, catalog_table.schema_name, catalog_table.table_name, current_user_id())
        catalog_context = build_catalog_report_context(catalog_table, catalog_history)
    except Exception:
        st.error("Unable to load persisted catalog metadata.")
        st.stop()
    _render_catalog_report_preview(catalog_context)
    st.stop()

dataset_options = [CHOOSE_DATASET] + list(table_options)
load_widget_state(
    st.session_state,
    REPORT_DATASET_KEY,
    REPORT_DATASET_WIDGET_KEY,
    CHOOSE_DATASET,
    dataset_options,
)
st.markdown('<div class="section-kicker reports-section-kicker">SELECT DATASET</div>', unsafe_allow_html=True)
selected_dataset_id = st.selectbox(
    "Dataset",
    dataset_options,
    key=REPORT_DATASET_WIDGET_KEY,
    on_change=store_widget_state,
    args=(st.session_state, REPORT_DATASET_KEY, REPORT_DATASET_WIDGET_KEY),
    format_func=lambda value: CHOOSE_DATASET if value == CHOOSE_DATASET else _dataset_label(table_options[value]),
)
if selected_dataset_id == CHOOSE_DATASET:
    st.caption("Choose a persisted dataset to inspect its quality history.")
    st.stop()

selected_table = table_options[selected_dataset_id]
if st.session_state.get("reports_active_dataset") != selected_dataset_id:
    st.session_state["reports_active_dataset"] = selected_dataset_id
    st.session_state[REPORT_RUN_KEY] = CHOOSE_RUN
    for key in (REPORT_PREVIEW_KEY, REPORT_PREVIEW_DATASET_KEY, REPORT_PREVIEW_RUN_KEY):
        st.session_state.pop(key, None)
try:
    quality_runs = QualityRunRepository().list_quality_runs_for_dataset(selected_table.source_type, selected_table.database_name, selected_table.schema_name, selected_table.table_name, user_id=current_user_id())
except Exception:
    st.error("Unable to load persisted quality runs.")
    st.stop()
st.markdown('<div class="section-kicker reports-section-kicker">SELECT RUN</div>', unsafe_allow_html=True)
if not quality_runs:
    st.session_state[REPORT_RUN_KEY] = CHOOSE_RUN
    for key in (REPORT_PREVIEW_KEY, REPORT_PREVIEW_DATASET_KEY, REPORT_PREVIEW_RUN_KEY):
        st.session_state.pop(key, None)
    _render_report_preview(selected_table, None, [])
    st.stop()
run_options = [CHOOSE_RUN] + [run.run_id for run in quality_runs]
run_by_id = {run.run_id: run for run in quality_runs}
load_widget_state(
    st.session_state,
    REPORT_RUN_KEY,
    REPORT_RUN_WIDGET_KEY,
    CHOOSE_RUN,
    run_options,
)
selected_run_id = st.selectbox(
    "Quality Run",
    run_options,
    key=REPORT_RUN_WIDGET_KEY,
    on_change=store_widget_state,
    args=(st.session_state, REPORT_RUN_KEY, REPORT_RUN_WIDGET_KEY),
    format_func=lambda value: CHOOSE_RUN if value == CHOOSE_RUN else _run_label(run_by_id[value]),
)
if selected_run_id == CHOOSE_RUN:
    for key in (REPORT_PREVIEW_KEY, REPORT_PREVIEW_DATASET_KEY, REPORT_PREVIEW_RUN_KEY):
        st.session_state.pop(key, None)
    st.caption("Choose a persisted quality run to preview its findings.")
    st.stop()
authorized_run = QualityRunRepository().get_quality_run(selected_run_id, user_id=current_user_id())
if authorized_run is None:
    for key in (REPORT_PREVIEW_KEY, REPORT_PREVIEW_DATASET_KEY, REPORT_PREVIEW_RUN_KEY):
        st.session_state.pop(key, None)
    st.error("The selected quality run is not available for this account.")
    st.stop()
_render_report_preview(selected_table, authorized_run, quality_runs)
