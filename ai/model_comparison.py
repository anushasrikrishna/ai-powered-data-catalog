from __future__ import annotations

import os
from typing import Any

from ai.ollama_client import OllamaClient
from ai.quality_rule_suggester import QualityRuleSuggester
from documentation.models import ColumnDocumentation, TableDocumentation, TableTechnicalSummary


SCENARIOS = [
    ("CUSTOMER_ID", "NUMBER", False, "Identifier"),
    ("PRODUCT_ID", "NUMBER", False, "Identifier"),
    ("EMAIL", "STRING", True, "Contact Information"),
    ("ORDER_DATE", "DATE", False, "Date/Time"),
    ("AMOUNT", "DECIMAL", True, "Financial/Measure"),
    ("STATUS", "STRING", True, "Other"),
    ("DESCRIPTION", "STRING", True, "Text/Description"),
    ("IS_ACTIVE", "BOOLEAN", False, "Boolean/Flag"),
    ("QUANTITY", "NUMBER", True, "Quantity/Measure"),
    ("UPDATED_AT", "DATETIME", True, "Date/Time"),
]


def build_synthetic_documentation() -> TableDocumentation:
    columns = [
        ColumnDocumentation(
            column_name=name,
            source_data_type=normalized_type,
            normalized_data_type=normalized_type,
            nullable=nullable,
            ordinal_position=index,
            possible_category=category,
            null_count=10 if nullable else 0,
            distinct_count=90 if nullable else 100,
        )
        for index, (name, normalized_type, nullable, category) in enumerate(SCENARIOS, start=1)
    ]
    return TableDocumentation(
        source_type="synthetic",
        database_name="benchmark",
        schema_name="public",
        table_name="quality_scenarios",
        table_type="TABLE",
        summary=TableTechnicalSummary(row_count=100, column_count=len(columns)),
        columns=columns,
    )


def compare_models() -> list[dict[str, Any]]:
    """Run the optional local comparison; never used by normal application execution."""
    if os.getenv("RUN_AI_MODEL_COMPARISON", "0") != "1":
        return []
    models = [
        os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
        os.getenv("OLLAMA_COMPARISON_MODEL", "qwen2.5:7b"),
    ]
    documentation = build_synthetic_documentation()
    report = []
    for model in models:
        result = QualityRuleSuggester(OllamaClient(model=model)).suggest_for_table(documentation)
        report.append(
            {
                "model": model,
                "status": result.status,
                "valid_rules": len(result.suggestions),
                "rejected_rules": len(result.rejected_suggestions),
                "hallucinated_columns": sum(
                    item.category == "unknown_column" for item in result.rejected_suggestions
                ),
                "response_time_ms": result.response_time_ms,
            }
        )
    return report
