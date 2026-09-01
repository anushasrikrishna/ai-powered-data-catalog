from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UserRecord:
    user_id: str
    username: str
    email: str
    password_hash: str
    is_active: bool
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: str
    username: str
    email: str
