from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from uuid import uuid4

from auth.models import AuthenticatedUser
from auth.security import hash_password, normalize_email, normalize_username, validate_email, validate_password, validate_username, verify_password
from storage.user_repository import UserAlreadyExistsError, UserRepository


PASSWORD_RESET_TTL = timedelta(minutes=20)


class AuthenticationService:
    def __init__(self, repository: UserRepository | None = None) -> None:
        self.repository = repository or UserRepository()

    def register(self, username: str, email: str, password: str, confirm_password: str) -> AuthenticatedUser:
        username = normalize_username(username)
        email = normalize_email(email)
        for error in (validate_username(username), validate_email(email), validate_password(password)):
            if error:
                raise ValueError(error)
        if password != confirm_password:
            raise ValueError("Passwords do not match.")
        if self.repository.username_exists(username):
            raise ValueError("Username is already in use.")
        if self.repository.email_exists(email):
            raise ValueError("Email is already registered.")
        try:
            record = self.repository.create_user(username, email, hash_password(password))
        except UserAlreadyExistsError as exc:
            raise ValueError("Username or email is already registered.") from exc
        return AuthenticatedUser(record.user_id, record.username, record.email)

    def authenticate(self, identifier: str, password: str) -> AuthenticatedUser | None:
        value = str(identifier or "").strip()
        record = self.repository.get_by_email(normalize_email(value)) if "@" in value else self.repository.get_by_username(normalize_username(value))
        if record is None or not record.is_active or not verify_password(password, record.password_hash):
            return None
        return AuthenticatedUser(record.user_id, record.username, record.email)

    def begin_password_reset(self, email: str) -> str | None:
        record = self.repository.get_by_email(normalize_email(email))
        if record is None or not record.is_active:
            return None
        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        expires_at = (datetime.now(timezone.utc) + PASSWORD_RESET_TTL).isoformat()
        self.repository.create_password_reset_token(record.user_id, token_hash, expires_at, str(uuid4()))
        return token

    def reset_password(self, token: str, password: str, confirm_password: str) -> bool:
        error = validate_password(password)
        if error:
            raise ValueError(error)
        if password != confirm_password:
            raise ValueError("Passwords do not match.")
        token_value = str(token or "")
        if not token_value:
            return False
        token_hash = hashlib.sha256(token_value.encode("utf-8")).hexdigest()
        return self.repository.consume_password_reset(token_hash, hash_password(password))
