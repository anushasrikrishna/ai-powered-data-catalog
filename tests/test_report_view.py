from __future__ import annotations

import unittest
from datetime import datetime
import inspect
from types import SimpleNamespace

from documentation import MetadataDocumentationGenerator
from metadata.models import ColumnMetadata, TableMetadata
from quality.rule_engine import QualityReport, QualityResult
from storage.scan_history import ScanSnapshot
from ui.report_view import build_catalog_report_context, build_column_profiles, build_metadata_summary, failed_results, format_profile_value, quality_health
from ui.report_export import PDF_TABLE_HEADER_BACKGROUND, build_export_filename, render_html_report, render_markdown_report, render_pdf_report
from ui.report_view import build_report_context


class TestReportView(unittest.TestCase):
    def setUp(self) -> None:
        table = TableMetadata(
            source_type="sqlserver",
            database_name="catalog",
            schema_name="dbo",
            table_name="orders",
            row_count=100,
            columns=[
                ColumnMetadata(
                    column_name="order_id",
                    source_data_type="INT",
                    normalized_data_type="NUMBER",
                    nullable=False,
                    ordinal_position=1,
                    null_count=0,
                    distinct_count=100,
                    minimum=1,
                    maximum=100,
                ),
                ColumnMetadata(
                    column_name="status",
                    source_data_type="VARCHAR",
                    normalized_data_type="STRING",
                    nullable=True,
                    ordinal_position=2,
                    null_count=4,
                    distinct_count=3,
                ),
                ColumnMetadata(
                    column_name="created_at",
                    source_data_type="DATETIME",
                    normalized_data_type="DATETIME",
                    nullable=False,
                    ordinal_position=3,
                ),
            ],
        )
        self.table = table
        self.documentation = MetadataDocumentationGenerator().generate(table)

    def test_metadata_summary_and_profiles_use_persisted_values(self) -> None:
        summary = build_metadata_summary(self.documentation)
        self.assertEqual(summary.total_columns, 3)
        self.assertEqual(summary.non_nullable_columns, 2)
        self.assertEqual(summary.nullable_columns, 1)
        self.assertEqual(summary.numeric_columns, 1)
        self.assertEqual(summary.date_datetime_columns, 1)

        profiles = build_column_profiles(self.documentation)
        self.assertEqual([row["Column"] for row in profiles], ["order_id", "status", "created_at"])
        self.assertEqual(profiles[0]["Distinct Ratio"], 1.0)
        self.assertIsNone(profiles[2]["Distinct Ratio"])

    def test_profile_bounds_are_formatted_for_display_without_mutating_raw_values(self) -> None:
        self.assertEqual(format_profile_value("2026-01-07T10:51:38.7670000", "DATETIME"), "07 Jan 2026, 10:51 AM")
        self.assertEqual(format_profile_value("2026-01-07", "DATE"), "07 Jan 2026")
        self.assertEqual(format_profile_value(3.50, "DECIMAL"), "3.5")
        self.assertEqual(format_profile_value("BUS1000", "STRING"), "BUS1000")
        self.assertEqual(format_profile_value(None, "STRING"), "—")

    def test_failed_results_filter_and_order_without_changing_full_results(self) -> None:
        report = QualityReport(
            source_type="sqlserver", database_name="catalog", schema_name="dbo", table_name="orders",
            total_rules=3, passed_rules=1, failed_rules=1, error_rules=1, quality_score=80,
            results=[
                QualityResult(rule_type="not_null", column="order_id", status="PASS", total_records=100, passed_records=100),
                QualityResult(rule_type="accepted_values", column="status", status="FAIL", total_records=100, passed_records=70, failed_records=30, failure_percentage=30),
                QualityResult(rule_type="unique", column="order_id", status="ERROR", error_message="Permission denied"),
            ],
        )
        failures = failed_results(report)
        self.assertEqual([result.status for result in failures], ["ERROR", "FAIL"])
        self.assertEqual([result.status for result in report.results], ["PASS", "FAIL", "ERROR"])

    def test_quality_health_bands_are_centralized(self) -> None:
        self.assertEqual(quality_health(99), "Excellent")
        self.assertEqual(quality_health(90), "Good")
        self.assertEqual(quality_health(75), "Needs Attention")
        self.assertEqual(quality_health(60), "Poor")
        self.assertIsNone(quality_health(None))

    def test_all_export_formats_share_persisted_report_values(self) -> None:
        report = QualityReport(
            source_type="sqlserver", database_name="catalog", schema_name="dbo", table_name="orders",
            total_rules=2, passed_rules=1, failed_rules=1, error_rules=0, quality_score=88.5,
            results=[QualityResult(rule_type="accepted_values", column="status", status="FAIL", total_records=100, passed_records=80, failed_records=20, failure_percentage=20)],
        )
        run = SimpleNamespace(run_id="run-safe", executed_at="2026-08-31T10:00:00+00:00", report=report)
        context = build_report_context(self.table, run, [run])
        html = render_html_report(context)
        markdown = render_markdown_report(context)
        pdf = render_pdf_report(context)

        for rendered in (html, markdown):
            self.assertIn("catalog", rendered)
            self.assertIn("88.5%", rendered)
            self.assertIn("Failed Checks", rendered)
            self.assertNotIn("password", rendered.casefold())
        self.assertTrue(pdf.startswith(b"%PDF-"))
        self.assertGreater(len(pdf), 1000)
        self.assertEqual(build_export_filename(context, "html", generated_on=datetime(2026, 8, 31)), "catalog_dbo_orders_quality_report_2026-08-31.html")

    def test_markdown_escapes_table_values_and_pdf_supports_long_reports(self) -> None:
        long_table = self.table.model_copy(update={
            "table_name": "orders|safe",
            "columns": [self.table.columns[0].model_copy(update={"column_name": f"column_{index}"}) for index in range(90)]
        })
        run = SimpleNamespace(
            run_id="run-1", executed_at="2026-08-31T10:00:00+00:00",
            report=QualityReport(source_type="sqlserver", database_name="catalog", schema_name="dbo", table_name="orders", total_rules=0, passed_rules=0, failed_rules=0, error_rules=0, quality_score=None, results=[]),
        )
        context = build_report_context(long_table, run, [run])
        markdown = render_markdown_report(context)
        self.assertIn("\\|", markdown)
        pdf = render_pdf_report(context)
        self.assertGreater(pdf.count(b"/Type /Page"), 1)

    def test_pdf_uses_shared_white_header_style_and_navy_background(self) -> None:
        source = inspect.getsource(render_pdf_report)
        self.assertEqual(PDF_TABLE_HEADER_BACKGROUND, "#192B37")
        self.assertIn('ParagraphStyle("PdfTableHeader"', source)
        self.assertIn("textColor=colors.white", source)
        self.assertIn('repeatRows=1', source)

    def test_catalog_report_exports_and_first_scan_sections(self) -> None:
        latest = ScanSnapshot(
            scan_id=2, source_type="sqlserver", database_name="catalog", schema_name="dbo", table_name="orders",
            table_type="TABLE", scanned_at="2026-08-31T10:00:00+00:00", row_count=105,
            columns=tuple(self.table.columns),
        )
        previous = ScanSnapshot(
            scan_id=1, source_type="sqlserver", database_name="catalog", schema_name="dbo", table_name="orders",
            table_type="TABLE", scanned_at="2026-08-30T10:00:00+00:00", row_count=100,
            columns=tuple(self.table.columns[:2]),
        )
        first_context = build_catalog_report_context(self.table, [latest])
        first_markdown = render_markdown_report(first_context)
        self.assertNotIn("## Dataset Evolution", first_markdown)
        self.assertNotIn("## Scan History", first_markdown)

        context = build_catalog_report_context(self.table, [latest, previous])
        markdown = render_markdown_report(context)
        html = render_html_report(context)
        pdf = render_pdf_report(context)
        self.assertIn("# Data Catalog Report", markdown)
        self.assertIn("## Dataset Evolution", markdown)
        self.assertIn("## Change Summary", markdown)
        self.assertIn("## Scan History", markdown)
        self.assertIn("DATA CATALOG REPORT", html)
        self.assertIn("Column Metadata", html)
        self.assertTrue(pdf.startswith(b"%PDF-"))
        self.assertEqual(build_export_filename(context, "pdf", generated_on=datetime(2026, 8, 31)), "catalog_dbo_orders_catalog_report_2026-08-31.pdf")


if __name__ == "__main__":
    unittest.main()
