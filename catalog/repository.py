from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel, Field

from documentation.models import TableDocumentation


class CatalogEntry(BaseModel):
    """Search-facing catalog entry derived from Phase 4 documentation."""

    documentation: TableDocumentation
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    quality_score: float | None = None

    @property
    def dataset_id(self) -> str:
        parts = (
            self.documentation.source_type,
            self.documentation.database_name,
            self.documentation.schema_name,
            self.documentation.table_name,
        )
        return "|".join(part.strip().lower() for part in parts)

    @classmethod
    def from_documentation(
        cls,
        documentation: TableDocumentation,
        *,
        description: str | None = None,
        tags: Iterable[str] | None = None,
        quality_score: float | None = None,
    ) -> "CatalogEntry":
        return cls(
            documentation=documentation,
            description=description,
            tags=list(tags or []),
            quality_score=quality_score,
        )


class CatalogRepository:
    """Small in-memory repository that is independent from Person 2 storage."""

    def __init__(self, entries: Iterable[CatalogEntry] | None = None) -> None:
        self._entries: dict[str, CatalogEntry] = {}
        if entries:
            self.add_many(entries)

    def add(self, entry: CatalogEntry) -> CatalogEntry:
        """Insert or replace the current entry for its stable dataset identity."""
        self._entries[entry.dataset_id] = entry
        return entry

    def add_many(self, entries: Iterable[CatalogEntry]) -> list[CatalogEntry]:
        added = []
        for entry in entries:
            added.append(self.add(entry))
        return added

    def get_all(self) -> list[CatalogEntry]:
        return [self._entries[key] for key in sorted(self._entries)]

    def get(self, dataset_id: str) -> CatalogEntry | None:
        return self._entries.get(dataset_id.strip().lower())

    def get_by_identity(
        self,
        source_type: str,
        database_name: str,
        schema_name: str,
        table_name: str,
    ) -> CatalogEntry | None:
        dataset_id = "|".join(
            part.strip().lower()
            for part in (source_type, database_name, schema_name, table_name)
        )
        return self.get(dataset_id)

    def remove(self, dataset_id: str) -> CatalogEntry | None:
        return self._entries.pop(dataset_id.strip().lower(), None)

    def __len__(self) -> int:
        return len(self._entries)


__all__ = ["CatalogEntry", "CatalogRepository"]
