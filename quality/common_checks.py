from typing import Any

from documentation.classifier import ColumnClassifier
from metadata.models import TableMetadata
from quality.rule_models import NotNullRule, UniqueRule


_CLASSIFIER = ColumnClassifier()


def infer_common_rules(table: TableMetadata) -> list[dict[str, Any]]:
    """Infer deterministic checks from persisted metadata facts only."""
    rules: list[dict[str, Any]] = []
    for column in table.columns:
        if not column.nullable:
            rules.append(NotNullRule(column=column.column_name).model_dump())
        if (
            table.row_count is not None
            and table.row_count > 0
            and column.distinct_count is not None
            and column.distinct_count == table.row_count
            and column.null_count == 0
            and _CLASSIFIER.classify(column) == "Identifier"
        ):
            rules.append(UniqueRule(column=column.column_name).model_dump())
    return rules
