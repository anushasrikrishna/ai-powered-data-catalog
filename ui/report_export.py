from __future__ import annotations

from datetime import datetime
from html import escape
import re
from typing import Any

from ui.report_view import CatalogReportContext, ReportContext, build_column_profiles, build_metadata_summary, failed_results, format_profile_value, quality_health
from ui.quality_trend import build_quality_trend_svg
from ui.metadata_trends import build_dataset_growth_trend_svg, build_schema_evolution_trend_svg

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


def build_export_filename(context: ReportContext | CatalogReportContext, extension: str, generated_on: datetime | None = None) -> str:
    date_text = (generated_on or datetime.now()).strftime("%Y-%m-%d")
    report_name = "catalog_report" if isinstance(context, CatalogReportContext) else "quality_report"
    parts = [context.documentation.database_name, context.documentation.schema_name, context.documentation.table_name, report_name, date_text]
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


def _catalog_fields(context: CatalogReportContext) -> list[tuple[str, str]]:
    documentation = context.documentation
    latest_scan = context.scan_history[0].scanned_at if context.scan_history else None
    return [
        ("Source", _source_name(documentation.source_type)),
        ("Database", documentation.database_name),
        ("Schema", documentation.schema_name),
        ("Table", documentation.table_name),
        ("Object Type", documentation.table_type),
        ("Row Count", _text(documentation.summary.row_count)),
        ("Column Count", str(documentation.summary.column_count)),
        ("Latest Scan", _timestamp(latest_scan) if latest_scan else "—"),
    ]


def _catalog_summary_rows(context: CatalogReportContext) -> list[list[str]]:
    summary = build_metadata_summary(context.documentation)
    technical = context.documentation.summary
    return [[label, value] for label, value in [
        ("Total Columns", str(summary.total_columns)),
        ("Required / Non-Nullable Columns", str(summary.non_nullable_columns)),
        ("Nullable Columns", str(summary.nullable_columns)),
        ("Numeric Columns", str(summary.numeric_columns)),
        ("Date / Datetime Columns", str(summary.date_datetime_columns)),
        ("String Columns", str(technical.string_column_count)),
        ("Boolean Columns", str(technical.boolean_column_count)),
        ("Other Columns", str(technical.other_column_count + technical.binary_column_count)),
    ]]


def _catalog_distribution_rows(context: CatalogReportContext) -> list[list[str]]:
    summary = context.documentation.summary
    return [[label, str(count)] for label, count in [
        ("Number", summary.number_column_count), ("Decimal", summary.decimal_column_count),
        ("String", summary.string_column_count), ("Date", summary.date_column_count),
        ("Datetime", summary.datetime_column_count), ("Boolean", summary.boolean_column_count),
        ("Binary", summary.binary_column_count), ("Other", summary.other_column_count),
    ] if count]


def _catalog_classification_rows(context: CatalogReportContext) -> list[list[str]]:
    counts: dict[str, int] = {}
    for column in context.documentation.columns:
        counts[column.possible_category] = counts.get(column.possible_category, 0) + 1
    return [[label, str(count)] for label, count in sorted(counts.items())]


def _catalog_column_rows(context: CatalogReportContext) -> list[list[str]]:
    return [
        [_text(column.column_name), _text(column.source_data_type), _text(column.normalized_data_type),
         _text(column.possible_category), "Yes" if column.nullable else "No", str(column.ordinal_position),
         _text(column.null_count), _text(column.distinct_count), format_profile_value(column.minimum, column.normalized_data_type),
         format_profile_value(column.maximum, column.normalized_data_type)]
        for column in context.documentation.columns
    ]


def _catalog_change_rows(context: CatalogReportContext) -> list[list[str]]:
    comparison = context.comparison
    if comparison is None:
        return []
    rows = [["COLUMN ADDED", name, "+ Added"] for name in comparison.added_columns]
    rows += [["COLUMN REMOVED", name, "- Removed"] for name in comparison.removed_columns]
    rows += [["DATA TYPE CHANGED", item["column"], f'{item["from"]} -> {item["to"]}'] for item in comparison.type_changes]
    rows += [["NULLABILITY CHANGED", item["column"], f'{item["from"]} -> {item["to"]}'] for item in comparison.nullability_changes]
    rows += [["NULL COUNT CHANGED", item["column"], f'{item["from"]} -> {item["to"]}'] for item in comparison.null_count_changes]
    rows += [["DISTINCT COUNT CHANGED", item["column"], f'{item["from"]} -> {item["to"]}'] for item in comparison.distinct_count_changes]
    return rows


def _catalog_history_rows(context: CatalogReportContext) -> list[list[str]]:
    rows: list[list[str]] = []
    for index, snapshot in enumerate(context.scan_history):
        comparison = None
        if index + 1 < len(context.scan_history):
            from storage.scan_history import compare_snapshots
            comparison = compare_snapshots(context.scan_history[index + 1], snapshot)
        rows.append([
            _timestamp(snapshot.scanned_at), _text(snapshot.row_count), str(snapshot.column_count),
            _text(comparison.net_row_change if comparison else None),
            _percent(comparison.growth_percent) if comparison else "—",
            str(comparison.schema_change_count) if comparison else "—",
        ])
    return rows


def _render_catalog_html(context: CatalogReportContext) -> str:
    optional_sections = ""
    if context.comparison is not None:
        chronological = list(reversed(context.scan_history))
        growth_points = []
        schema_points = []
        for index, snapshot in enumerate(chronological):
            prior = None
            if index:
                from storage.scan_history import compare_snapshots
                prior = compare_snapshots(chronological[index - 1], snapshot)
            growth_points.append((_timestamp(snapshot.scanned_at), snapshot.row_count, prior.net_row_change if prior else None, prior.growth_percent if prior else None))
            schema_points.append((_timestamp(snapshot.scanned_at), snapshot.column_count, prior.schema_change_count if prior else None, len(prior.added_columns) if prior else 0, len(prior.removed_columns) if prior else 0, (len(prior.type_changes) + len(prior.nullability_changes)) if prior else 0))
        growth_svg = build_dataset_growth_trend_svg(growth_points)
        schema_svg = build_schema_evolution_trend_svg(schema_points)
        evolution = context.comparison
        evolution_rows = [["Previous Rows", _text(evolution.previous.row_count)], ["Current Rows", _text(evolution.current.row_count)], ["Net Row Change", f"{evolution.net_row_change:+,}"], ["Data Growth %", _percent(evolution.growth_percent)], ["Column Change", f"{evolution.column_change:+,}"], ["Schema Changes", str(evolution.schema_change_count)]]
        if growth_svg and schema_svg:
            optional_sections += f'<h2>Evolution Trends</h2><h3>Dataset Growth Trend</h3>{growth_svg}<h3>Schema Evolution</h3>{schema_svg}'
        optional_sections += f'<h2>Dataset Evolution</h2>{_html_table(["Metric", "Value"], evolution_rows)}'
        optional_sections += f'<h2>Change Summary</h2>{_html_table(["Change", "Column", "Details"], _catalog_change_rows(context)) or "<p>No changes detected.</p>"}'
        optional_sections += f'<h2>Scan History</h2>{_html_table(["Scan Date", "Rows", "Columns", "Net Change", "Growth", "Schema Changes"], _catalog_history_rows(context))}'
    return f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Data Catalog Report</title><style>:root{{--ink:#192B37;--muted:#64727C;--accent:#FF5640;--line:#D4DADD;--surface:#F5F7F8}}*{{box-sizing:border-box}}body{{color:var(--ink);font:14px/1.45 Arial,sans-serif;margin:0 auto;max-width:1120px;padding:42px 34px}}h1{{margin:0 0 6px;font-size:30px}}h2{{border-bottom:2px solid var(--accent);font-size:17px;margin:30px 0 10px;padding-bottom:5px}}.identity,.muted{{color:var(--muted)}}.identity{{margin-bottom:24px}}table{{border-collapse:collapse;margin:8px 0 20px;width:100%}}th{{background:var(--ink);color:#fff;text-align:left}}th,td{{border:1px solid var(--line);padding:8px 10px;vertical-align:top}}tr:nth-child(even){{background:var(--surface)}}@media print{{body{{padding:16px}}h2{{break-after:avoid}}table{{page-break-inside:auto}}tr{{page-break-inside:avoid}}}}</style></head><body><h1>AI-Powered Data Catalog</h1><div class="identity">DATA CATALOG REPORT<br>{escape(_source_name(context.documentation.source_type))} / {escape(context.documentation.database_name)} / {escape(context.documentation.schema_name)} / {escape(context.documentation.table_name)}</div><h2>Dataset Overview</h2>{_html_table(["Field", "Value"], [[label, value] for label, value in _catalog_fields(context)])}<h2>Metadata Summary</h2>{_html_table(["Metric", "Value"], _catalog_summary_rows(context))}<h2>Data Type Distribution</h2>{_html_table(["Type", "Columns"], _catalog_distribution_rows(context))}<h2>Column Classifications</h2>{_html_table(["Classification", "Columns"], _catalog_classification_rows(context))}<h2>Column Metadata</h2>{_html_table(["Column", "Source Type", "Normalized Type", "Possible Category", "Nullable", "Position", "Null Count", "Distinct Count", "Minimum", "Maximum"], _catalog_column_rows(context))}{optional_sections}</body></html>'''


def _render_catalog_markdown(context: CatalogReportContext) -> str:
    sections = ["# Data Catalog Report", f"\n{_source_name(context.documentation.source_type)} / {context.documentation.database_name} / {context.documentation.schema_name} / {context.documentation.table_name}", "\n## Dataset Overview", _markdown_table(["Field", "Value"], [[label, value] for label, value in _catalog_fields(context)]), "\n## Metadata Summary", _markdown_table(["Metric", "Value"], _catalog_summary_rows(context)), "\n## Data Type Distribution", _markdown_table(["Type", "Columns"], _catalog_distribution_rows(context)), "\n## Column Classifications", _markdown_table(["Classification", "Columns"], _catalog_classification_rows(context)), "\n## Column Metadata", _markdown_table(["Column", "Source Type", "Normalized Type", "Possible Category", "Nullable", "Position", "Null Count", "Distinct Count", "Minimum", "Maximum"], _catalog_column_rows(context))]
    if context.comparison is not None:
        sections.extend(["\n## Evolution Trends", "Dataset Growth Trend and Schema Evolution are represented by the chronological Scan History below.", "\n## Dataset Evolution", _markdown_table(["Metric", "Value"], [["Previous Rows", _text(context.comparison.previous.row_count)], ["Current Rows", _text(context.comparison.current.row_count)], ["Net Row Change", f"{context.comparison.net_row_change:+,}"], ["Data Growth %", _percent(context.comparison.growth_percent)], ["Column Change", f"{context.comparison.column_change:+,}"], ["Schema Changes", str(context.comparison.schema_change_count)]]), "\n## Change Summary", _markdown_table(["Change", "Column", "Details"], _catalog_change_rows(context)), "\n## Scan History", _markdown_table(["Scan Date", "Rows", "Columns", "Net Change", "Growth", "Schema Changes"], _catalog_history_rows(context))])
    return "\n".join(sections) + "\n"


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
    if isinstance(context, CatalogReportContext):
        return _render_catalog_html(context)
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
    if isinstance(context, CatalogReportContext):
        return _render_catalog_markdown(context)
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


def _render_catalog_pdf(context: CatalogReportContext) -> bytes:
    from io import BytesIO
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import landscape, letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    output = BytesIO()
    document = SimpleDocTemplate(output, pagesize=landscape(letter), rightMargin=.35 * inch, leftMargin=.35 * inch, topMargin=.45 * inch, bottomMargin=.45 * inch, title="Data Catalog Report", author="AI-Powered Data Catalog")
    styles = getSampleStyleSheet()
    styles["Title"].textColor = colors.HexColor("#192B37")
    styles["Heading2"].textColor = colors.HexColor("#FF5640")
    body = ParagraphStyle("CatalogBody", parent=styles["BodyText"], fontSize=7.5, leading=9)
    header = ParagraphStyle("CatalogHeader", parent=body, textColor=colors.white, fontName="Helvetica-Bold")
    story: list[Any] = [Paragraph("AI-Powered Data Catalog", styles["Title"]), Paragraph("DATA CATALOG REPORT", styles["Heading2"]), Paragraph(escape(_source_name(context.documentation.source_type) + " / " + context.documentation.database_name + " / " + context.documentation.schema_name + " / " + context.documentation.table_name), body), Spacer(1, 10)]

    def add_section(title: str, headers: list[str], rows: list[list[str]], widths: list[float] | None = None) -> None:
        story.append(Paragraph(title, styles["Heading2"]))
        if not rows:
            story.extend([Paragraph("No data available.", body), Spacer(1, 8)])
            return
        table = Table([[Paragraph(escape(str(value)), header) for value in headers]] + [[Paragraph(escape(str(value)), body) for value in row] for row in rows], colWidths=widths, repeatRows=1, hAlign="LEFT")
        table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(PDF_TABLE_HEADER_BACKGROUND)), ("GRID", (0, 0), (-1, -1), .35, colors.HexColor("#D4DADD")), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F5F7F8")]), ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
        story.extend([table, Spacer(1, 8)])

    add_section("Dataset Overview", ["Field", "Value"], [[label, value] for label, value in _catalog_fields(context)])
    add_section("Metadata Summary", ["Metric", "Value"], _catalog_summary_rows(context))
    add_section("Data Type Distribution", ["Type", "Columns"], _catalog_distribution_rows(context))
    add_section("Column Classifications", ["Classification", "Columns"], _catalog_classification_rows(context))
    add_section("Column Metadata", ["Column", "Source Type", "Normalized Type", "Possible Category", "Nullable", "Position", "Null Count", "Distinct Count", "Minimum", "Maximum"], _catalog_column_rows(context), [1.0 * inch, .95 * inch, 1.0 * inch, 1.1 * inch, .55 * inch, .5 * inch, .7 * inch, .8 * inch, 1.2 * inch, 1.2 * inch])
    if context.comparison is not None:
        comparison = context.comparison
        add_section("Dataset Evolution", ["Metric", "Value"], [["Previous Rows", _text(comparison.previous.row_count)], ["Current Rows", _text(comparison.current.row_count)], ["Net Row Change", f"{comparison.net_row_change:+,}"], ["Data Growth %", _percent(comparison.growth_percent)], ["Column Change", f"{comparison.column_change:+,}"], ["Schema Changes", str(comparison.schema_change_count)]])
        add_section("Change Summary", ["Change", "Column", "Details"], _catalog_change_rows(context))
        add_section("Scan History", ["Scan Date", "Rows", "Columns", "Net Change", "Growth", "Schema Changes"], _catalog_history_rows(context))
    document.build(story, onFirstPage=_catalog_footer, onLaterPages=_catalog_footer)
    return output.getvalue()


def render_pdf_report(context: ReportContext | CatalogReportContext) -> bytes:
    if isinstance(context, CatalogReportContext):
        return _render_catalog_pdf(context)
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


def _catalog_footer(canvas: Any, document: Any) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColorRGB(.35, .4, .43)
    canvas.drawString(.35 * 72, .25 * 72, "AI-Powered Data Catalog — Data Catalog Report")
    canvas.drawRightString(10.65 * 72, .25 * 72, f"Page {document.page}")
    canvas.restoreState()


__all__ = ["build_export_filename", "render_html_report", "render_markdown_report", "render_pdf_report"]
