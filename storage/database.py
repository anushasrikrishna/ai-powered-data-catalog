from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


DEFAULT_DATABASE_PATH = Path(__file__).resolve().parent / "catalog_metadata.db"


def ensure_parent_directory(database_path: str | Path = DEFAULT_DATABASE_PATH) -> Path:
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def connect(database_path: str | Path = DEFAULT_DATABASE_PATH) -> sqlite3.Connection:
    path = ensure_parent_directory(database_path)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def connection_context(database_path: str | Path = DEFAULT_DATABASE_PATH) -> Iterator[sqlite3.Connection]:
    connection = connect(database_path)
    try:
        yield connection
    finally:
        connection.close()
