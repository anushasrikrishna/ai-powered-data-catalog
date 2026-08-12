class ConnectorError(Exception):
    """Base exception for connector-level failures."""


class ConnectionFailedError(ConnectorError):
    """Raised when a connector cannot establish a connection."""


class DatabaseNotFoundError(ConnectorError):
    """Raised when a requested database is unavailable."""


class SchemaNotFoundError(ConnectorError):
    """Raised when a requested schema does not exist."""


class TableNotFoundError(ConnectorError):
    """Raised when a requested table does not exist."""