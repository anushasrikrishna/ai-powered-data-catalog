import unittest

from metadata.models import ColumnMetadata, TableMetadata
from quality.common_checks import infer_common_rules


def _table(row_count: int, *columns: tuple[str, bool, int | None], null_count: int = 0) -> TableMetadata:
    return TableMetadata(
        source_type="postgresql",
        database_name="sales",
        schema_name="public",
        table_name="orders",
        row_count=row_count,
        columns=[
            ColumnMetadata(
                column_name=name,
                source_data_type="integer",
                normalized_data_type="NUMBER",
                nullable=nullable,
                ordinal_position=index,
                distinct_count=distinct_count,
                null_count=null_count,
            )
            for index, (name, nullable, distinct_count) in enumerate(columns, start=1)
        ],
    )


class CommonChecksInferenceTests(unittest.TestCase):
    def test_non_nullable_column_gets_not_null(self) -> None:
        rules = infer_common_rules(_table(3, ("ORDER_ID", False, 2)))
        self.assertEqual([rule["rule_type"] for rule in rules], ["not_null"])

    def test_profiled_distinct_values_get_unique(self) -> None:
        rules = infer_common_rules(_table(3, ("ORDER_ROW_ID", True, 3)))
        self.assertEqual([rule["rule_type"] for rule in rules], ["unique"])

    def test_repeated_values_do_not_get_unique(self) -> None:
        rules = infer_common_rules(_table(3, ("ORDER_ID", True, 2)))
        self.assertEqual(rules, [])

    def test_identifier_with_duplicates_does_not_get_unique(self) -> None:
        rules = infer_common_rules(_table(3, ("CUSTOMER_ID", True, 2)))
        self.assertEqual(rules, [])

    def test_distinct_date_does_not_get_unique(self) -> None:
        rules = infer_common_rules(_table(3, ("CREATED_DATE", True, 3)))
        self.assertEqual(rules, [])

    def test_distinct_datetime_does_not_get_unique(self) -> None:
        rules = infer_common_rules(_table(3, ("UPDATED_AT", True, 3)))
        self.assertEqual(rules, [])

    def test_identifier_with_null_values_does_not_get_unique(self) -> None:
        rules = infer_common_rules(_table(3, ("PRODUCT_ROW_ID", True, 3), null_count=1))
        self.assertEqual(rules, [])

    def test_empty_table_does_not_get_unique(self) -> None:
        rules = infer_common_rules(_table(0, ("ORDER_ROW_ID", False, 0)))
        self.assertEqual([rule["rule_type"] for rule in rules], ["not_null"])

    def test_column_can_get_not_null_and_unique(self) -> None:
        rules = infer_common_rules(_table(3, ("ORDER_ROW_ID", False, 3)))
        self.assertEqual([rule["rule_type"] for rule in rules], ["not_null", "unique"])

    def test_repeated_inference_returns_one_clean_set(self) -> None:
        table = _table(3, ("ORDER_ROW_ID", False, 3))
        self.assertEqual(infer_common_rules(table), infer_common_rules(table))
        self.assertEqual(len(infer_common_rules(table)), 2)


if __name__ == "__main__":
    unittest.main()
