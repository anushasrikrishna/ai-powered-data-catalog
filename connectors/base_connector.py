from abc import ABC, abstractmethod
from typing import Any

class BaseConnector(ABC):
    """Common interface implemented by every database connector."""

    @abstractmethod
    def test_connection(self) -> bool:
        """Return True when the database connection succeeds."""
        raise NotImplementedError

    @abstractmethod
    def list_databases(self) -> list[str]:
        """Return databases accessible to the current user."""
        raise NotImplementedError

    @abstractmethod
    def list_schemas(self, database_name: str | None = None) -> list[str]:
        """Return schemas from the selected database."""
        raise NotImplementedError

    @abstractmethod
    def list_tables(self, schema_name: str) -> list[str]:
        """Return tables from the selected schema."""
        raise NotImplementedError

    @abstractmethod
    def get_columns(
        self,
        schema_name: str,
        table_name: str,
    ) -> list[dict[str, Any]]:
        """Return source column metadata dictionaries."""
        raise NotImplementedError

    @abstractmethod
    def get_sample_rows(
        self,
        schema_name: str,
        table_name: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Return a limited number of sample rows."""
        raise NotImplementedError