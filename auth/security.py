from __future__ import annotations

import re

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError


PASSWORD_MIN_LENGTH = 8
_PASSWORD_HASHER = PasswordHasher()
_USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{3,50}$")
_EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def normalize_username(username: str) -> str:
    return str(username or "").strip()


def normalize_email(email: str) -> str:
    return str(email or "").strip().casefold()


def validate_username(username: str) -> str | None:
    normalized = normalize_username(username)
    if not _USERNAME_PATTERN.fullmatch(normalized):
        return "Username must be 3–50 characters and use letters, numbers, ., _, or -."
    return None


def validate_email(email: str) -> str | None:
    normalized = normalize_email(email)
    if len(normalized) > 254 or not _EMAIL_PATTERN.fullmatch(normalized):
        return "Enter a valid email address."
    return None


def validate_password(password: str) -> str | None:
    value = str(password or "")
    if len(value) < PASSWORD_MIN_LENGTH:
        return "Password must be at least 8 characters."
    if not re.search(r"[A-Z]", value) or not re.search(r"[a-z]", value) or not re.search(r"\d", value):
        return "Password must include an uppercase letter, lowercase letter, and number."
    return None


def hash_password(password: str) -> str:
    return _PASSWORD_HASHER.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _PASSWORD_HASHER.verify(password_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False
