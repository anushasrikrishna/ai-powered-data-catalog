from __future__ import annotations

import unittest

from pydantic import ValidationError

from quality.rule_models import (
    AcceptedValuesRule,
    FreshnessRule,
    NumericRangeRule,
    StringLengthRule,
    parse_quality_rule,
)


class TestQualityRuleModels(unittest.TestCase):
    def test_all_required_rule_types_parse(self) -> None:
        payloads = [
            {"rule_type": "not_null", "column": "id"},
            {"rule_type": "duplicate", "column": "email"},
            {"rule_type": "unique", "column": "id"},
            {"rule_type": "accepted_values", "column": "status", "accepted_values": ["A"]},
            {"rule_type": "numeric_range", "column": "age", "min_value": 0},
            {"rule_type": "string_length", "column": "name", "max_length": 10},
            {"rule_type": "freshness", "column": "updated_at", "max_age_days": 30},
        ]

        for payload in payloads:
            with self.subTest(payload=payload):
                self.assertEqual(parse_quality_rule(payload).rule_type, payload["rule_type"])

    def test_invalid_rule_configurations_are_rejected(self) -> None:
        invalid_payloads = [
            {"rule_type": "accepted_values", "column": "status", "accepted_values": []},
            {"rule_type": "numeric_range", "column": "age"},
            {"rule_type": "numeric_range", "column": "age", "min_value": 5, "max_value": 1},
            {"rule_type": "string_length", "column": "name"},
            {"rule_type": "string_length", "column": "name", "min_length": -1},
            {"rule_type": "string_length", "column": "name", "min_length": 5, "max_length": 1},
            {"rule_type": "freshness", "column": "updated_at", "max_age_days": -1},
            {"rule_type": "unknown", "column": "id"},
            {"rule_type": "not_null", "column": ""},
        ]

        for payload in invalid_payloads:
            with self.subTest(payload=payload), self.assertRaises(ValidationError):
                parse_quality_rule(payload)

    def test_rule_models_forbid_unchecked_extra_fields(self) -> None:
        with self.assertRaises(ValidationError):
            AcceptedValuesRule(column="status", accepted_values=["A"], unexpected=True)

        self.assertEqual(NumericRangeRule(column="age", min_value=0).min_value, 0)
        self.assertEqual(StringLengthRule(column="name", max_length=10).max_length, 10)
        self.assertEqual(FreshnessRule(column="updated_at", max_age_days=0).max_age_days, 0)
