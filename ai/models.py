from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from quality.rule_models import QualityRule


class RuleCandidate(BaseModel):
    """Transport schema accepted from Ollama before Phase 6 validation."""

    model_config = ConfigDict(extra="forbid")
    rule_type: Literal[
        "not_null",
        "duplicate",
        "unique",
        "accepted_values",
        "numeric_range",
        "string_length",
        "freshness",
    ]
    column: str
    accepted_values: list[Any] | None = None
    min_value: int | float | str | None = None
    max_value: int | float | str | None = None
    min_length: int | None = None
    max_length: int | None = None
    max_age_days: int | None = None


class RawSuggestedRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    rule: RuleCandidate
    reason: str | None = None


class RuleSuggestionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    suggestions: list[RawSuggestedRule] = Field(default_factory=list)


class ApprovedSuggestion(BaseModel):
    rule: QualityRule
    reason: str | None = None


class RejectedSuggestion(BaseModel):
    rule_type: str | None = None
    column: str | None = None
    category: Literal[
        "unsupported_rule",
        "unknown_column",
        "datatype_mismatch",
        "invalid_configuration",
        "duplicate_suggestion",
        "schema_validation_failure",
    ]
    reason: str


class AISuggestionResult(BaseModel):
    status: Literal["SUCCESS", "DISABLED", "UNAVAILABLE", "ERROR"]
    model: str
    response_time_ms: float | None = None
    cache_hit: bool = False
    suggestions: list[ApprovedSuggestion] = Field(default_factory=list)
    rejected_suggestions: list[RejectedSuggestion] = Field(default_factory=list)
    message: str | None = None
