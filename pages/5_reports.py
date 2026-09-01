from __future__ import annotations

from datetime import datetime
from html import escape

import streamlit as st

from auth.session import current_user_id, require_authenticated
from documentation import MetadataDocumentationGenerator
from metadata.models import TableMetadata
from storage.quality_repository import QualityRunRepository, StoredQualityRun
from storage.repository import MetadataRepository
from ui.components import render_get_started_workflow, render_html_table, render_page_header, render_workspace_status
from ui.report_export import build_export_filename, render_html_report, render_markdown_report, render_pdf_report
from ui.report_view import build_column_profiles, build_metadata_summary, build_report_context, failed_results, format_profile_value, quality_health
from ui.quality_trend import build_quality_trend_svg


require_authenticated()


REPORT_DATASET_KEY = "reports_selected_dataset"
REPORT_RUN_KEY = "reports_selected_run"
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


def _render_dataset_overview(documentation: object) -> None:
    fields = [
        ("Source", _source_name(documentation.source_type)),
        ("Database", documentation.database_name),
        ("Schema", documentation.schema_name),
        ("Table", documentation.table_name),
        ("Rows", "—" if documentation.summary.row_count is None else f"{documentation.summary.row_count:,}"),
        ("Columns", f"{documentation.summary.column_count:,}"),
    ]
    columns = st.columns(6)
    for column, (label, value) in zip(columns, fields):
        with column:
            st.markdown(f'<div class="quality-context-item"><span>{escape(label)}</span><strong>{escape(value)}</strong></div>', unsafe_allow_html=True)


def _render_metadata_summary(documentation: object) -> None:
    summary = build_metadata_summary(documentation)
    st.markdown('<div class="section-kicker reports-section-kicker">METADATA SUMMARY</div>', unsafe_allow_html=True)
    render_workspace_status([
        ("catalog", "Total Columns", f"{summary.total_columns:,}", "Persisted metadata"),
        ("quality", "Required Columns", f"{summary.non_nullable_columns:,}", "Non-nullable columns"),
        ("catalog", "Nullable Columns", f"{summary.nullable_columns:,}", "Allow null values"),
        ("quality", "Numeric Columns", f"{summary.numeric_columns:,}", "Number and decimal types"),
        ("report", "Date / Datetime", f"{summary.date_datetime_columns:,}", "Date and datetime types"),
    ], compact=True, show_detail=False)
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


def _render_report_preview(table: TableMetadata, run: StoredQualityRun | None, all_runs: list[StoredQualityRun]) -> None:
    context = build_report_context(table, run, all_runs) if run is not None else None
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
    ])
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
            st.markdown(f'<div class="quality-history-latest"><div class="quality-history-panel-title">DATASET / RUN SUMMARY</div>{summary_html}</div>', unsafe_allow_html=True)
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


render_page_header("Reports", "Review persisted metadata and data-quality findings.", "Inspect historical quality runs without reconnecting to the source system.", icon="report")
render_get_started_workflow([("catalog", "SELECT DATASET"), ("quality", "SELECT RUN"), ("report", "PREVIEW"), ("report", "EXPORT")], class_name="get-started-workflow metadata-scan-workflow")

try:
    catalog = MetadataRepository().list_tables(current_user_id())
except Exception:
    st.error("Unable to load persisted catalog datasets.")
    st.stop()

table_options = {_dataset_id(table): table for table in catalog}
dataset_options = [CHOOSE_DATASET] + list(table_options)
if st.session_state.get(REPORT_DATASET_KEY) not in dataset_options:
    st.session_state[REPORT_DATASET_KEY] = CHOOSE_DATASET
st.markdown('<div class="section-kicker reports-section-kicker">SELECT DATASET</div>', unsafe_allow_html=True)
selected_dataset_id = st.selectbox("Dataset", dataset_options, key=REPORT_DATASET_KEY, format_func=lambda value: CHOOSE_DATASET if value == CHOOSE_DATASET else _dataset_label(table_options[value]))
if selected_dataset_id == CHOOSE_DATASET:
    st.caption("Choose a persisted dataset to inspect its quality history.")
    st.stop()

selected_table = table_options[selected_dataset_id]
if st.session_state.get("reports_active_dataset") != selected_dataset_id:
    st.session_state["reports_active_dataset"] = selected_dataset_id
    st.session_state[REPORT_RUN_KEY] = CHOOSE_RUN
try:
    quality_runs = QualityRunRepository().list_quality_runs_for_dataset(selected_table.source_type, selected_table.database_name, selected_table.schema_name, selected_table.table_name, user_id=current_user_id())
except Exception:
    st.error("Unable to load persisted quality runs.")
    st.stop()
st.markdown('<div class="section-kicker reports-section-kicker">SELECT RUN</div>', unsafe_allow_html=True)
if not quality_runs:
    st.session_state[REPORT_RUN_KEY] = CHOOSE_RUN
    _render_report_preview(selected_table, None, [])
    st.stop()
run_options = [CHOOSE_RUN] + [run.run_id for run in quality_runs]
run_by_id = {run.run_id: run for run in quality_runs}
if st.session_state.get(REPORT_RUN_KEY) not in run_options:
    st.session_state[REPORT_RUN_KEY] = CHOOSE_RUN
selected_run_id = st.selectbox("Quality Run", run_options, key=REPORT_RUN_KEY, format_func=lambda value: CHOOSE_RUN if value == CHOOSE_RUN else _run_label(run_by_id[value]))
if selected_run_id == CHOOSE_RUN:
    st.caption("Choose a persisted quality run to preview its findings.")
    st.stop()
authorized_run = QualityRunRepository().get_quality_run(selected_run_id, user_id=current_user_id())
if authorized_run is None:
    st.error("The selected quality run is not available for this account.")
    st.stop()
_render_report_preview(selected_table, authorized_run, quality_runs)
