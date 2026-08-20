from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator


class QualityRuleBase(BaseModel):
    """Validated common fields for an executable quality rule."""

    model_config = ConfigDict(extra="forbid")
    column: str

    @model_validator(mode="after")
    def validate_column(self) -> "QualityRuleBase":
        if not self.column.strip():
            raise ValueError("column must be a non-empty string")
        return self


class NotNullRule(QualityRuleBase):
    rule_type: Literal["not_null"] = "not_null"


class DuplicateRule(QualityRuleBase):
    rule_type: Literal["duplicate"] = "duplicate"


class UniqueRule(QualityRuleBase):
    rule_type: Literal["unique"] = "unique"


class AcceptedValuesRule(QualityRuleBase):
    rule_type: Literal["accepted_values"] = "accepted_values"
    accepted_values: list[Any]

    @model_validator(mode="after")
    def validate_values(self) -> "AcceptedValuesRule":
        if not self.accepted_values:
            raise ValueError("accepted_values must not be empty")
        return self


class NumericRangeRule(QualityRuleBase):
    rule_type: Literal["numeric_range"] = "numeric_range"
    min_value: int | float | str | None = None
    max_value: int | float | str | None = None

    @model_validator(mode="after")
    def validate_range(self) -> "NumericRangeRule":
        if self.min_value is None and self.max_value is None:
            raise ValueError("numeric_range requires min_value or max_value")
        if self.min_value is not None and self.max_value is not None:
            if float(self.min_value) > float(self.max_value):
                raise ValueError("min_value cannot exceed max_value")
        return self


class StringLengthRule(QualityRuleBase):
    rule_type: Literal["string_length"] = "string_length"
    min_length: int | None = None
    max_length: int | None = None

    @model_validator(mode="after")
    def validate_length(self) -> "StringLengthRule":
        if self.min_length is None and self.max_length is None:
            raise ValueError("string_length requires min_length or max_length")
        if self.min_length is not None and self.min_length < 0:
            raise ValueError("min_length cannot be negative")
        if self.max_length is not None and self.max_length < 0:
            raise ValueError("max_length cannot be negative")
        if self.min_length is not None and self.max_length is not None:
            if self.min_length > self.max_length:
                raise ValueError("min_length cannot exceed max_length")
        return self


class FreshnessRule(QualityRuleBase):
    rule_type: Literal["freshness"] = "freshness"
    max_age_days: int

    @model_validator(mode="after")
    def validate_age(self) -> "FreshnessRule":
        if self.max_age_days < 0:
            raise ValueError("max_age_days cannot be negative")
        return self


QualityRule = Annotated[
    Union[
        NotNullRule,
        DuplicateRule,
        UniqueRule,
        AcceptedValuesRule,
        NumericRangeRule,
        StringLengthRule,
        FreshnessRule,
    ],
    Field(discriminator="rule_type"),
]

QUALITY_RULE_ADAPTER = TypeAdapter(QualityRule)


def parse_quality_rule(value: QualityRule | dict[str, Any]) -> QualityRule:
    """Validate a rule model or a serialized rule payload before execution."""
    if isinstance(value, BaseModel):
        return QUALITY_RULE_ADAPTER.validate_python(value.model_dump())
    return QUALITY_RULE_ADAPTER.validate_python(value)


__all__ = [
    "AcceptedValuesRule",
    "DuplicateRule",
    "FreshnessRule",
    "NotNullRule",
    "NumericRangeRule",
    "QualityRule",
    "QUALITY_RULE_ADAPTER",
    "StringLengthRule",
    "UniqueRule",
    "parse_quality_rule",
]
