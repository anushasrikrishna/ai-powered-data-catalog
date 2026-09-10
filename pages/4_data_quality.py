from __future__ import annotations

import json
import re
from datetime import datetime
from html import escape
from typing import Any
from uuid import uuid4

import streamlit as st

from auth.session import current_user_id, require_authenticated
from pydantic import ValidationError

from core.connection_registry import canonical_source_type, get_connection_registry
from ai.quality_rule_suggester import QualityRuleSuggester
from documentation import MetadataDocumentationGenerator
from ai.models import AISuggestionResult
from metadata.models import TableMetadata
from quality.common_checks import infer_common_rules
from quality.rule_engine import FAILURE_DETAIL_LIMIT, QualityReport, QualityResult, QualityRuleEngine
from quality.rule_models import (
    AcceptedValuesRule,
    DuplicateRule,
    FreshnessRule,
    NotNullRule,
    NumericRangeRule,
    StringLengthRule,
    UniqueRule,
    parse_quality_rule,
)
from storage.repository import MetadataRepository
from storage.quality_repository import QualityRunRepository
from ui.components import loading_indicator, render_empty_state, render_get_started_workflow, render_html_table, render_page_header, table_to_csv
from ui.connection_workflow import (
    ACTIVE_CONNECTION_ID_KEY,
    render_connected_sources_table,
    safe_connection_error,
)
from ui.quality_trend import build_quality_trend_svg


require_authenticated()


QUALITY_RULES_KEY = "quality_configured_rules"
QUALITY_DATASET_KEY = "quality_configured_dataset"
QUALITY_COMMON_RULES_KEY = "quality_common_rules"
QUALITY_FORM_OPEN_KEY = "quality_business_form_open"
QUALITY_LAST_COLUMN_KEY = "quality_last_rule_column"
QUALITY_LAST_TYPE_KEY = "quality_last_rule_type"
QUALITY_RESULT_KEY = "quality_execution_result"
QUALITY_RESULT_DATASET_KEY = "quality_execution_result_dataset"
QUALITY_RESULT_RULE_SIGNATURE_KEY = "quality_execution_result_rule_signature"
QUALITY_RULE_SIGNATURE_KEY = "quality_prepared_rule_signature"
QUALITY_RUN_STATUS_KEY = "quality_run_status"
QUALITY_REVIEW_READY_KEY = "quality_review_ready"
QUALITY_RUN_IN_PROGRESS_KEY = "quality_run_in_progress"
QUALITY_REVIEW_DETAIL_KEY = "quality_review_detail_selection"
QUALITY_REVIEW_DETAIL_CACHE_KEY = "quality_review_detail_cache"
QUALITY_REVIEW_RECORD_CACHE_KEY = "quality_review_record_cache"
QUALITY_REVIEW_ALL_RECORD_CACHE_KEY = "quality_review_all_record_cache"
QUALITY_REVIEW_ALL_RECORDS_OPEN_KEY = "quality_review_all_records_open"
QUALITY_REVIEW_RULE_RECORDS_OPEN_KEY = "quality_review_rule_records_open"
QUALITY_FAILED_RECORD_VIEW_LIMIT = 100
QUALITY_RESULT_RUN_ID_KEY = "quality_execution_run_id"
QUALITY_HISTORY_DATASET_KEY = "quality_history_dataset"
QUALITY_AI_RESULT_KEY = "quality_ai_suggestion_result"
QUALITY_AI_RESULT_DATASET_KEY = "quality_ai_suggestion_dataset"
QUALITY_AI_IN_PROGRESS_KEY = "quality_ai_suggestion_in_progress"
QUALITY_AI_ACCEPTED_KEY = "quality_ai_accepted_rule_identities"
QUALITY_AI_DUPLICATE_NOTICE_KEY = "quality_ai_duplicate_notice"
QUALITY_AI_SUGGESTER_KEY = "quality_ai_suggester"
QUALITY_HISTORY_LIMIT = 10
SELECT_COLUMN = "Select a column"
SELECT_RULE_TYPE = "Select a rule type"
CHOOSE_DATASET = "Choose a dataset"

RULE_DEFINITIONS = {
    "Not Null": (NotNullRule, "Checks that selected values are populated."),
    "Unique": (UniqueRule, "Checks that selected values are unique."),
    "Duplicate": (DuplicateRule, "Checks for duplicate values in the selected column."),
    "Accepted Values": (AcceptedValuesRule, "Checks that values are within an accepted set."),
    "Numeric Range": (NumericRangeRule, "Checks that numeric values stay within configured bounds."),
    "String Length": (StringLengthRule, "Checks that string values stay within configured lengths."),
    "Freshness": (FreshnessRule, "Checks that date values are not older than the configured age."),
}
BUSINESS_RULE_DEFINITIONS = {
    name: RULE_DEFINITIONS[name]
    for name in ("Accepted Values", "Numeric Range", "String Length", "Freshness", "Not Null", "Unique")
}
RULES_BY_NORMALIZED_TYPE = {
    "NUMBER": ("Not Null", "Unique", "Accepted Values", "Numeric Range"),
    "DECIMAL": ("Not Null", "Unique", "Accepted Values", "Numeric Range"),
    "STRING": ("Not Null", "Unique", "Accepted Values", "String Length"),
    "DATE": ("Not Null", "Unique", "Accepted Values", "Freshness"),
    "DATETIME": ("Not Null", "Unique", "Accepted Values", "Freshness"),
}


def _dataset_id(table: TableMetadata) -> str:
    return "|".join(part.strip().lower() for part in (table.source_type, table.database_name, table.schema_name, table.table_name))


def _source_name(source_type: str) -> str:
    return {"sqlserver": "SQL Server", "postgresql": "PostgreSQL", "snowflake": "Snowflake"}.get(source_type.strip().lower(), source_type)


def _dataset_label(table: TableMetadata) -> str:
    return f"{_source_name(table.source_type)} / {table.database_name} / {table.schema_name} / {table.table_name}"


def _rule_signature(common_rules: list[dict[str, Any]], business_rules: list[dict[str, Any]]) -> str:
    payload = {"common": common_rules, "business": business_rules}
    return json.dumps(payload, sort_keys=True, default=str)


def _rule_identity(rule: Any) -> str:
    if isinstance(rule, dict):
        payload = parse_quality_rule(rule).model_dump(exclude_none=True)
    else:
        payload = parse_quality_rule(rule).model_dump(exclude_none=True)
    return json.dumps(payload, sort_keys=True, default=str)


def _prepared_rule_identities() -> set[str]:
    return {
        _rule_identity(rule)
        for rule in (
            *st.session_state.get(QUALITY_COMMON_RULES_KEY, []),
            *st.session_state.get(QUALITY_RULES_KEY, []),
        )
    }


def _accepted_ai_identities(dataset_id: str) -> set[str]:
    accepted = st.session_state.setdefault(QUALITY_AI_ACCEPTED_KEY, {})
    return accepted.setdefault(dataset_id, set())


def _invalidate_execution_result() -> None:
    for key in (
        QUALITY_RESULT_KEY,
        QUALITY_RESULT_DATASET_KEY,
        QUALITY_RESULT_RULE_SIGNATURE_KEY,
        QUALITY_REVIEW_DETAIL_KEY,
        QUALITY_REVIEW_DETAIL_CACHE_KEY,
        QUALITY_REVIEW_RECORD_CACHE_KEY,
        QUALITY_REVIEW_ALL_RECORD_CACHE_KEY,
        QUALITY_REVIEW_ALL_RECORDS_OPEN_KEY,
        QUALITY_REVIEW_RULE_RECORDS_OPEN_KEY,
        QUALITY_RESULT_RUN_ID_KEY,
    ):
        st.session_state.pop(key, None)
    st.session_state[QUALITY_RUN_STATUS_KEY] = "ready"
    st.session_state[QUALITY_REVIEW_READY_KEY] = False


def _active_connector_for(table: TableMetadata) -> Any | None:
    registry = get_connection_registry()
    expected_source = canonical_source_type(table.source_type)
    active_entry = registry.get(st.session_state.get(ACTIVE_CONNECTION_ID_KEY))
    if active_entry is not None and (
        active_entry.source_type != expected_source
        or active_entry.database_name.casefold() != table.database_name.strip().casefold()
    ):
        active_entry = None
    entry = active_entry or registry.find(expected_source, table.database_name)
    if entry is None or not entry.connected or getattr(entry.connector, "engine", None) is None:
        return None
    return entry.connector


def _connected_catalog_tables(catalog: list[TableMetadata]) -> tuple[list[TableMetadata], bool]:
    active_entries = [entry for entry in get_connection_registry().entries() if entry.connected]
    if not active_entries:
        return [], False
    identities = {
        (canonical_source_type(entry.source_type), entry.database_name.strip().casefold())
        for entry in active_entries
    }
    return [
        table
        for table in catalog
        if (canonical_source_type(table.source_type), table.database_name.strip().casefold()) in identities
    ], True


def _run_quality_checks(
    table: TableMetadata | None,
    common_rules: list[dict[str, Any]],
    business_rules: list[dict[str, Any]],
) -> bool:
    if table is None:
        st.error("Choose a dataset before running quality checks.")
        return False
    rules = [*common_rules, *business_rules]
    if not rules:
        st.error("Configure at least one quality check before running.")
        return False
    connector = _active_connector_for(table)
    if connector is None:
        st.error("A live source connection is required to run quality checks.")
        return False

    dataset_id = _dataset_id(table)
    rule_signature = _rule_signature(common_rules, business_rules)
    st.session_state.pop(QUALITY_REVIEW_DETAIL_KEY, None)
    st.session_state[QUALITY_RUN_IN_PROGRESS_KEY] = True
    st.session_state[QUALITY_RUN_STATUS_KEY] = "running"
    try:
        with loading_indicator("Running quality checks..."):
            report = QualityRuleEngine().execute_rules(connector, table, rules)
    except Exception as exc:
        st.session_state[QUALITY_RUN_STATUS_KEY] = "error"
        st.session_state[QUALITY_REVIEW_READY_KEY] = False
        st.error(f"Quality checks could not be completed: {safe_connection_error(str(exc))}")
        return False
    finally:
        st.session_state[QUALITY_RUN_IN_PROGRESS_KEY] = False

    run_id = str(uuid4())
    st.session_state[QUALITY_RESULT_KEY] = report
    st.session_state[QUALITY_RESULT_DATASET_KEY] = dataset_id
    st.session_state[QUALITY_RESULT_RULE_SIGNATURE_KEY] = rule_signature
    st.session_state[QUALITY_RESULT_RUN_ID_KEY] = run_id
    st.session_state[QUALITY_HISTORY_DATASET_KEY] = dataset_id
    st.session_state[QUALITY_REVIEW_DETAIL_CACHE_KEY] = {}
    st.session_state[QUALITY_REVIEW_RECORD_CACHE_KEY] = {}
    st.session_state[QUALITY_REVIEW_ALL_RECORD_CACHE_KEY] = {}
    try:
        QualityRunRepository().save_quality_run(run_id, report, user_id=current_user_id())
    except Exception:
        st.warning("Quality checks completed, but the run history could not be saved.")
    st.session_state[QUALITY_RUN_STATUS_KEY] = "complete"
    st.session_state[QUALITY_REVIEW_READY_KEY] = True
    st.success("Quality checks completed. Results are ready for review.")
    return True


def _selectbox_with_reset(label: str, options: list[str], key: str) -> str:
    if st.session_state.get(key) not in options:
        st.session_state[key] = options[0]
    return st.selectbox(label, options, key=key)


def _close_business_form() -> None:
    st.session_state[QUALITY_FORM_OPEN_KEY] = False
    for key in (
        "quality_rule_type",
        "quality_rule_column",
        "quality_accepted_values",
        "quality_min_value",
        "quality_max_value",
        "quality_min_length",
        "quality_max_length",
        "quality_max_age_days",
        QUALITY_LAST_COLUMN_KEY,
        QUALITY_LAST_TYPE_KEY,
    ):
        st.session_state.pop(key, None)


def _clear_rule_configuration() -> None:
    for key in (
        "quality_accepted_values",
        "quality_min_value",
        "quality_max_value",
        "quality_min_length",
        "quality_max_length",
        "quality_max_age_days",
    ):
        st.session_state.pop(key, None)


def _clear_rule_type_and_configuration() -> None:
    st.session_state.pop("quality_rule_type", None)
    st.session_state.pop(QUALITY_LAST_TYPE_KEY, None)
    _clear_rule_configuration()


def _rule_types_for_column(table: TableMetadata, column_name: str) -> list[str]:
    column = next(column for column in table.columns if column.column_name == column_name)
    normalized_type = column.normalized_data_type.strip().upper()
    return list(RULES_BY_NORMALIZED_TYPE.get(normalized_type, ("Not Null", "Unique", "Accepted Values")))


def _column_label(table: TableMetadata, column_name: str) -> str:
    column = next(column for column in table.columns if column.column_name == column_name)
    return f"{column.column_name} — {column.normalized_data_type}"


def _compatible_columns(table: TableMetadata, rule_name: str) -> list[Any]:
    if rule_name == "Numeric Range":
        return [column for column in table.columns if column.normalized_data_type.upper() in {"NUMBER", "DECIMAL"}]
    if rule_name == "String Length":
        return [column for column in table.columns if column.normalized_data_type.upper() == "STRING"]
    if rule_name == "Freshness":
        return [column for column in table.columns if column.normalized_data_type.upper() in {"DATE", "DATETIME"}]
    return list(table.columns)


def _common_rules(table: TableMetadata) -> list[dict[str, Any]]:
    return infer_common_rules(table)


def _parse_number(value: str) -> int | float | None:
    normalized = value.strip()
    if not normalized:
        return None
    try:
        number = float(normalized)
    except ValueError as exc:
        raise ValueError("Numeric bounds must be valid numbers.") from exc
    return int(number) if number.is_integer() else number


def _parse_int(value: str) -> int | None:
    normalized = value.strip()
    if not normalized:
        return None
    try:
        return int(normalized)
    except ValueError as exc:
        raise ValueError("Length bounds must be whole numbers.") from exc


def _build_rule(rule_name: str, column: str, values: dict[str, Any]) -> Any:
    rule_model = RULE_DEFINITIONS[rule_name][0]
    payload: dict[str, Any] = {"column": column}
    if rule_model is AcceptedValuesRule:
        payload["accepted_values"] = [value.strip() for value in values["accepted_values"].split(",") if value.strip()]
    elif rule_model is NumericRangeRule:
        payload.update(min_value=_parse_number(values["min_value"]), max_value=_parse_number(values["max_value"]))
    elif rule_model is StringLengthRule:
        payload.update(min_length=_parse_int(values["min_length"]), max_length=_parse_int(values["max_length"]))
    elif rule_model is FreshnessRule:
        payload["max_age_days"] = values["max_age_days"]
    return rule_model(**payload)


def _rule_summary(payload: dict[str, Any]) -> tuple[str, str, str]:
    label = {"not_null": "Not Null", "unique": "Unique", "duplicate": "Duplicate", "accepted_values": "Accepted Values", "numeric_range": "Numeric Range", "string_length": "String Length", "freshness": "Freshness"}.get(str(payload.get("rule_type")), str(payload.get("rule_type")))
    details = []
    for key in ("accepted_values", "min_value", "max_value", "min_length", "max_length", "max_age_days"):
        if key in payload and payload[key] is not None:
            value = payload[key]
            details.append(", ".join(str(item) for item in value) if isinstance(value, list) else f"{key.replace('_', ' ').title()}: {value}")
    return label, str(payload.get("column", "")), " · ".join(details)


def _table_badge(value: Any, _row: dict[Any, Any]) -> str:
    return f'<span class="html-table-badge html-table-badge--rule">{escape(str(value))}</span>'


def _table_identifier(value: Any, _row: dict[Any, Any]) -> str:
    return f'<span class="html-table-column-name">{escape(str(value))}</span>'


def _table_secondary(value: Any, _row: dict[Any, Any]) -> str:
    return f'<span class="html-table-secondary">{escape(str(value))}</span>'


def _quality_rule_label(rule_type: str | None) -> str:
    if not rule_type:
        return "Unknown Rule"
    return {
        "not_null": "Not Null",
        "unique": "Unique",
        "duplicate": "Duplicate",
        "accepted_values": "Accepted Values",
        "numeric_range": "Numeric Range",
        "string_length": "String Length",
        "freshness": "Freshness",
    }.get(rule_type, rule_type.replace("_", " ").title())


def _rejection_category_label(category: str) -> str:
    return {
        "unsupported_rule": "Unsupported Rule",
        "unknown_column": "Unknown Column",
        "datatype_mismatch": "Datatype Mismatch",
        "invalid_configuration": "Invalid Configuration",
        "duplicate_suggestion": "Duplicate Suggestion",
        "schema_validation_failure": "Schema Validation Failure",
    }.get(category, category.replace("_", " ").title())


def _ai_suggester() -> QualityRuleSuggester:
    suggester = st.session_state.get(QUALITY_AI_SUGGESTER_KEY)
    if not isinstance(suggester, QualityRuleSuggester):
        suggester = QualityRuleSuggester()
        st.session_state[QUALITY_AI_SUGGESTER_KEY] = suggester
    return suggester


def _format_ai_response_time(response_time_ms: float | None) -> str | None:
    if response_time_ms is None:
        return None
    if response_time_ms >= 1000:
        return f"{response_time_ms / 1000:.1f} s"
    return f"{response_time_ms:.1f} ms"


def _render_ai_suggestions(selected_table: TableMetadata) -> None:
    """Render explicit, metadata-grounded AI suggestions for the selected dataset."""
    st.markdown('<div class="section-kicker">AI RULE SUGGESTIONS</div>', unsafe_allow_html=True)
    st.caption("Generate metadata-grounded quality-rule suggestions using the configured local AI model.")
    st.caption("AI suggestions require human review and are not added automatically.")

    dataset_id = _dataset_id(selected_table)
    suggester = _ai_suggester()
    existing_result = st.session_state.get(QUALITY_AI_RESULT_KEY)
    existing_dataset = st.session_state.get(QUALITY_AI_RESULT_DATASET_KEY)
    in_progress = st.session_state.get(QUALITY_AI_IN_PROGRESS_KEY, False)
    has_current_result = isinstance(existing_result, AISuggestionResult) and existing_dataset == dataset_id
    generate = st.button(
        "Regenerate AI Suggestions" if has_current_result else "Generate AI Suggestions",
        type="primary",
        icon=":material/auto_awesome:",
        key="generate-ai-suggestions",
        disabled=not suggester.client.enabled or in_progress,
    )
    if generate:
        st.session_state[QUALITY_AI_IN_PROGRESS_KEY] = True
        try:
            if has_current_result:
                suggester.clear_cache()
            documentation = MetadataDocumentationGenerator().generate(selected_table)
            with loading_indicator("Generating AI quality suggestions..."):
                result = suggester.suggest_for_table(documentation)
            st.session_state[QUALITY_AI_RESULT_KEY] = result
            st.session_state[QUALITY_AI_RESULT_DATASET_KEY] = dataset_id
        except Exception:
            st.session_state[QUALITY_AI_RESULT_KEY] = AISuggestionResult(
                status="ERROR",
                model=suggester.client.model,
                message="AI suggestions could not be generated.",
            )
            st.session_state[QUALITY_AI_RESULT_DATASET_KEY] = dataset_id
        finally:
            st.session_state[QUALITY_AI_IN_PROGRESS_KEY] = False
        st.rerun()

    if not suggester.client.enabled:
        st.caption("AI suggestions are currently disabled.")
        return
    if not isinstance(existing_result, AISuggestionResult) or existing_dataset != dataset_id:
        return

    result = existing_result
    if result.status == "SUCCESS":
        acceptance_notice = st.session_state.pop("quality_ai_acceptance_notice", None)
        if acceptance_notice:
            st.success(acceptance_notice)
        duplicate_notice = st.session_state.pop(QUALITY_AI_DUPLICATE_NOTICE_KEY, None)
        if duplicate_notice and duplicate_notice[0] == dataset_id:
            st.info(duplicate_notice[1])
        response_time = _format_ai_response_time(result.response_time_ms)
        summary = [f"Model: {result.model}", f"Suggestions: {len(result.suggestions)}"]
        if response_time is not None:
            summary.append(f"Response Time: {response_time}")
        if result.cache_hit:
            summary.append("Cached")
        st.caption(" · ".join(summary))
        if result.rejected_suggestions:
            st.caption(f"{len(result.rejected_suggestions)} additional AI suggestions were rejected by validation.")
            with st.expander(f"Rejected by Validation ({len(result.rejected_suggestions)})", expanded=False):
                rejected_rows = [
                    {
                        "Rule": _quality_rule_label(rejected.rule_type),
                        "Column": rejected.column or "—",
                        "Category": _rejection_category_label(rejected.category),
                        "Reason": rejected.reason,
                    }
                    for rejected in result.rejected_suggestions
                ]
                render_html_table(
                    rejected_rows,
                    table_id="quality-ai-rejected-suggestions",
                    download=False,
                    column_widths=[20, 22, 25, 33],
                    cell_renderers={
                        "Rule": _table_badge,
                        "Column": _table_identifier,
                        "Category": _table_secondary,
                        "Reason": _table_secondary,
                    },
                )
        if not result.suggestions:
            st.info("No AI suggestions passed validation for this dataset.")
            return
        rows = [
            {
                "Rule": _quality_rule_label(suggestion.rule.rule_type),
                "Column": suggestion.rule.column,
                "Reason": suggestion.reason or "No reason provided.",
                "Action": "",
            }
            for index, suggestion in enumerate(result.suggestions)
        ]
        render_html_table(
            rows,
            table_id="quality-ai-suggestions",
            download=False,
            column_widths=[20, 25, 43, 12],
            cell_renderers={"Rule": _table_badge, "Column": _table_identifier, "Reason": _table_secondary},
            action={
                "header": "Action",
                "key_prefix": "add-ai-rule",
                "help": "Add AI suggestion to Business Rules",
                "label": lambda _row, suggestion_index: _ai_action_label(suggestion_index, dataset_id),
                "disabled": lambda _row, suggestion_index: _ai_action_disabled(suggestion_index, dataset_id),
                "callback": _add_ai_rule,
            },
        )
    elif result.status == "DISABLED":
        st.info(result.message or "AI suggestions are currently disabled.")
    elif result.status == "UNAVAILABLE":
        st.warning("The configured local AI model or service is unavailable.")
    elif result.status == "ERROR":
        st.error(result.message or "AI suggestions could not be generated.")


def _format_quality_percent(value: float) -> str:
    return f"{value:g}%"


def _quality_status_cell(value: Any, _row: dict[Any, Any]) -> str:
    status = str(value)
    return f'<span class="quality-result-status quality-result-status--{status.casefold()}">{escape(status)}</span>'


def _quality_result_message(result: QualityResult) -> str:
    if result.status == "PASS":
        return "Passed"
    if result.status == "FAIL":
        return f"{result.failed_records:,} failed records"
    return safe_connection_error(result.error_message or "Execution error")


def _quality_configuration_lines(result: QualityResult) -> list[tuple[str, str]]:
    config = result.rule_config or {}
    lines: list[tuple[str, str]] = []
    if "accepted_values" in config:
        values = config["accepted_values"]
        rendered = ", ".join(str(value) for value in values) if isinstance(values, list) else str(values)
        lines.append(("Expected Values", rendered))
    for key, label in (
        ("min_value", "Minimum"),
        ("max_value", "Maximum"),
        ("min_length", "Minimum Length"),
        ("max_length", "Maximum Length"),
        ("max_age_days", "Freshness Threshold (days)"),
    ):
        if config.get(key) is not None:
            lines.append((label, str(config[key])))
    return lines or [("Configuration", "No additional configuration")]


def _quality_expected_condition(result: QualityResult) -> str:
    return {
        "not_null": "Value must not be NULL",
        "unique": "Values must be unique",
        "duplicate": "Duplicate values are not allowed",
        "accepted_values": "Value must match one of the expected values",
        "numeric_range": "Value must remain within the configured bounds",
        "string_length": "Value length must remain within the configured bounds",
        "freshness": "Value must be within the configured freshness threshold",
    }.get(result.rule_type, "See the configured rule definition")


def _render_quality_result_detail(selected_table: TableMetadata, result: QualityResult) -> None:
    detail_heading = "FAILURE DETAILS" if result.status == "FAIL" else "ERROR DETAILS"
    st.markdown(f'<div class="section-kicker quality-detail-heading">{detail_heading}</div>', unsafe_allow_html=True)
    rule_items = [
        ("Rule", _quality_rule_label(result.rule_type)),
        ("Column / Scope", result.column),
        ("Expected Condition", _quality_expected_condition(result)),
    ]
    rule_items.extend(_quality_configuration_lines(result))
    summary_items = [("Status", result.status)]
    if result.status == "FAIL":
        summary_items.extend(
            [
                ("Total Records", f"{result.total_records:,}"),
                ("Passed Records", f"{result.passed_records:,}"),
                ("Failed Records", f"{result.failed_records:,}"),
                ("Failure %", _format_quality_percent(result.failure_percentage)),
            ]
        )
    summary_items.append(("Message", _quality_result_message(result)))
    with st.container(key="quality-review-detail-panels"):
        detail_columns = st.columns(2, gap="large")
        with detail_columns[0]:
            rule_html = ''.join(
                f'<div class="quality-detail-row"><span>{escape(label)}</span><strong>{escape(value)}</strong></div>'
                for label, value in rule_items
            )
            st.markdown(
                f'<div class="quality-detail-panel card-decoration-data-grid"><div class="card-content"><div class="quality-detail-panel-title">RULE DETAILS</div>{rule_html}</div></div>',
                unsafe_allow_html=True,
            )
        with detail_columns[1]:
            summary_html = ''.join(
                f'<div class="quality-detail-row"><span>{escape(label)}</span><strong>{escape(value)}</strong></div>'
                if label != "Status"
                else f'<div class="quality-detail-row"><span>{escape(label)}</span>{_quality_status_cell(value, {})}</div>'
                for label, value in summary_items
            )
            st.markdown(
                f'<div class="quality-detail-panel card-decoration-quality-signal"><div class="card-content"><div class="quality-detail-panel-title">{"FAILURE SUMMARY" if result.status == "FAIL" else "ERROR SUMMARY"}</div>{summary_html}</div></div>',
                unsafe_allow_html=True,
            )
    if result.status != "FAIL":
        return

    run_id = st.session_state.get(QUALITY_RESULT_RUN_ID_KEY, "")
    cache_key = "|".join((str(run_id), result.rule_type, result.column, json.dumps(result.rule_config, sort_keys=True, default=str)))
    connector = _active_connector_for(selected_table)
    if connector is None:
        st.info("A live source connection is required to inspect detailed failure records.")
        return
    rule_payload = {"rule_type": result.rule_type, "column": result.column, **result.rule_config}

    if result.rule_type == "not_null":
        st.info(f"Failed condition: NULL · {result.failed_records:,} failed records")
    else:
        detail_cache = st.session_state.setdefault(QUALITY_REVIEW_DETAIL_CACHE_KEY, {})
        if cache_key not in detail_cache:
            try:
                detail_cache[cache_key] = QualityRuleEngine().inspect_failed_values(
                    connector, selected_table, rule_payload, limit=FAILURE_DETAIL_LIMIT
                )
            except Exception as exc:
                detail_cache[cache_key] = {"error": safe_connection_error(str(exc))}
        detail = detail_cache[cache_key]
        if isinstance(detail, dict) and "error" in detail:
            st.info(f"Detailed failure values could not be loaded: {detail['error']}")
        elif not detail:
            st.caption("No grouped failure values are available for this rule.")
        else:
            st.markdown('<div class="section-kicker quality-detail-heading">FAILED VALUES</div>', unsafe_allow_html=True)
            render_html_table(
                [{"Failed Value": "NULL" if item["failed_value"] is None else item["failed_value"], "Count": f'{item["failure_count"]:,}'} for item in detail],
                table_id="quality-failed-values",
                download=False,
                column_widths=[75, 25],
                max_visible_rows=4,
                sticky_header=True,
                scrollable=True,
            )

    is_records_open = st.session_state.get(QUALITY_REVIEW_RULE_RECORDS_OPEN_KEY) == cache_key
    record_toggle_key = f"quality-view-failed-records-{re.sub(r'[^A-Za-z0-9_-]+', '-', cache_key)[:120]}"
    if st.button(
        "Hide Failed Records" if is_records_open else "View Failed Records",
        key=record_toggle_key,
        icon=":material/expand_less:" if is_records_open else ":material/expand_more:",
        type="tertiary",
    ):
        st.session_state[QUALITY_REVIEW_RULE_RECORDS_OPEN_KEY] = None if is_records_open else cache_key
        st.rerun()
    if not is_records_open:
        return

    record_cache = st.session_state.setdefault(QUALITY_REVIEW_RECORD_CACHE_KEY, {})
    if cache_key not in record_cache:
        try:
            engine = QualityRuleEngine()
            record_cache[cache_key] = {
                "view": engine.inspect_failed_records(
                    connector, selected_table, rule_payload, limit=QUALITY_FAILED_RECORD_VIEW_LIMIT
                ),
                "all": engine.inspect_failed_records(connector, selected_table, rule_payload, limit=None),
            }
        except Exception as exc:
            record_cache[cache_key] = {"error": safe_connection_error(str(exc))}
    records = record_cache[cache_key]
    if isinstance(records, dict) and "error" in records:
        st.info(f"Failed records could not be loaded: {records['error']}")
        return
    all_records = records.get("all", [])
    view_records = records.get("view", [])
    if len(all_records) != result.failed_records:
        st.warning(
            f"The source returned {len(all_records):,} failed records, but the quality result reports "
            f"{result.failed_records:,}. Review is unavailable until the counts agree."
        )
        return
    if not all_records:
        return
    st.markdown('<div class="section-kicker quality-detail-heading">FAILED RECORDS</div>', unsafe_allow_html=True)
    context_columns = st.columns([1, 0.34], vertical_alignment="center")
    with context_columns[0]:
        st.caption(f"{len(all_records):,} failed records · Showing up to {len(view_records):,} rows")
        st.caption("Live source rows for the current quality run; historical row snapshots are not persisted.")
    with context_columns[1]:
        filename_parts = [
            "failed_records", selected_table.source_type, selected_table.database_name,
            selected_table.schema_name, selected_table.table_name, result.rule_type, result.column,
            datetime.now().strftime("%Y%m%d"),
        ]
        filename = re.sub(r"[^A-Za-z0-9._-]+", "_", "_".join(str(part) for part in filename_parts)).strip("._") + ".csv"
        with st.container(key="quality-failed-records-download"):
            st.download_button(
                "Download Failed Records",
                data=table_to_csv(all_records),
                file_name=filename,
                mime="text/csv",
                icon=":material/download:",
                key=f"quality_failed_records_download_{cache_key}",
                type="tertiary",
            )
    render_html_table(
        view_records,
        table_id="quality-failed-records",
        download=False,
        max_visible_rows=7,
        sticky_header=True,
        scrollable=True,
        table_class="failed-records",
        fill_available_width=True,
    )


def _render_all_failed_records(selected_table: TableMetadata, report: QualityReport) -> None:
    failed_results = [result for result in report.results if result.status == "FAIL" and result.failed_records > 0]
    if not failed_results:
        return

    is_open = bool(st.session_state.get(QUALITY_REVIEW_ALL_RECORDS_OPEN_KEY, False))
    if st.button(
        "Hide All Failed Records" if is_open else "View All Failed Records",
        key="quality-view-all-failed-records",
        icon=":material/expand_less:" if is_open else ":material/expand_more:",
        type="tertiary",
    ):
        st.session_state[QUALITY_REVIEW_ALL_RECORDS_OPEN_KEY] = not is_open
        st.rerun()
    if not is_open:
        return

    run_id = st.session_state.get(QUALITY_RESULT_RUN_ID_KEY, "")
    cache_key = f"{run_id}|{_dataset_id(selected_table)}"
    record_cache = st.session_state.setdefault(QUALITY_REVIEW_ALL_RECORD_CACHE_KEY, {})
    if cache_key not in record_cache:
        connector = _active_connector_for(selected_table)
        if connector is None:
            st.info("A live source connection is required to inspect all failed records.")
            return
        try:
            record_cache[cache_key] = QualityRuleEngine().inspect_all_failed_records(
                connector, selected_table, failed_results, rule_label=_quality_rule_label
            )
        except Exception as exc:
            record_cache[cache_key] = {"error": safe_connection_error(str(exc))}
    records = record_cache[cache_key]
    if isinstance(records, dict) and "error" in records:
        st.info(f"All failed records could not be loaded: {records['error']}")
        return
    if not records:
        st.info("No failed source records are available for this quality run.")
        return

    st.markdown('<div class="section-kicker quality-detail-heading">ALL FAILED RECORDS</div>', unsafe_allow_html=True)
    context_columns = st.columns([1, 0.4], vertical_alignment="center")
    with context_columns[0]:
        st.caption(f"{len(records):,} unique failed records · Current quality run")
        st.caption("Rows are deduplicated by complete source-row values; historical row snapshots are not persisted.")
    with context_columns[1]:
        filename_parts = [
            "all_failed_records", selected_table.source_type, selected_table.database_name,
            selected_table.schema_name, selected_table.table_name, datetime.now().strftime("%Y%m%d"),
        ]
        filename = re.sub(r"[^A-Za-z0-9._-]+", "_", "_".join(str(part) for part in filename_parts)).strip("._") + ".csv"
        with st.container(key="quality-all-failed-records-download"):
            st.download_button(
                "Download All Failed Records",
                data=table_to_csv(records),
                file_name=filename,
                mime="text/csv",
                icon=":material/download:",
                key="quality_all_failed_records_download",
                type="tertiary",
            )
    render_html_table(
        records[:QUALITY_FAILED_RECORD_VIEW_LIMIT],
        table_id="quality-all-failed-records",
        download=False,
        max_visible_rows=7,
        sticky_header=True,
        scrollable=True,
        table_class="failed-records-with-reason",
        fill_available_width=True,
    )


def _render_quality_review(selected_table: TableMetadata) -> None:
    report = st.session_state.get(QUALITY_RESULT_KEY)
    if not st.session_state.get(QUALITY_REVIEW_READY_KEY) or not isinstance(report, QualityReport):
        return
    if (
        st.session_state.get(QUALITY_RESULT_DATASET_KEY) != _dataset_id(selected_table)
        or st.session_state.get(QUALITY_RESULT_RULE_SIGNATURE_KEY) != st.session_state.get(QUALITY_RULE_SIGNATURE_KEY)
    ):
        return

    st.markdown('<div class="section-kicker">QUALITY RESULTS</div>', unsafe_allow_html=True)
    st.caption(f"{_dataset_label(selected_table)} · {report.total_rules:,} checks evaluated")
    summary_cards = [
        ("Quality Score", "—" if report.quality_score is None else _format_quality_percent(report.quality_score), "Engine-provided overall score"),
        ("Passed Checks", f"{report.passed_rules:,}", "Rules with PASS status"),
        ("Failed Checks", f"{report.failed_rules:,}", "Rules with FAIL status"),
        ("Error Checks", f"{report.error_rules:,}", "Rules with ERROR status"),
        ("Total Checks", f"{report.total_rules:,}", "All executed rule results"),
    ]
    summary_columns = st.columns(len(summary_cards))
    result_decorations = {
        "Quality Score": "quality-signal",
        "Passed Checks": "verified-path",
        "Failed Checks": "broken-path",
        "Error Checks": "signal-path",
        "Total Checks": "check-grid",
    }
    for column, (label, value, detail) in zip(summary_columns, summary_cards):
        with column:
            decoration = result_decorations[label]
            st.markdown(
                f'<div class="metric-card card-decoration-{decoration}"><div class="card-content"><div class="metric-value">{escape(value)}</div>'
                f'<div class="metric-label">{escape(label)}</div><div class="metric-detail">{escape(detail)}</div></div></div>',
                unsafe_allow_html=True,
            )

    score_value = 0.0 if report.quality_score is None else max(0.0, min(float(report.quality_score), 100.0))
    total_rules = max(report.total_rules, 1)
    status_bars = (
        ("PASS", report.passed_rules, "pass"),
        ("FAIL", report.failed_rules, "fail"),
        ("ERROR", report.error_rules, "error"),
    )
    with st.container(key="quality-review-visual-summary"):
        visual_columns = st.columns(2, gap="large")
        with visual_columns[0]:
            st.markdown(
                f'<div class="quality-visual-panel card-decoration-quality-signal"><div class="card-content"><div class="quality-visual-title">OVERALL QUALITY</div>'
                f'<div class="quality-visual-score">{escape("—" if report.quality_score is None else _format_quality_percent(report.quality_score))}</div>'
                f'<div class="quality-progress-track"><div class="quality-progress-fill" style="width:{score_value:.2f}%"></div></div></div></div>',
                unsafe_allow_html=True,
            )
        with visual_columns[1]:
            bars_html = ''.join(
                f'<div class="quality-status-bar"><span class="quality-status-bar-label quality-status-bar-label--{kind}">{label}</span>'
                f'<span class="quality-status-bar-track"><span class="quality-status-bar-fill quality-status-bar-fill--{kind}" style="width:{(count / total_rules) * 100:.2f}%"></span></span>'
                f'<strong>{count:,}</strong></div>'
                for label, count, kind in status_bars
            )
            st.markdown(
                f'<div class="quality-visual-panel card-decoration-quality-signal"><div class="card-content"><div class="quality-visual-title">RULE STATUS DISTRIBUTION</div>{bars_html}</div></div>',
                unsafe_allow_html=True,
            )

    result_rows = []
    for result in report.results:
        result_rows.append(
            {
                "Rule": _quality_rule_label(result.rule_type),
                "Column / Scope": result.column,
                "Status": result.status,
                "Total Records": f"{result.total_records:,}",
                "Passed": f"{result.passed_records:,}",
                "Failed": f"{result.failed_records:,}",
                "Failure %": _format_quality_percent(result.failure_percentage),
                "Message": _quality_result_message(result),
            }
        )
    st.markdown('<div class="section-kicker quality-results-heading">RULE RESULTS</div>', unsafe_allow_html=True)
    render_html_table(
        result_rows,
        table_id="quality-results",
        download=False,
        column_widths=[14, 18, 12, 10, 10, 12, 10, 14],
        table_class="quality-result-table",
        cell_renderers={
            "Rule": _table_badge,
            "Column / Scope": _table_identifier,
            "Status": _quality_status_cell,
            "Message": _table_secondary,
        },
    )
    _render_all_failed_records(selected_table, report)
    detail_results = [result for result in report.results if result.status in {"FAIL", "ERROR"}]
    if detail_results:
        detail_placeholder = "Select a failed or errored rule"
        detail_options = [detail_placeholder] + [
            f"{_quality_rule_label(result.rule_type)} · {result.column} · {result.status}"
            for result in detail_results
        ]
        if st.session_state.get(QUALITY_REVIEW_DETAIL_KEY) not in detail_options:
            st.session_state[QUALITY_REVIEW_DETAIL_KEY] = detail_placeholder
        selected_detail = st.selectbox(
            "Inspect rule details",
            detail_options,
            key=QUALITY_REVIEW_DETAIL_KEY,
        )
        if selected_detail != detail_placeholder:
            selected_index = detail_options.index(selected_detail) - 1
            _render_quality_result_detail(selected_table, detail_results[selected_index])


def _history_timestamp(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.astimezone().strftime("%d %b %Y, %I:%M %p").lstrip("0")
    except (TypeError, ValueError):
        return value


def _render_quality_history(selected_table: TableMetadata) -> None:
    st.markdown('<div class="section-kicker quality-history-heading">QUALITY HISTORY</div>', unsafe_allow_html=True)
    st.caption(f"Persisted quality runs for {_dataset_label(selected_table)}")
    try:
        runs = QualityRunRepository().list_quality_runs_for_dataset(
            selected_table.source_type,
            selected_table.database_name,
            selected_table.schema_name,
            selected_table.table_name,
            user_id=current_user_id(),
        )[:QUALITY_HISTORY_LIMIT]
    except Exception:
        st.warning("Quality run history is temporarily unavailable.")
        return
    if not runs:
        st.info("No quality run history is available for this dataset yet.")
        return

    chronological = list(reversed(runs))
    scored_runs = [run for run in chronological if run.report.quality_score is not None]
    with st.container(key="quality-history-summary"):
        history_columns = st.columns(2, gap="large")
        with history_columns[0]:
            with st.container(key="quality-history-trend"):
                st.markdown('<div class="quality-history-panel-title">QUALITY SCORE TREND</div>', unsafe_allow_html=True)
                if len(scored_runs) < 2:
                    st.info("Run quality checks again to build a quality trend.")
                    st.markdown('<div class="quality-empty-trend-art" aria-hidden="true"></div>', unsafe_allow_html=True)
                else:
                    trend_svg = build_quality_trend_svg(
                        [(_history_timestamp(run.executed_at), run.report.quality_score) for run in scored_runs]
                    )
                    if trend_svg is None:
                        st.info("Quality score trend is unavailable for the stored history.")
                    else:
                        st.markdown(trend_svg, unsafe_allow_html=True)
                    st.caption("Oldest run → newest run · score scale 0–100")
        with history_columns[1]:
            latest = runs[0].report
            latest_items = [
                ("Run Time", _history_timestamp(runs[0].executed_at)),
                ("Quality Score", "—" if latest.quality_score is None else _format_quality_percent(latest.quality_score)),
                ("Passed", f"{latest.passed_rules:,}"),
                ("Failed", f"{latest.failed_rules:,}"),
                ("Errors", f"{latest.error_rules:,}"),
                ("Total", f"{latest.total_rules:,}"),
            ]
            latest_html = ''.join(
                f'<div class="quality-history-latest-row"><span>{escape(label)}</span><strong>{escape(value)}</strong></div>'
                for label, value in latest_items
            )
            st.markdown(
                f'<div class="quality-history-latest card-decoration-quality-signal"><div class="card-content"><div class="quality-history-panel-title">LATEST RUN</div>{latest_html}</div></div>',
                unsafe_allow_html=True,
            )

    recent_rows = [
        {
            "Run Time": _history_timestamp(run.executed_at),
            "Quality Score": "—" if run.report.quality_score is None else _format_quality_percent(run.report.quality_score),
            "Passed": f"{run.report.passed_rules:,}",
            "Failed": f"{run.report.failed_rules:,}",
            "Errors": f"{run.report.error_rules:,}",
            "Total": f"{run.report.total_rules:,}",
        }
        for run in runs
    ]
    st.markdown('<div class="section-kicker quality-history-table-heading">RECENT RUNS</div>', unsafe_allow_html=True)
    render_html_table(
        recent_rows,
        table_id="quality-recent-runs",
        download=False,
        column_widths=[34, 17, 12, 12, 12, 13],
        max_visible_rows=5,
        sticky_header=True,
        scrollable=True,
    )


def _remove_common_rule(index: int) -> None:
    st.session_state[QUALITY_COMMON_RULES_KEY].pop(index)
    _invalidate_execution_result()
    st.rerun()


def _remove_business_rule(index: int) -> None:
    removed_rule = st.session_state[QUALITY_RULES_KEY].pop(index)
    dataset_id = st.session_state.get(QUALITY_DATASET_KEY)
    if dataset_id in st.session_state.get(QUALITY_AI_ACCEPTED_KEY, {}):
        st.session_state[QUALITY_AI_ACCEPTED_KEY][dataset_id].discard(_rule_identity(removed_rule))
    _invalidate_execution_result()
    st.rerun()


def _add_ai_rule(index: int) -> None:
    result = st.session_state.get(QUALITY_AI_RESULT_KEY)
    dataset_id = st.session_state.get(QUALITY_DATASET_KEY)
    if not isinstance(result, AISuggestionResult) or result.status != "SUCCESS" or not dataset_id:
        return
    if index < 0 or index >= len(result.suggestions):
        return

    rule = result.suggestions[index].rule
    identity = _rule_identity(rule)
    if identity in _prepared_rule_identities():
        st.session_state[QUALITY_AI_DUPLICATE_NOTICE_KEY] = (
            dataset_id,
            "This rule is already included in the prepared checks.",
        )
        st.rerun()
        return

    st.session_state[QUALITY_RULES_KEY].append(rule.model_dump())
    _accepted_ai_identities(dataset_id).add(identity)
    st.session_state["quality_ai_acceptance_notice"] = "AI suggestion added to Business Rules."
    _invalidate_execution_result()
    st.rerun()


def _ai_action_label(index: int, dataset_id: str) -> str:
    result = st.session_state.get(QUALITY_AI_RESULT_KEY)
    if not isinstance(result, AISuggestionResult) or index >= len(result.suggestions):
        return "Add Rule"
    identity = _rule_identity(result.suggestions[index].rule)
    return "Added" if identity in _prepared_rule_identities() else "Add Rule"


def _ai_action_disabled(index: int, dataset_id: str) -> bool:
    result = st.session_state.get(QUALITY_AI_RESULT_KEY)
    if not isinstance(result, AISuggestionResult) or index >= len(result.suggestions):
        return True
    return _rule_identity(result.suggestions[index].rule) in _prepared_rule_identities()


render_page_header(
    "Data Quality",
    "Validate trusted datasets with deterministic quality rules.",
    "Configure checks against cataloged metadata before executing them on the source system.",
    icon="quality",
)

render_get_started_workflow(
    [("catalog", "SELECT"), ("quality", "PREPARE"), ("search", "RUN"), ("report", "REVIEW")],
    class_name="get-started-workflow metadata-scan-workflow",
)

render_connected_sources_table()

try:
    all_catalog = MetadataRepository().list_tables(current_user_id())
except Exception:
    st.error("Unable to load cataloged datasets.")
    st.stop()

history_dataset_id = st.session_state.get(QUALITY_HISTORY_DATASET_KEY)
history_table = next((table for table in all_catalog if _dataset_id(table) == history_dataset_id), None)
catalog = all_catalog
catalog, has_active_connections = _connected_catalog_tables(catalog)
if not has_active_connections:
    _invalidate_execution_result()
    for key in (QUALITY_DATASET_KEY, QUALITY_RULES_KEY, QUALITY_COMMON_RULES_KEY):
        st.session_state.pop(key, None)
    _close_business_form()
    st.session_state["quality_table"] = CHOOSE_DATASET
    render_empty_state(
        "No active connections",
        "Connect a data source before running quality checks.",
        "quality",
    )
    st.page_link("pages/1_connections.py", label="Manage Connections", icon=":material/database:")
    if history_table is not None:
        _render_quality_history(history_table)
    st.stop()
if not catalog:
    _invalidate_execution_result()
    for key in (QUALITY_DATASET_KEY, QUALITY_RULES_KEY, QUALITY_COMMON_RULES_KEY):
        st.session_state.pop(key, None)
    _close_business_form()
    st.session_state["quality_table"] = CHOOSE_DATASET
    render_empty_state(
        "No cataloged datasets are available for the connected source.",
        "Scan a table from Metadata Scan before running quality checks.",
        "quality",
    )
    st.page_link("pages/2_metadata_scan.py", label="Go to Metadata Scan", icon=":material/manage_search:")
    if history_table is not None:
        _render_quality_history(history_table)
    st.stop()

st.markdown('<div class="section-kicker">SELECT DATASET</div>', unsafe_allow_html=True)
table_options = {_dataset_id(table): table for table in catalog}
table_ids = [CHOOSE_DATASET] + list(table_options)
restored_quality_dataset = st.session_state.get(QUALITY_DATASET_KEY)
if st.session_state.get("quality_table") not in table_ids:
    st.session_state["quality_table"] = (
        restored_quality_dataset if restored_quality_dataset in table_options else CHOOSE_DATASET
    )
selected_id = st.selectbox(
    "Dataset",
    table_ids,
    key="quality_table",
    format_func=lambda value: CHOOSE_DATASET if value == CHOOSE_DATASET else _dataset_label(table_options[value]),
)

if selected_id == CHOOSE_DATASET:
    _invalidate_execution_result()
    st.session_state.pop(QUALITY_DATASET_KEY, None)
    st.session_state.pop(QUALITY_RULES_KEY, None)
    st.session_state.pop(QUALITY_COMMON_RULES_KEY, None)
    _close_business_form()
    st.caption("Choose a dataset to prepare common checks and business rules.")
    st.stop()

selected_table = table_options[selected_id]

if st.session_state.get(QUALITY_DATASET_KEY) != selected_id:
    _invalidate_execution_result()
    st.session_state.pop(QUALITY_AI_RESULT_KEY, None)
    st.session_state.pop(QUALITY_AI_RESULT_DATASET_KEY, None)
    st.session_state.pop(QUALITY_AI_IN_PROGRESS_KEY, None)
    st.session_state.pop(QUALITY_AI_DUPLICATE_NOTICE_KEY, None)
    st.session_state[QUALITY_DATASET_KEY] = selected_id
    st.session_state[QUALITY_RULES_KEY] = []
    _close_business_form()
    st.session_state[QUALITY_COMMON_RULES_KEY] = _common_rules(selected_table)
if QUALITY_RULES_KEY not in st.session_state:
    st.session_state[QUALITY_RULES_KEY] = []
if QUALITY_COMMON_RULES_KEY not in st.session_state:
    st.session_state[QUALITY_COMMON_RULES_KEY] = _common_rules(selected_table)
if QUALITY_FORM_OPEN_KEY not in st.session_state:
    st.session_state[QUALITY_FORM_OPEN_KEY] = False

current_rule_signature = _rule_signature(
    st.session_state[QUALITY_COMMON_RULES_KEY],
    st.session_state[QUALITY_RULES_KEY],
)
if st.session_state.get(QUALITY_RULE_SIGNATURE_KEY) not in (None, current_rule_signature):
    _invalidate_execution_result()
st.session_state[QUALITY_RULE_SIGNATURE_KEY] = current_rule_signature

st.markdown('<div class="section-kicker">SELECTED DATASET</div>', unsafe_allow_html=True)
context_columns = st.columns(6)
context_values = [
    ("Source", _source_name(selected_table.source_type)),
    ("Database", selected_table.database_name),
    ("Schema", selected_table.schema_name),
    ("Table", selected_table.table_name),
    ("Rows", "-" if selected_table.row_count is None else f"{selected_table.row_count:,}"),
    ("Columns", f"{len(selected_table.columns):,}"),
]
for column, (label, value) in zip(context_columns, context_values):
    with column:
        decoration = {
            "Source": "data-nodes",
            "Database": "data-grid",
            "Schema": "data-grid",
            "Table": "data-nodes",
            "Rows": "data-grid",
            "Columns": "data-nodes",
        }[label]
        st.markdown(f'<div class="quality-context-item card-decoration-{decoration}"><div class="card-content"><span>{label}</span><strong>{value}</strong></div></div>', unsafe_allow_html=True)

common_rules = st.session_state[QUALITY_COMMON_RULES_KEY]
st.markdown('<div class="section-kicker">COMMON CHECKS</div>', unsafe_allow_html=True)
st.caption(f"{len(common_rules)} checks prepared from dataset metadata.")
if common_rules:
    common_rows = []
    for payload in common_rules:
        label, column, _ = _rule_summary(payload)
        reason = "All profiled values are distinct" if payload.get("rule_type") == "unique" else "Required by source metadata"
        common_rows.append({"Rule": label, "Column / Scope": column, "Reason": reason, "Action": ""})
    render_html_table(
        common_rows,
        table_id="quality-common-checks",
        download=False,
        column_widths=[20, 25, 47, 8],
        cell_renderers={"Rule": _table_badge, "Column / Scope": _table_identifier, "Reason": _table_secondary},
        action={"header": "Action", "icon": ":material/remove_circle_outline:", "key_prefix": "remove-common-rule", "help": "Remove check", "callback": _remove_common_rule},
    )
else:
    st.markdown(
        '<div class="quality-common-empty">No common checks could be inferred from this dataset metadata.</div>',
        unsafe_allow_html=True,
    )
with st.container(key="quality-reset-common-checks"):
    if st.button("Reset Common Checks", type="primary", icon=":material/refresh:", key="reset-common-rules"):
        st.session_state[QUALITY_COMMON_RULES_KEY] = _common_rules(selected_table)
        _invalidate_execution_result()
        st.rerun()

st.markdown('<div class="section-kicker">BUSINESS RULES</div>', unsafe_allow_html=True)
st.caption("Add dataset-specific rules that cannot be inferred automatically.")
if not st.session_state[QUALITY_FORM_OPEN_KEY]:
    with st.container(key="quality-add-business-rule"):
        if st.button("Add Business Rule", icon=":material/add:", key="open-quality-rule-form", type="primary"):
            st.session_state[QUALITY_FORM_OPEN_KEY] = True
            st.rerun()
else:
    column_options = [SELECT_COLUMN] + [column.column_name for column in selected_table.columns]
    selected_column = st.selectbox(
        "Column",
        column_options,
        index=0,
        key="quality_rule_column",
        format_func=lambda value: SELECT_COLUMN if value == SELECT_COLUMN else _column_label(selected_table, value),
    )
    previous_column = st.session_state.get(QUALITY_LAST_COLUMN_KEY)
    if selected_column != previous_column:
        _clear_rule_type_and_configuration()
    st.session_state[QUALITY_LAST_COLUMN_KEY] = None if selected_column == SELECT_COLUMN else selected_column

    if selected_column == SELECT_COLUMN:
        st.caption("Select a column to choose an applicable rule type.")
    else:
        rule_type_options = [SELECT_RULE_TYPE] + _rule_types_for_column(selected_table, selected_column)
        selected_rule_type = st.selectbox(
            "Rule Type",
            rule_type_options,
            index=0,
            key="quality_rule_type",
        )
        previous_rule_type = st.session_state.get(QUALITY_LAST_TYPE_KEY)
        if selected_rule_type != previous_rule_type:
            _clear_rule_configuration()
        st.session_state[QUALITY_LAST_TYPE_KEY] = None if selected_rule_type == SELECT_RULE_TYPE else selected_rule_type

        if selected_rule_type == SELECT_RULE_TYPE:
            st.caption("Select a rule type to configure the check.")
        else:
            rule_name = selected_rule_type
            column = selected_column
            st.caption(BUSINESS_RULE_DEFINITIONS[rule_name][1])
            input_columns = st.columns(2)
            values: dict[str, Any] = {}
            configuration_valid = True
            if rule_name == "Accepted Values":
                values["accepted_values"] = st.text_input("Accepted Values", placeholder="ACTIVE, INACTIVE", key="quality_accepted_values")
                configuration_valid = bool(values["accepted_values"].strip())
            elif rule_name == "Numeric Range":
                with input_columns[0]:
                    values["min_value"] = st.text_input("Minimum", placeholder="Optional", key="quality_min_value")
                with input_columns[1]:
                    values["max_value"] = st.text_input("Maximum", placeholder="Optional", key="quality_max_value")
                configuration_valid = bool(values["min_value"].strip() or values["max_value"].strip())
            elif rule_name == "String Length":
                with input_columns[0]:
                    values["min_length"] = st.text_input("Minimum Length", placeholder="Optional", key="quality_min_length")
                with input_columns[1]:
                    values["max_length"] = st.text_input("Maximum Length", placeholder="Optional", key="quality_max_length")
                configuration_valid = bool(values["min_length"].strip() or values["max_length"].strip())
            elif rule_name == "Freshness":
                values["max_age_days"] = st.number_input("Maximum Age (days)", min_value=0, value=30, step=1, key="quality_max_age_days")

            with st.container(key="quality-form-actions"):
                action_columns = st.columns([1.15, 0.8, 4.05], gap="small")
                with action_columns[0]:
                    with st.container(key="quality-add-rule-button"):
                        add_rule = st.button("Add Rule", type="primary", icon=":material/add:", key="quality_add_rule", disabled=not configuration_valid)
                with action_columns[1]:
                    cancel_rule = st.button("Cancel", type="secondary", key="cancel-quality-rule")
            if cancel_rule:
                _close_business_form()
                st.rerun()
            if add_rule:
                try:
                    rule = _build_rule(rule_name, column, values)
                    payload = rule.model_dump()
                    if payload in st.session_state[QUALITY_RULES_KEY]:
                        st.info("This exact business rule is already configured.")
                    else:
                        st.session_state[QUALITY_RULES_KEY].append(payload)
                        _close_business_form()
                        st.rerun()
                except (ValidationError, ValueError) as exc:
                    st.error(str(exc))

st.markdown('<div class="section-kicker">CONFIGURED BUSINESS RULES</div>', unsafe_allow_html=True)
business_rules = st.session_state.get(QUALITY_RULES_KEY, [])
if not business_rules:
    st.caption("No business rules configured for this dataset.")
else:
    business_rows = []
    for payload in business_rules:
        label, column, details = _rule_summary(payload)
        business_rows.append({"Rule": label, "Column": column, "Configuration": details or "—", "Action": ""})
    render_html_table(
        business_rows,
        table_id="quality-business-rules",
        download=False,
        column_widths=[22, 23, 47, 8],
        cell_renderers={"Rule": _table_badge, "Column": _table_identifier, "Configuration": _table_secondary},
        action={"header": "Action", "icon": ":material/delete_outline:", "key_prefix": "remove-quality-rule", "help": "Remove business rule", "callback": _remove_business_rule},
    )

_render_ai_suggestions(selected_table)

st.markdown('<div class="section-kicker">CHECK SUMMARY</div>', unsafe_allow_html=True)
summary_columns = st.columns(3)
for column, (label, value) in zip(summary_columns, [("Common Checks", len(common_rules)), ("Business Rules", len(business_rules)), ("Total Checks", len(common_rules) + len(business_rules))]):
    with column:
        decoration = {"Common Checks": "quality-signal", "Business Rules": "data-nodes", "Total Checks": "data-grid"}[label]
        st.markdown(f'<div class="quality-count-item card-decoration-{decoration}"><div class="card-content"><span>{label}</span><strong>{value}</strong></div></div>', unsafe_allow_html=True)

with st.container(key="quality-run-quality-checks"):
    run_quality_checks = st.button(
        "Run Quality Checks",
        type="primary",
        disabled=not (selected_id != CHOOSE_DATASET and bool(common_rules or business_rules))
        or st.session_state.get(QUALITY_RUN_IN_PROGRESS_KEY, False),
        icon=":material/play_arrow:",
        key="run-quality-checks",
    )
if run_quality_checks:
    _run_quality_checks(selected_table, common_rules, business_rules)

_render_quality_review(selected_table)
_render_quality_history(selected_table)
