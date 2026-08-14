from __future__ import annotations

import unittest

from documentation.classifier import ColumnClassifier
from metadata.models import ColumnMetadata


class TestColumnClassifier(unittest.TestCase):
    def setUp(self) -> None:
        self.classifier = ColumnClassifier()

    def _column(self, name: str, normalized_type: str) -> ColumnMetadata:
        return ColumnMetadata(
            column_name=name,
            source_data_type=normalized_type,
            normalized_data_type=normalized_type,
            nullable=True,
            ordinal_position=1,
        )

    def test_expected_categories(self) -> None:
        cases = {
            "customer_id": ("NUMBER", "Identifier"),
            "order_id": ("NUMBER", "Identifier"),
            "email": ("STRING", "Contact Information"),
            "email_address": ("STRING", "Contact Information"),
            "phone_number": ("STRING", "Contact Information"),
            "contact_number": ("STRING", "Contact Information"),
            "created_at": ("DATETIME", "Date/Time"),
            "order_date": ("DATE", "Date/Time"),
            "amount": ("DECIMAL", "Financial/Measure"),
            "price": ("DECIMAL", "Financial/Measure"),
            "quantity": ("NUMBER", "Quantity/Measure"),
            "is_active": ("BOOLEAN", "Boolean/Flag"),
            "active_flag": ("BOOLEAN", "Boolean/Flag"),
            "first_name": ("STRING", "Name"),
            "customer_name": ("STRING", "Name"),
            "city": ("STRING", "Location"),
            "postal_code": ("STRING", "Location"),
            "description": ("STRING", "Text/Description"),
            "unknown_field": ("STRING", "Other"),
        }

        for name, (normalized_type, expected) in cases.items():
            with self.subTest(name=name):
                self.assertEqual(self.classifier.classify(self._column(name, normalized_type)), expected)

    def test_tokenization_handles_case_and_camel_case(self) -> None:
        self.assertEqual(self.classifier.classify(self._column("CustomerId", "NUMBER")), "Identifier")
        self.assertEqual(self.classifier.classify(self._column("EmailAddress", "STRING")), "Contact Information")
        self.assertEqual(self.classifier.classify(self._column("CREATED_AT", "DATETIME")), "Date/Time")

    def test_avoids_common_false_positives(self) -> None:
        self.assertNotEqual(self.classifier.classify(self._column("paid_amount", "DECIMAL")), "Identifier")
        self.assertEqual(self.classifier.classify(self._column("amount_description", "STRING")), "Text/Description")
        self.assertEqual(self.classifier.classify(self._column("database_name", "STRING")), "Other")

    def test_priority_prefers_contact_over_name_and_date_over_generic(self) -> None:
        self.assertEqual(self.classifier.classify(self._column("customer_email", "STRING")), "Contact Information")
        self.assertEqual(self.classifier.classify(self._column("name", "DATE")), "Date/Time")
