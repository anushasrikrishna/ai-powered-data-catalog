from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import re
from typing import Any

from documentation.models import TableDocumentation
from documentation.summarizer import MetadataDocumentationGenerator
from quality.rule_engine import QualityReport, QualityResult


@dataclass(frozen=True)
class ReportMetadataSummary:
    total_columns: int
    non_nullable_columns: int
    nullable_columns: int
    numeric_columns: int
    date_datetime_columns: int


@dataclass(frozen=True)
class ReportContext:
    """Single persisted-data view model shared by preview and export renderers."""

    documentation: TableDocumentation
    report: QualityReport
    run_id: str
    executed_at: str
    historical_runs: tuple[tuple[str, QualityReport], ...]


def build_metadata_summary(documentation: TableDocumentation) -> ReportMetadataSummary:
    summary = documentation.summary
    return ReportMetadataSummary(
        total_columns=summary.column_count,
        non_nullable_columns=summary.non_nullable_column_count,
        nullable_columns=summary.nullable_column_count,
        numeric_columns=summary.numeric_column_count,
        date_datetime_columns=summary.date_column_count + summary.datetime_column_count,
    )


def build_report_context(table: Any, run: Any, all_runs: list[Any]) -> ReportContext:
    documentation = MetadataDocumentationGenerator().generate(table)
    return ReportContext(
        documentation=documentation,
        report=run.report,
        run_id=run.run_id,
        executed_at=run.executed_at,
        historical_runs=tuple((item.executed_at, item.report) for item in reversed(all_runs)),
    )


def _distinct_ratio(column: Any, row_count: int | None) -> float | None:
    if column.distinct_count is None or row_count is None or row_count <= 0:
        return None
    return column.distinct_count / row_count


def build_column_profiles(documentation: TableDocumentation) -> list[dict[str, Any]]:
    return [
        {
            "Column": column.column_name,
            "Type": column.normalized_data_type,
            "Nullable": "Yes" if column.nullable else "No",
            "Null Count": column.null_count,
            "Distinct Count": column.distinct_count,
            "Distinct Ratio": _distinct_ratio(column, documentation.summary.row_count),
            "Min": column.minimum,
            "Max": column.maximum,
        }
        for column in documentation.columns
    ]


def format_profile_value(value: Any, normalized_type: str) -> str:
    """Format persisted profile bounds for display without changing their values."""
    if value is None:
        return "—"
    kind = str(normalized_type or "").upper()
    if kind == "DATE":
        parsed = _parse_temporal(value)
        return parsed.strftime("%d %b %Y") if parsed is not None else str(value)
    if kind == "DATETIME":
        parsed = _parse_temporal(value)
        return parsed.strftime("%d %b %Y, %I:%M %p") if parsed is not None else str(value)
    return str(value)


def _parse_temporal(value: Any) -> date | datetime | None:
    if isinstance(value, (date, datetime)):
        return value
    if not isinstance(value, str):
        return None
    text = value.strip()
    try:
        if "T" not in text and " " not in text:
            return date.fromisoformat(text)
        # Python accepts microseconds up to six digits; persisted source values
        # can contain seven fractional digits, so trim only the extra precision.
        normalized = re.sub(r"(\.\d{6})\d+(?=(?:Z|[+-]\d\d:?\d\d)?$)", r"\1", text)
        return datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError:
        return None


def failed_results(report: QualityReport) -> list[QualityResult]:
    return sorted(
        (result for result in report.results if result.status in {"FAIL", "ERROR"}),
        key=lambda result: (
            0 if result.status == "ERROR" else 1,
            -(result.failure_percentage if result.failure_percentage is not None else 0),
            -result.failed_records,
        ),
    )


def quality_health(score: float | None) -> str | None:
    if score is None:
        return None
    if score >= 95:
        return "Excellent"
    if score >= 85:
        return "Good"
    if score >= 70:
        return "Needs Attention"
    return "Poor"


__all__ = [
    "ReportMetadataSummary",
    "ReportContext",
    "build_report_context",
    "build_column_profiles",
    "build_metadata_summary",
    "failed_results",
    "format_profile_value",
    "quality_health",
]
