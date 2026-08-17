from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel, Field, model_validator

from catalog.ranking import CatalogRanker, CatalogTokenizer, RankingBreakdown
from catalog.repository import CatalogEntry, CatalogRepository


class CatalogFilters(BaseModel):
    """Exact catalog filters applied with AND semantics."""

    source_type: str | list[str] | None = None
    database_name: str | None = None
    schema_name: str | None = None
    min_quality_score: float | None = None
    max_quality_score: float | None = None

    @model_validator(mode="after")
    def validate_quality_range(self) -> "CatalogFilters":
        if self.min_quality_score is not None and self.max_quality_score is not None:
            if self.min_quality_score > self.max_quality_score:
                raise ValueError("min_quality_score cannot exceed max_quality_score")
        for value in (self.min_quality_score, self.max_quality_score):
            if value is not None and not 0 <= value <= 100:
                raise ValueError("quality scores must be between 0 and 100")
        return self


class CatalogSearchResult(BaseModel):
    """Explainable search result suitable for a catalog UI."""

    dataset_id: str
    entry: CatalogEntry
    score: int
    matched_fields: list[str] = Field(default_factory=list)
    matched_terms: list[str] = Field(default_factory=list)
    score_breakdown: dict[str, int] = Field(default_factory=dict)


class CatalogSearch:
    """Search and rank an in-memory catalog without database access."""

    def __init__(
        self,
        repository: CatalogRepository,
        ranker: CatalogRanker | None = None,
        tokenizer: CatalogTokenizer | None = None,
    ) -> None:
        self.repository = repository
        self.tokenizer = tokenizer or CatalogTokenizer()
        self.ranker = ranker or CatalogRanker(self.tokenizer)

    def search(
        self,
        query: str = "",
        *,
        filters: CatalogFilters | None = None,
        limit: int | None = None,
        source_type: str | list[str] | None = None,
        database_name: str | None = None,
        schema_name: str | None = None,
        min_quality_score: float | None = None,
        max_quality_score: float | None = None,
    ) -> list[CatalogSearchResult]:
        if limit is not None and limit < 0:
            raise ValueError("limit cannot be negative")
        combined_filters = filters or CatalogFilters(
            source_type=source_type,
            database_name=database_name,
            schema_name=schema_name,
            min_quality_score=min_quality_score,
            max_quality_score=max_quality_score,
        )
        candidates = [
            entry for entry in self.repository.get_all() if self._matches_filters(entry, combined_filters)
        ]
        query_tokens = self.tokenizer.tokenize(query)
        if not query_tokens:
            results = [
                CatalogSearchResult(dataset_id=entry.dataset_id, entry=entry, score=0)
                for entry in candidates
            ]
            results.sort(key=self._browse_sort_key)
        else:
            results = []
            for entry in candidates:
                breakdown = self.ranker.rank(entry, query_tokens)
                if breakdown.score <= 0:
                    continue
                results.append(self._result(entry, breakdown))
            results.sort(key=self._ranked_sort_key)
        return results if limit is None else results[:limit]

    def _matches_filters(self, entry: CatalogEntry, filters: CatalogFilters) -> bool:
        documentation = entry.documentation
        if filters.source_type is not None:
            requested = filters.source_type
            requested_values = [requested] if isinstance(requested, str) else requested
            if documentation.source_type.lower() not in {value.strip().lower() for value in requested_values}:
                return False
        if filters.database_name is not None and documentation.database_name.lower() != filters.database_name.strip().lower():
            return False
        if filters.schema_name is not None and documentation.schema_name.lower() != filters.schema_name.strip().lower():
            return False
        if filters.min_quality_score is not None:
            if entry.quality_score is None or entry.quality_score < filters.min_quality_score:
                return False
        if filters.max_quality_score is not None:
            if entry.quality_score is None or entry.quality_score > filters.max_quality_score:
                return False
        return True

    def _result(self, entry: CatalogEntry, breakdown: RankingBreakdown) -> CatalogSearchResult:
        return CatalogSearchResult(
            dataset_id=entry.dataset_id,
            entry=entry,
            score=breakdown.score,
            matched_fields=list(breakdown.matched_fields),
            matched_terms=list(breakdown.matched_terms),
            score_breakdown=breakdown.components,
        )

    def _ranked_sort_key(self, result: CatalogSearchResult) -> tuple[Any, ...]:
        documentation = result.entry.documentation
        table_score = sum(
            result.score_breakdown.get(component, 0)
            for component in ("exact_table_name", "all_table_tokens", "table_prefix", "table_tokens")
        )
        return (
            -result.score,
            -table_score,
            -len(result.matched_terms),
            documentation.table_name.lower(),
            documentation.database_name.lower(),
            documentation.schema_name.lower(),
        )

    def _browse_sort_key(self, result: CatalogSearchResult) -> tuple[str, str, str, str]:
        documentation = result.entry.documentation
        return (
            documentation.table_name.lower(),
            documentation.database_name.lower(),
            documentation.schema_name.lower(),
            documentation.source_type.lower(),
        )


CatalogSearchEngine = CatalogSearch

__all__ = ["CatalogFilters", "CatalogSearch", "CatalogSearchEngine", "CatalogSearchResult"]
