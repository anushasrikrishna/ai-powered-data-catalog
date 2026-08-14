from __future__ import annotations

import re

from metadata.models import ColumnMetadata


class ColumnClassifier:
    """Classify columns using deterministic name and normalized-type rules."""

    CONTACT_TOKENS = {
        "email",
        "fax",
        "mobile",
        "phone",
        "telephone",
    }
    FINANCIAL_TOKENS = {
        "amount",
        "balance",
        "budget",
        "cost",
        "discount",
        "expense",
        "fee",
        "price",
        "profit",
        "revenue",
        "salary",
        "subtotal",
        "tax",
        "total",
    }
    QUANTITY_TOKENS = {
        "age",
        "count",
        "duration",
        "height",
        "length",
        "percent",
        "percentage",
        "quantity",
        "qty",
        "rating",
        "ratio",
        "score",
        "weight",
    }
    BOOLEAN_TOKENS = {"active", "deleted", "disabled", "enabled"}
    NAME_TOKENS = {"first_name", "full_name", "last_name", "name"}
    LOCATION_TOKENS = {
        "address",
        "city",
        "country",
        "latitude",
        "location",
        "longitude",
        "postal",
        "province",
        "region",
        "state",
        "street",
        "zip",
    }
    TEXT_TOKENS = {
        "comment",
        "comments",
        "description",
        "details",
        "message",
        "notes",
        "remark",
        "remarks",
    }
    TEXT_EXCLUSION_TOKENS = TEXT_TOKENS | {"description"}

    def classify(self, column: ColumnMetadata) -> str:
        """Return a possible category without claiming a confirmed business meaning."""
        tokens = self._tokenize(column.column_name)
        normalized_type = column.normalized_data_type.upper()

        if self._is_identifier(tokens):
            return "Identifier"
        if tokens & self.CONTACT_TOKENS or (
            "number" in tokens and tokens & {"contact", "fax", "mobile", "phone", "telephone"}
        ):
            return "Contact Information"
        if normalized_type in {"DATE", "DATETIME"}:
            return "Date/Time"
        if normalized_type in {"NUMBER", "DECIMAL"} and tokens & self.FINANCIAL_TOKENS:
            if not tokens & self.TEXT_EXCLUSION_TOKENS:
                return "Financial/Measure"
        if normalized_type in {"NUMBER", "DECIMAL"} and tokens & self.QUANTITY_TOKENS:
            return "Quantity/Measure"
        if normalized_type == "BOOLEAN":
            return "Boolean/Flag"
        if tokens & self.NAME_TOKENS and not tokens & {"database", "schema", "table"}:
            return "Name"
        if tokens & self.LOCATION_TOKENS:
            return "Location"
        if normalized_type == "STRING" and tokens & self.TEXT_TOKENS:
            return "Text/Description"
        return "Other"

    def _is_identifier(self, tokens: set[str]) -> bool:
        return bool(
            {"id", "identifier", "key"} & tokens
            or "id" in tokens
            or "key" in tokens
        )

    def _tokenize(self, column_name: str) -> set[str]:
        camel_case_name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", column_name)
        normalized_name = re.sub(r"[^A-Za-z0-9]+", "_", camel_case_name).lower()
        return {token for token in normalized_name.split("_") if token}
