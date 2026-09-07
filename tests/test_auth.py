from __future__ import annotations

from pathlib import Path
import sqlite3
from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import MagicMock, patch

from auth.models import AuthenticatedUser
from auth.security import hash_password, validate_email, validate_password, validate_username, verify_password
from auth.service import AuthenticationService
from storage.user_repository import UserRepository


class TestAuthenticationFoundation(unittest.TestCase):
    def test_password_hash_is_not_plaintext_and_wrong_password_fails(self) -> None:
        password = "StrongPass1"
        password_hash = hash_password(password)
        self.assertNotEqual(password_hash, password)
        self.assertTrue(verify_password(password, password_hash))
        self.assertFalse(verify_password("WrongPass1", password_hash))

    def test_repository_persists_users_and_case_insensitive_lookups(self) -> None:
        with TemporaryDirectory() as directory:
            repository = UserRepository(Path(directory) / "users.db")
            created = repository.create_user(" analyst ", "Analyst@Example.com", hash_password("StrongPass1"))
            loaded = repository.get_by_username("ANALYST")
            self.assertEqual(loaded.user_id, created.user_id)
            self.assertEqual(repository.get_by_email("analyst@example.com").email, "analyst@example.com")
            with self.assertRaises(ValueError):
                repository.create_user("ANALYST", "other@example.com", hash_password("StrongPass1"))
            with self.assertRaises(ValueError):
                repository.create_user("other", "ANALYST@example.com", hash_password("StrongPass1"))
            connection = sqlite3.connect(Path(directory) / "users.db")
            try:
                stored_hash = connection.execute("SELECT password_hash FROM users").fetchone()[0]
            finally:
                connection.close()
            self.assertNotEqual(stored_hash, "StrongPass1")

    def test_service_supports_username_and_email_and_rejects_invalid_registration(self) -> None:
        with TemporaryDirectory() as directory:
            service = AuthenticationService(UserRepository(Path(directory) / "users.db"))
            created = service.register("analyst", "analyst@example.com", "StrongPass1", "StrongPass1")
            self.assertIsInstance(created, AuthenticatedUser)
            self.assertEqual(service.authenticate("analyst", "StrongPass1"), created)
            self.assertEqual(service.authenticate("ANALYST@EXAMPLE.COM", "StrongPass1"), created)
            self.assertIsNone(service.authenticate("analyst", "WrongPass1"))
            with self.assertRaises(ValueError):
                service.register("ANALYST", "other@example.com", "StrongPass1", "StrongPass1")
            with self.assertRaises(ValueError):
                service.register("other", "bad-email", "StrongPass1", "StrongPass1")
            with self.assertRaises(ValueError):
                service.register("other", "other@example.com", "weakpass", "weakpass")
            with self.assertRaises(ValueError):
                service.register("other", "other@example.com", "StrongPass1", "Different1")

    def test_policy_helpers_are_centralized(self) -> None:
        self.assertIsNone(validate_username("analyst_1"))
        self.assertIsNotNone(validate_username("ab"))
        self.assertIsNone(validate_email("analyst@example.com"))
        self.assertIsNotNone(validate_email("invalid"))
        self.assertIsNone(validate_password("StrongPass1"))
        self.assertIsNotNone(validate_password("weakpass"))

    def test_local_password_reset_is_hashed_expiring_and_single_use(self) -> None:
        with TemporaryDirectory() as directory:
            service = AuthenticationService(UserRepository(Path(directory) / "users.db"))
            service.register("analyst", "analyst@example.com", "StrongPass1", "StrongPass1")
            token = service.begin_password_reset("analyst@example.com")
            self.assertIsNotNone(token)
            assert token is not None
            self.assertTrue(service.reset_password(token, "NewStrong2", "NewStrong2"))
            self.assertIsNone(service.authenticate("analyst", "StrongPass1"))
            self.assertIsNotNone(service.authenticate("analyst", "NewStrong2"))
            self.assertFalse(service.reset_password(token, "Another3A", "Another3A"))
            self.assertIsNone(service.begin_password_reset("missing@example.com"))

    def test_expired_password_reset_cannot_change_credentials(self) -> None:
        with TemporaryDirectory() as directory:
            repository = UserRepository(Path(directory) / "users.db")
            service = AuthenticationService(repository)
            user = service.register("analyst", "analyst@example.com", "StrongPass1", "StrongPass1")
            token = secrets.token_urlsafe(24)
            repository.create_password_reset_token(
                user.user_id,
                hashlib.sha256(token.encode("utf-8")).hexdigest(),
                (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
                "expired-reset",
            )
            self.assertFalse(service.reset_password(token, "NewStrong2", "NewStrong2"))
            self.assertIsNotNone(service.authenticate("analyst", "StrongPass1"))

    def test_logout_disposes_connections_and_clears_transient_state(self) -> None:
        import auth.session as session

        state = {
            "authenticated": True,
            "current_user": AuthenticatedUser("id", "analyst", "analyst@example.com"),
            "connection_registry": object(),
            "quality_rules": [],
            "ai_suggestions": [],
            "catalog_search_query": "secret search",
            "catalog_source_filter": "SQL Server",
            "reports_selected_run": "run-1",
            "dark_mode": True,
        }
        registry = MagicMock()
        entry = MagicMock(connection_id="conn-1")
        registry.entries.return_value = [entry]
        with patch.object(session.st, "session_state", state), patch.object(session, "get_connection_registry", return_value=registry):
            session.logout()
        registry.disconnect.assert_called_once_with("conn-1")
        self.assertFalse(state["authenticated"])
        self.assertNotIn("current_user", state)
        self.assertNotIn("quality_rules", state)
        self.assertNotIn("ai_suggestions", state)
        self.assertNotIn("catalog_search_query", state)
        self.assertNotIn("catalog_source_filter", state)
        self.assertNotIn("reports_selected_run", state)
        self.assertTrue(state["dark_mode"])

    def test_auth_routing_targets_registered_pages(self) -> None:
        import auth.session as session

        overview_page = object()
        login_page = object()
        state = {session.AUTH_OVERVIEW_PAGE_KEY: overview_page, session.AUTH_LOGIN_PAGE_KEY: login_page}
        with patch.object(session.st, "session_state", state), patch.object(session.st, "switch_page") as switch_page:
            session.redirect_to_login()
            switch_page.assert_called_once_with(login_page)
        with patch.object(session.st, "session_state", state), patch.object(session.st, "switch_page") as switch_page:
            session.redirect_to_overview()
            switch_page.assert_called_once_with(overview_page)


if __name__ == "__main__":
    unittest.main()
