from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from pydantic import ValidationError

from ai.models import (
    AISuggestionResult,
    ApprovedSuggestion,
    RawSuggestedRule,
    RejectedSuggestion,
)
from ai.ollama_client import OllamaClient
from ai.prompts import PROMPT_VERSION
from documentation.models import TableDocumentation
from quality.rule_models import (
    AcceptedValuesRule,
    DuplicateRule,
    FreshnessRule,
    NumericRangeRule,
    StringLengthRule,
    UniqueRule,
    parse_quality_rule,
)


class QualityRuleSuggester:
    """Suggest validated Phase 6 rules without database access or execution."""

    def __init__(
        self,
        client: OllamaClient | None = None,
        *,
        max_suggestions: int = 8,
        max_context_columns: int | None = None,
    ) -> None:
        self.client = client or OllamaClient()
        if max_suggestions < 0:
            raise ValueError("max_suggestions cannot be negative")
        self.max_suggestions = max_suggestions
        try:
            configured_context_columns = (
                int(os.getenv("AI_MAX_CONTEXT_COLUMNS", "100"))
                if max_context_columns is None
                else max_context_columns
            )
        except ValueError as exc:
            raise ValueError("AI_MAX_CONTEXT_COLUMNS must be an integer") from exc
        if configured_context_columns <= 0:
            raise ValueError("max_context_columns must be greater than zero")
        self.max_context_columns = configured_context_columns
        self._cache: dict[str, AISuggestionResult] = {}

    def suggest_for_table(self, documentation: TableDocumentation) -> AISuggestionResult:
        if not self.client.enabled:
            return AISuggestionResult(
                status="DISABLED",
                model=self.client.model,
                message="AI suggestions are disabled.",
            )

        context = self.build_context(documentation)
        if self.max_suggestions == 0:
            return AISuggestionResult(status="SUCCESS", model=self.client.model)
        cache_key = self._cache_key(context)
        if cache_key in self._cache:
            cached = self._cache[cache_key].model_copy(deep=True)
            cached.cache_hit = True
            cached.response_time_ms = 0.0
            return cached

        last_message = "Ollama returned invalid structured output."
        for _ in range(2):
            response = self.client.suggest(context)
            if response.status != "SUCCESS":
                return AISuggestionResult(
                    status=response.status,
                    model=response.model,
                    response_time_ms=response.response_time_ms,
                    message=response.message,
                )
            try:
                raw_payload = json.loads((response.payload or {}).get("content") or "")
                result = self._validate_response(
                    raw_payload,
                    documentation,
                    response.model,
                    response.response_time_ms,
                    {item["column_name"].lower() for item in context["columns"]},
                )
                self._cache[cache_key] = result.model_copy(deep=True)
                return result
            except (json.JSONDecodeError, TypeError, ValueError):
                last_message = "Ollama returned invalid structured output."

        return AISuggestionResult(
            status="ERROR",
            model=self.client.model,
            message=last_message,
        )

    def build_context(self, documentation: TableDocumentation) -> dict[str, Any]:
        row_count = documentation.summary.row_count
        columns = []
        for column in documentation.columns[: self.max_context_columns]:
            null_count = column.null_count
            distinct_count = column.distinct_count
            non_null_count = (
                row_count - null_count
                if (
                    row_count is not None
                    and null_count is not None
                    and row_count >= 0
                    and 0 <= null_count <= row_count
                )
                else None
            )
            distinct_ratio = (
                distinct_count / non_null_count
                if (
                    distinct_count is not None
                    and distinct_count >= 0
                    and non_null_count is not None
                    and non_null_count > 0
                )
                else None
            )
            null_ratio = (
                null_count / row_count
                if (
                    null_count is not None
                    and row_count is not None
                    and row_count > 0
                    and 0 <= null_count <= row_count
                )
                else None
            )
            columns.append(
                {
                    "column_name": column.column_name,
                    "normalized_data_type": column.normalized_data_type,
                    "nullable": column.nullable,
                    "null_count": null_count,
                    "distinct_count": distinct_count,
                    "non_null_count": non_null_count,
                    "distinct_ratio": distinct_ratio,
                    "null_ratio": null_ratio,
                    "possible_category": column.possible_category,
                    "minimum": column.minimum,
                    "maximum": column.maximum,
                }
            )
        return {
            "table_name": documentation.table_name,
            "row_count": row_count,
            "columns": columns,
            "allowed_rule_types": [
                "not_null",
                "duplicate",
                "unique",
                "accepted_values",
                "numeric_range",
                "string_length",
                "freshness",
            ],
            "max_suggestions": self.max_suggestions,
        }

    def clear_cache(self) -> None:
        self._cache.clear()

    def _validate_response(
        self,
        payload: dict[str, Any],
        documentation: TableDocumentation,
        model: str,
        response_time_ms: float | None,
        context_columns: set[str],
    ) -> AISuggestionResult:
        if not isinstance(payload, dict) or not isinstance(payload.get("suggestions"), list):
            raise ValueError("Invalid suggestion response structure")
        if set(payload) != {"suggestions"}:
            raise ValueError("Unexpected response fields")

        columns = {column.column_name.lower(): column for column in documentation.columns}
        approved: list[ApprovedSuggestion] = []
        rejected: list[RejectedSuggestion] = []
        identities: set[str] = set()
        unique_columns: set[str] = set()

        for candidate_payload in payload["suggestions"]:
            try:
                candidate = RawSuggestedRule.model_validate(candidate_payload)
            except ValidationError as exc:
                raw_rule = candidate_payload.get("rule", {}) if isinstance(candidate_payload, dict) else {}
                raw_rule_type = raw_rule.get("rule_type") if isinstance(raw_rule, dict) else None
                category = (
                    "unsupported_rule"
                    if raw_rule_type not in {
                        "not_null",
                        "duplicate",
                        "unique",
                        "accepted_values",
                        "numeric_range",
                        "string_length",
                        "freshness",
                    }
                    else "schema_validation_failure"
                )
                rejected.append(
                    RejectedSuggestion(
                        rule_type=raw_rule_type,
                        column=raw_rule.get("column") if isinstance(raw_rule, dict) else None,
                        category=category,
                        reason="Suggestion did not match the allowed structured schema.",
                    )
                )
                continue

            rule_payload = candidate.rule.model_dump(exclude_none=True)
            column = columns.get(candidate.rule.column.lower())
            if column is None or candidate.rule.column.lower() not in context_columns:
                rejected.append(
                    self._rejection(
                        candidate,
                        "unknown_column",
                        "Suggested column was not included in the supplied metadata context.",
                    )
                )
                continue

            try:
                rule = parse_quality_rule(rule_payload)
            except (ValidationError, ValueError, TypeError) as exc:
                rejected.append(self._rejection(candidate, "invalid_configuration", "Rule configuration failed Phase 6 validation."))
                continue

            mismatch = self._datatype_mismatch(rule, column.normalized_data_type)
            if mismatch:
                rejected.append(self._rejection(candidate, "datatype_mismatch", mismatch))
                continue

            if isinstance(rule, (AcceptedValuesRule, NumericRangeRule, StringLengthRule, FreshnessRule)):
                rejected.append(
                    self._rejection(
                        candidate,
                        "invalid_configuration",
                        "Configuration-dependent rule parameters are not grounded by this metadata context.",
                    )
                )
                continue

            if isinstance(rule, DuplicateRule) and rule.column.lower() in unique_columns:
                rejected.append(self._rejection(candidate, "duplicate_suggestion", "Unique already represents this duplicate-value intent."))
                continue
            if isinstance(rule, UniqueRule):
                unique_columns.add(rule.column.lower())
                approved = [item for item in approved if not (isinstance(item.rule, DuplicateRule) and item.rule.column.lower() == rule.column.lower())]

            identity = json.dumps(rule.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
            if identity in identities:
                rejected.append(self._rejection(candidate, "duplicate_suggestion", "Duplicate suggestion removed."))
                continue
            identities.add(identity)
            approved.append(ApprovedSuggestion(rule=rule, reason=candidate.reason))
            if len(approved) >= self.max_suggestions:
                break

        return AISuggestionResult(
            status="SUCCESS",
            model=model,
            response_time_ms=response_time_ms,
            suggestions=approved,
            rejected_suggestions=rejected,
        )

    def _datatype_mismatch(self, rule: Any, normalized_type: str) -> str | None:
        normalized_type = normalized_type.upper()
        if isinstance(rule, NumericRangeRule) and normalized_type not in {"NUMBER", "DECIMAL"}:
            return "numeric_range requires NUMBER or DECIMAL."
        if isinstance(rule, StringLengthRule) and normalized_type != "STRING":
            return "string_length requires STRING."
        if isinstance(rule, FreshnessRule) and normalized_type not in {"DATE", "DATETIME"}:
            return "freshness requires DATE or DATETIME."
        return None

    def _rejection(self, candidate: RawSuggestedRule, category: str, reason: str) -> RejectedSuggestion:
        return RejectedSuggestion(
            rule_type=candidate.rule.rule_type,
            column=candidate.rule.column,
            category=category,
            reason=reason,
        )

    def _cache_key(self, context: dict[str, Any]) -> str:
        canonical = json.dumps(
            {
                "model": self.client.model,
                "prompt_version": PROMPT_VERSION,
                "context": context,
            },
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
