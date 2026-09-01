from __future__ import annotations

from datetime import datetime
from html import escape
import re
from typing import Any

from ui.report_view import ReportContext, build_column_profiles, build_metadata_summary, failed_results, format_profile_value, quality_health
from ui.quality_trend import build_quality_trend_svg

PDF_TABLE_HEADER_BACKGROUND = "#192B37"


def _source_name(source_type: str) -> str:
    return {"sqlserver": "SQL Server", "postgresql": "PostgreSQL", "snowflake": "Snowflake"}.get(source_type.casefold(), source_type)


def _rule_label(rule_type: str) -> str:
    return {"not_null": "Not Null", "unique": "Unique", "duplicate": "Duplicate", "accepted_values": "Accepted Values", "numeric_range": "Numeric Range", "string_length": "String Length", "freshness": "Freshness"}.get(rule_type, rule_type.replace("_", " ").title())


def _timestamp(value: str) -> str:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone().strftime("%d %b %Y, %I:%M %p").lstrip("0")
    except (TypeError, ValueError):
        return value


def _percent(value: float | None) -> str:
    return "—" if value is None else f"{value:g}%"


def _text(value: Any) -> str:
    return "—" if value is None else str(value)


def build_export_filename(context: ReportContext, extension: str, generated_on: datetime | None = None) -> str:
    date_text = (generated_on or datetime.now()).strftime("%Y-%m-%d")
    parts = [context.documentation.database_name, context.documentation.schema_name, context.documentation.table_name, "quality_report", date_text]
    safe = re.sub(r'[<>:"/\\|?*]+', "_", "_".join(str(part).strip() for part in parts)).strip(" ._")
    return f"{safe}.{extension.lstrip('.') }"


def _dataset_fields(context: ReportContext) -> list[tuple[str, str]]:
    documentation = context.documentation
    return [
        ("Source", _source_name(documentation.source_type)),
        ("Database", documentation.database_name),
        ("Schema", documentation.schema_name),
        ("Table", documentation.table_name),
        ("Rows", _text(documentation.summary.row_count)),
        ("Columns", str(documentation.summary.column_count)),
    ]


def _summary_fields(context: ReportContext) -> list[tuple[str, str]]:
    summary = build_metadata_summary(context.documentation)
    report = context.report
    return [
        ("Total Columns", str(summary.total_columns)),
        ("Required Columns", str(summary.non_nullable_columns)),
        ("Nullable Columns", str(summary.nullable_columns)),
        ("Numeric Columns", str(summary.numeric_columns)),
        ("Date / Datetime Columns", str(summary.date_datetime_columns)),
        ("Quality Score", _percent(report.quality_score)),
        ("Quality Health", quality_health(report.quality_score) or "—"),
        ("Passed Checks", str(report.passed_rules)),
        ("Failed Checks", str(report.failed_rules)),
        ("Error Checks", str(report.error_rules)),
        ("Total Checks", str(report.total_rules)),
    ]


def _profile_rows(context: ReportContext) -> list[list[str]]:
    return [
        [
            _text(row["Column"]), _text(row["Type"]), _text(row["Nullable"]), _text(row["Null Count"]),
            _text(row["Distinct Count"]), _percent(row["Distinct Ratio"]),
            format_profile_value(row["Min"], str(row["Type"])), format_profile_value(row["Max"], str(row["Type"])),
        ]
        for row in build_column_profiles(context.documentation)
    ]


def _failed_rows(context: ReportContext) -> list[list[str]]:
    return [
        [_rule_label(result.rule_type), result.column, result.status, "—" if result.status == "ERROR" else str(result.failed_records), _percent(result.failure_percentage), result.error_message or "—"]
        for result in failed_results(context.report)
    ]


def _result_rows(context: ReportContext) -> list[list[str]]:
    return [[_rule_label(result.rule_type), result.column, result.status, str(result.passed_records), str(result.failed_records), _percent(result.failure_percentage)] for result in context.report.results]


def _html_table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th scope=\"col\">{escape(header)}</th>" for header in headers)
    def cell(value: str) -> str:
        safe = escape(value)
        if value in {"PASS", "FAIL", "ERROR"}:
            return f'<td><span class="status status-{value}">{safe}</span></td>'
        return f"<td>{safe}</td>"
    body = "".join("<tr>" + "".join(cell(value) for value in row) + "</tr>" for row in rows)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def render_html_report(context: ReportContext) -> str:
    documentation = context.documentation
    trend = build_quality_trend_svg([(_timestamp(executed_at), run.quality_score) for executed_at, run in context.historical_runs if run.quality_score is not None])
    trend_html = trend or "<p class=\"muted\">Not enough historical runs to draw a trend.</p>"
    dataset_rows = _html_table(["Field", "Value"], [[label, value] for label, value in _dataset_fields(context)])
    metadata = _summary_fields(context)
    metadata_rows = _html_table(["Metric", "Value"], [[label, value] for label, value in metadata[:5]])
    quality_rows = _html_table(["Metric", "Value"], [[label, value] for label, value in metadata[5:]])
    run_rows = _html_table(["Field", "Value"], [["Dataset", f"{_source_name(documentation.source_type)} / {documentation.database_name} / {documentation.schema_name} / {documentation.table_name}"], ["Executed At", _timestamp(context.executed_at)], ["Run ID", context.run_id]])
    failed = _failed_rows(context)
    failed_html = _html_table(["Rule", "Column / Scope", "Status", "Failed Records", "Failure %", "Message"], failed) if failed else "<p class=\"success\">No failed or error checks in this run.</p>"
    return f"""<!DOCTYPE html>
<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"><title>Data Quality Report</title>
<style>
:root {{ color-scheme:light; --ink:#192B37; --muted:#64727C; --accent:#FF5640; --line:#D4DADD; --surface:#F5F7F8; }}
* {{ box-sizing:border-box; }} body {{ color:var(--ink); font:14px/1.45 Arial,sans-serif; margin:0 auto; max-width:1120px; padding:42px 34px; }} h1 {{ margin:0 0 6px; font-size:30px; }} h2 {{ border-bottom:2px solid var(--accent); font-size:17px; margin:30px 0 10px; padding-bottom:5px; }} h3 {{ font-size:15px; margin:20px 0 8px; }} .identity,.muted {{ color:var(--muted); }} .identity {{ margin-bottom:24px; }} .grid {{ display:grid; gap:18px; grid-template-columns:1fr 1fr; }} table {{ border-collapse:collapse; margin:8px 0 20px; width:100%; }} th {{ background:var(--ink); color:#fff; text-align:left; }} th,td {{ border:1px solid var(--line); padding:8px 10px; vertical-align:top; }} tr:nth-child(even) {{ background:var(--surface); }} .status {{ font-weight:700; }} .status-PASS {{ color:#277944; }} .status-FAIL {{ color:#B23A2B; }} .status-ERROR {{ color:#8A4B00; }} .success {{ background:#E9F5EC; border:1px solid #A9D5B3; padding:10px 12px; }} .trend {{ border:1px solid var(--line); padding:10px; }} .quality-trend-grid {{ stroke:#D4DADD; stroke-width:1; }} .quality-trend-line {{ stroke:#FF5640; stroke-width:3; }} .quality-trend-point {{ fill:#FF5640; stroke:#fff; stroke-width:2; }} .quality-trend-axis {{ fill:#64727C; font-size:11px; }} svg {{ max-width:100%; }} @media print {{ body {{ padding:16px; }} h2 {{ break-after:avoid; }} table {{ page-break-inside:auto; }} tr {{ page-break-inside:avoid; }} }} @media (max-width:700px) {{ body {{ padding:20px 14px; }} .grid {{ grid-template-columns:1fr; }} }}
</style></head><body><h1>Data Quality Report</h1><div class=\"identity\">{escape(_source_name(documentation.source_type))} / {escape(documentation.database_name)} / {escape(documentation.schema_name)} / {escape(documentation.table_name)}</div>
<h2>Dataset Overview</h2>{dataset_rows}<h2>Metadata Summary</h2>{metadata_rows}<h2>Column Profile</h2>{_html_table(["Column","Type","Nullable","Null Count","Distinct Count","Distinct Ratio","Min","Max"], _profile_rows(context))}
<h2>Quality Overview</h2>{quality_rows}<div class=\"grid\"><div><h2>Run Summary</h2>{run_rows}</div><div><h2>Quality Score Trend</h2><div class=\"trend\">{trend_html}</div></div></div>
<h2>Failed Checks</h2>{failed_html}<h2>Rule Results</h2>{_html_table(["Rule","Column / Scope","Status","Passed","Failed","Failure %"], _result_rows(context))}
</body></html>"""


def _md_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def _markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    return "| " + " | ".join(_md_escape(value) for value in headers) + " |\n| " + " | ".join("---" for _ in headers) + " |\n" + "\n".join("| " + " | ".join(_md_escape(value) for value in row) + " |" for row in rows)


def render_markdown_report(context: ReportContext) -> str:
    documentation = context.documentation
    trend_rows = [[_timestamp(executed_at), _percent(run.quality_score)] for executed_at, run in context.historical_runs if run.quality_score is not None]
    summary = _summary_fields(context)
    failed = _failed_rows(context)
    failed_section = _markdown_table(["Rule", "Column / Scope", "Status", "Failed Records", "Failure %", "Message"], failed) if failed else "No failed or error checks in this run."
    return "\n".join([
        "# Data Quality Report", f"\n{_source_name(documentation.source_type)} / {documentation.database_name} / {documentation.schema_name} / {documentation.table_name}",
        "\n## Dataset Overview", _markdown_table(["Field", "Value"], [[label, value] for label, value in _dataset_fields(context)]),
        "\n## Metadata Summary", _markdown_table(["Metric", "Value"], [[label, value] for label, value in summary[:5]]),
        "\n## Column Profile", _markdown_table(["Column", "Type", "Nullable", "Null Count", "Distinct Count", "Distinct Ratio", "Min", "Max"], _profile_rows(context)),
        "\n## Quality Overview", _markdown_table(["Metric", "Value"], [[label, value] for label, value in summary[5:]]),
        "\n## Run Summary", _markdown_table(["Field", "Value"], [["Executed At", _timestamp(context.executed_at)], ["Run ID", context.run_id]]),
        "\n## Quality Score Trend", _markdown_table(["Executed At", "Quality Score"], trend_rows) if trend_rows else "No historical trend data is available.",
        "\n## Failed Checks", failed_section,
        "\n## Rule Results", _markdown_table(["Rule", "Column / Scope", "Status", "Passed", "Failed", "Failure %"], _result_rows(context)),
    ]) + "\n"


def render_pdf_report(context: ReportContext) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    from io import BytesIO

    output = BytesIO()
    document = SimpleDocTemplate(output, pagesize=letter, rightMargin=.45 * inch, leftMargin=.45 * inch, topMargin=.55 * inch, bottomMargin=.55 * inch, title="Data Quality Report", author="AI-Powered Data Catalog")
    styles = getSampleStyleSheet()
    styles["Title"].textColor = colors.HexColor("#192B37")
    styles["Heading2"].textColor = colors.HexColor("#FF5640")
    styles["BodyText"].textColor = colors.HexColor("#192B37")
    header_style = ParagraphStyle("PdfTableHeader", parent=styles["BodyText"], textColor=colors.white, fontName="Helvetica-Bold")
    story: list[Any] = [Paragraph("Data Quality Report", styles["Title"]), Paragraph(escape(_source_name(context.documentation.source_type) + " / " + context.documentation.database_name + " / " + context.documentation.schema_name + " / " + context.documentation.table_name), styles["BodyText"]), Spacer(1, 12)]

    def add_section(title: str, headers: list[str], rows: list[list[str]]) -> None:
        story.extend([Paragraph(title, styles["Heading2"])])
        if rows:
            table = Table([[Paragraph(escape(str(value)), header_style) for value in headers]] + [[Paragraph(escape(str(value)), styles["BodyText"]) for value in row] for row in rows], repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(PDF_TABLE_HEADER_BACKGROUND)), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#D4DADD")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F7F8")]), ("FONTSIZE", (0, 0), (-1, -1), 7.5), ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]))
            story.extend([table, Spacer(1, 8)])
        else:
            story.extend([Paragraph("No failed or error checks in this run.", styles["BodyText"]), Spacer(1, 8)])

    add_section("Dataset Overview", ["Field", "Value"], [[label, value] for label, value in _dataset_fields(context)])
    summary = _summary_fields(context)
    add_section("Metadata Summary", ["Metric", "Value"], [[label, value] for label, value in summary[:5]])
    add_section("Column Profile", ["Column", "Type", "Nullable", "Null Count", "Distinct Count", "Distinct Ratio", "Min", "Max"], _profile_rows(context))
    add_section("Quality Overview", ["Metric", "Value"], [[label, value] for label, value in summary[5:]])
    add_section("Run Summary", ["Field", "Value"], [["Executed At", _timestamp(context.executed_at)], ["Run ID", context.run_id]])
    trend_rows = [[_timestamp(executed_at), _percent(run.quality_score)] for executed_at, run in context.historical_runs if run.quality_score is not None]
    add_section("Quality Score Trend", ["Executed At", "Quality Score"], trend_rows)
    add_section("Failed Checks", ["Rule", "Column / Scope", "Status", "Failed Records", "Failure %", "Message"], _failed_rows(context))
    add_section("Rule Results", ["Rule", "Column / Scope", "Status", "Passed", "Failed", "Failure %"], _result_rows(context))
    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return output.getvalue()


def _footer(canvas: Any, document: Any) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColorRGB(.35, .4, .43)
    canvas.drawString(.45 * 72, .3 * 72, "AI-Powered Data Catalog — Data Quality Report")
    canvas.drawRightString(7.9 * 72, .3 * 72, f"Page {document.page}")
    canvas.restoreState()


__all__ = ["build_export_filename", "render_html_report", "render_markdown_report", "render_pdf_report"]
