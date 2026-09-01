from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from uuid import uuid4

from auth.models import UserRecord
from auth.security import normalize_email, normalize_username
from storage.database import DEFAULT_DATABASE_PATH, connection_context


class UserAlreadyExistsError(ValueError):
    pass


class UserRepository:
    def __init__(self, database_path: str | Path = DEFAULT_DATABASE_PATH) -> None:
        self.database_path = Path(database_path)
        self.initialize()

    def initialize(self) -> None:
        with connection_context(self.database_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    password_hash TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS password_reset_tokens (
                    reset_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    token_hash TEXT NOT NULL UNIQUE,
                    expires_at TEXT NOT NULL,
                    used_at TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
                """
            )
            connection.execute("CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_user ON password_reset_tokens(user_id)")
            connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_nocase ON users(username COLLATE NOCASE)")
            connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_nocase ON users(email COLLATE NOCASE)")
            connection.commit()

    def create_user(self, username: str, email: str, password_hash: str) -> UserRecord:
        username = normalize_username(username)
        email = normalize_email(email)
        timestamp = datetime.now(timezone.utc).isoformat()
        user = UserRecord(str(uuid4()), username, email, password_hash, True, timestamp, timestamp)
        try:
            with connection_context(self.database_path) as connection:
                with connection:
                    connection.execute(
                        "INSERT INTO users (user_id, username, email, password_hash, is_active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (user.user_id, user.username, user.email, user.password_hash, 1, user.created_at, user.updated_at),
                    )
        except sqlite3.IntegrityError as exc:
            raise UserAlreadyExistsError("Username or email is already registered.") from exc
        return user

    def get_by_username(self, username: str) -> UserRecord | None:
        return self._get("username", normalize_username(username))

    def get_by_email(self, email: str) -> UserRecord | None:
        return self._get("email", normalize_email(email))

    def get_by_id(self, user_id: str) -> UserRecord | None:
        return self._get("user_id", str(user_id))

    def username_exists(self, username: str) -> bool:
        return self.get_by_username(username) is not None

    def email_exists(self, email: str) -> bool:
        return self.get_by_email(email) is not None

    def create_password_reset_token(self, user_id: str, token_hash: str, expires_at: str, reset_id: str) -> None:
        created_at = datetime.now(timezone.utc).isoformat()
        with connection_context(self.database_path) as connection:
            with connection:
                connection.execute(
                    "UPDATE password_reset_tokens SET used_at = ? WHERE user_id = ? AND used_at IS NULL",
                    (created_at, user_id),
                )
                connection.execute(
                    "INSERT INTO password_reset_tokens (reset_id, user_id, token_hash, expires_at, created_at) VALUES (?, ?, ?, ?, ?)",
                    (reset_id, user_id, token_hash, expires_at, created_at),
                )

    def consume_password_reset(self, token_hash: str, password_hash: str) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        used_at = now
        with connection_context(self.database_path) as connection:
            with connection:
                row = connection.execute(
                    "SELECT user_id FROM password_reset_tokens WHERE token_hash = ? AND used_at IS NULL AND expires_at > ?",
                    (token_hash, now),
                ).fetchone()
                if row is None:
                    return False
                updated = connection.execute(
                    "UPDATE users SET password_hash = ?, updated_at = ? WHERE user_id = ? AND is_active = 1",
                    (password_hash, now, row["user_id"]),
                )
                if updated.rowcount != 1:
                    return False
                connection.execute(
                    "UPDATE password_reset_tokens SET used_at = ? WHERE token_hash = ? AND used_at IS NULL",
                    (used_at, token_hash),
                )
                return True

    def _get(self, field: str, value: str) -> UserRecord | None:
        if field not in {"user_id", "username", "email"}:
            raise ValueError("Unsupported user lookup field")
        with connection_context(self.database_path) as connection:
            row = connection.execute(f"SELECT user_id, username, email, password_hash, is_active, created_at, updated_at FROM users WHERE {field} = ?", (value,)).fetchone()
        if row is None:
            return None
        return UserRecord(row["user_id"], row["username"], row["email"], row["password_hash"], bool(row["is_active"]), row["created_at"], row["updated_at"])
