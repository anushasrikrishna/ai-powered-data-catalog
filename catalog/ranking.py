from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field

from catalog.repository import CatalogEntry


class CatalogTokenizer:
    """Tokenize human-entered queries and catalog names consistently."""

    @staticmethod
    def tokenize(value: str) -> tuple[str, ...]:
        if not value:
            return ()
        camel_case = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value)
        normalized = re.sub(r"[^A-Za-z0-9]+", " ", camel_case).lower()
        return tuple(token for token in normalized.split() if token)

    @staticmethod
    def normalize(value: str) -> str:
        return " ".join(CatalogTokenizer.tokenize(value))

    @staticmethod
    def equivalent_tokens(token: str) -> set[str]:
        """Return a conservative singular/plural equivalent set."""
        token = token.lower()
        values = {token}
        if len(token) > 3 and token.endswith("ies"):
            values.add(token[:-3] + "y")
        elif len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
            values.add(token[:-1])
        elif token and not token.endswith("s"):
            values.add(token + "s")
        return values


@dataclass(frozen=True)
class RankingBreakdown:
    score: int
    matched_fields: tuple[str, ...] = ()
    matched_terms: tuple[str, ...] = ()
    components: dict[str, int] = field(default_factory=dict)
    table_name_score: int = 0


class CatalogRanker:
    """Deterministic weighted ranker for catalog entries."""

    EXACT_TABLE_MATCH = 30
    ALL_TABLE_TOKENS_MATCH = 22
    TABLE_STRONG_TOKEN_MATCH = 16
    TABLE_TOKEN_MATCH = 8
    EXACT_COLUMN_MATCH = 12
    COLUMN_ALL_TOKENS_MATCH = 9
    COLUMN_TOKEN_MATCH = 5
    CATEGORY_MATCH = 7
    TAG_MATCH = 7
    DESCRIPTION_MATCH = 5
    SCHEMA_MATCH = 4
    DATABASE_MATCH = 3
    FULL_QUERY_COVERAGE_BONUS = 10
    EXACT_PHRASE_BONUS = 8
    COLUMN_SCORE_CAP = 30
    CATEGORY_SCORE_CAP = 14
    TAG_SCORE_CAP = 14
    DESCRIPTION_SCORE_CAP = 10
    TABLE_SCORE_CAP = 30

    def __init__(self, tokenizer: CatalogTokenizer | None = None) -> None:
        self.tokenizer = tokenizer or CatalogTokenizer()

    def rank(self, entry: CatalogEntry, query_tokens: Iterable[str]) -> RankingBreakdown:
        terms = tuple(dict.fromkeys(token.lower() for token in query_tokens if token))
        if not terms:
            return RankingBreakdown(score=0)

        documentation = entry.documentation
        table_tokens = self.tokenizer.tokenize(documentation.table_name)
        query_phrase = " ".join(terms)
        table_phrase = " ".join(table_tokens)
        components: dict[str, int] = {}
        matched_fields: list[str] = []
        matched_terms: set[str] = set()

        table_score, table_terms, table_components = self._score_table_name(
            table_tokens, table_phrase, query_phrase, terms
        )
        if table_score:
            components.update(table_components)
            matched_fields.append("table_name")
            matched_terms.update(table_terms)

        column_term_scores: dict[str, int] = {}
        column_terms: set[str] = set()
        for column in documentation.columns:
            score, matched = self._score_named_field(column.column_name, terms)
            if score:
                column_terms.update(matched)
                for term in matched:
                    column_term_scores[term] = max(column_term_scores.get(term, 0), score)
        if column_term_scores:
            components["column_name"] = min(
                sum(sorted(column_term_scores.values(), reverse=True)[:3]),
                self.COLUMN_SCORE_CAP,
            )
            matched_fields.append("column_name")
            matched_terms.update(column_terms)

        category_scores, category_terms = self._score_collection(
            (column.possible_category for column in documentation.columns),
            terms,
            self.CATEGORY_MATCH,
            self.CATEGORY_SCORE_CAP,
        )
        if category_scores:
            components["category"] = category_scores
            matched_fields.append("category")
            matched_terms.update(category_terms)

        tag_scores, tag_terms = self._score_collection(
            entry.tags,
            terms,
            self.TAG_MATCH,
            self.TAG_SCORE_CAP,
        )
        if tag_scores:
            components["tag"] = tag_scores
            matched_fields.append("tag")
            matched_terms.update(tag_terms)

        description_score, description_terms = self._score_text(
            entry.description or "", terms, self.DESCRIPTION_MATCH, self.DESCRIPTION_SCORE_CAP
        )
        if description_score:
            components["description"] = description_score
            matched_fields.append("description")
            matched_terms.update(description_terms)

        schema_score, schema_terms = self._score_named_field(documentation.schema_name, terms)
        if schema_score:
            components["schema_name"] = min(schema_score, self.SCHEMA_MATCH)
            matched_fields.append("schema_name")
            matched_terms.update(schema_terms)

        database_score, database_terms = self._score_named_field(documentation.database_name, terms)
        if database_score:
            components["database_name"] = min(database_score, self.DATABASE_MATCH)
            matched_fields.append("database_name")
            matched_terms.update(database_terms)

        coverage = len(matched_terms.intersection(terms)) / len(terms)
        if coverage == 1:
            components["full_query_coverage"] = self.FULL_QUERY_COVERAGE_BONUS
        if table_phrase == query_phrase:
            components["exact_phrase"] = self.EXACT_PHRASE_BONUS

        components["coverage"] = int(coverage * 10)
        return RankingBreakdown(
            score=sum(components.values()),
            matched_fields=tuple(matched_fields),
            matched_terms=tuple(sorted(matched_terms.intersection(terms))),
            components=components,
            table_name_score=table_score,
        )

    def _score_table_name(
        self,
        tokens: tuple[str, ...],
        phrase: str,
        query_phrase: str,
        terms: tuple[str, ...],
    ) -> tuple[int, set[str], dict[str, int]]:
        matched = self._matched_terms(tokens, terms)
        components: dict[str, int] = {}
        if phrase == query_phrase:
            components["exact_table_name"] = self.EXACT_TABLE_MATCH
        elif matched and len(matched) == len(terms):
            components["all_table_tokens"] = self.ALL_TABLE_TOKENS_MATCH
        elif matched and tuple(tokens[: len(terms)]) == terms:
            components["table_prefix"] = self.TABLE_STRONG_TOKEN_MATCH
        elif matched:
            components["table_tokens"] = min(len(matched) * self.TABLE_TOKEN_MATCH, 24)
        return min(sum(components.values()), self.TABLE_SCORE_CAP), matched, components

    def _score_named_field(self, value: str, terms: tuple[str, ...]) -> tuple[int, set[str]]:
        tokens = self.tokenizer.tokenize(value)
        if not tokens:
            return 0, set()
        matched = self._matched_terms(tokens, terms)
        if not matched:
            return 0, set()
        phrase = " ".join(tokens)
        query_phrase = " ".join(terms)
        if phrase == query_phrase:
            score = self.EXACT_COLUMN_MATCH
        elif len(matched) == len(terms):
            score = self.COLUMN_ALL_TOKENS_MATCH
        else:
            score = min(len(matched) * self.COLUMN_TOKEN_MATCH, 10)
        return score, matched

    def _score_collection(
        self,
        values: Iterable[str],
        terms: tuple[str, ...],
        weight: int,
        cap: int,
    ) -> tuple[int, set[str]]:
        scores: list[int] = []
        matched_terms: set[str] = set()
        for value in values:
            score, matched = self._score_named_field(value, terms)
            if score:
                scores.append(weight if score else 0)
                matched_terms.update(matched)
        return min(sum(sorted(scores, reverse=True)[:2]), cap), matched_terms

    def _score_text(
        self,
        value: str,
        terms: tuple[str, ...],
        weight: int,
        cap: int,
    ) -> tuple[int, set[str]]:
        tokens = self.tokenizer.tokenize(value)
        matched = self._matched_terms(tokens, terms)
        if not matched:
            return 0, set()
        return min(len(matched) * weight, cap), matched

    def _matched_terms(self, field_tokens: Iterable[str], terms: Iterable[str]) -> set[str]:
        field_tokens = set(field_tokens)
        return {
            term
            for term in terms
            if field_tokens.intersection(self.tokenizer.equivalent_tokens(term))
        }


__all__ = ["CatalogRanker", "CatalogTokenizer", "RankingBreakdown"]
