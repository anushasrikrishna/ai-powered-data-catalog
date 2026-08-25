from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
from typing import Any

import streamlit as st


CONNECTION_REGISTRY_STATE_KEY = "connection_registry"


def canonical_source_type(value: str) -> str:
    normalized = str(value).strip().lower()
    return {
        "mssql": "sqlserver",
        "sql_server": "sqlserver",
        "sql server": "sqlserver",
        "postgres": "postgresql",
    }.get(normalized, normalized)


def _safe_profile(source_type: str, settings: dict[str, Any]) -> dict[str, Any]:
    source = canonical_source_type(source_type)
    if source == "sqlserver":
        keys = ("host", "port", "database", "username", "driver", "encrypt", "trust_server_certificate", "windows_auth")
    elif source == "postgresql":
        keys = ("host", "port", "database", "username")
    else:
        keys = ("account", "database", "username", "role", "warehouse")
    return {key: settings.get(key) for key in keys if settings.get(key) is not None}


def logical_connection_key(source_type: str, settings: dict[str, Any]) -> str:
    profile = _safe_profile(source_type, settings)
    normalized = "|".join(f"{key}={str(profile[key]).strip().casefold()}" for key in sorted(profile))
    return f"{canonical_source_type(source_type)}|{normalized}"


def connection_id_for(source_type: str, settings: dict[str, Any]) -> str:
    digest = hashlib.sha256(logical_connection_key(source_type, settings).encode("utf-8")).hexdigest()
    return f"conn_{digest[:20]}"


@dataclass
class ConnectionEntry:
    connection_id: str
    source_type: str
    display_name: str
    server_or_account: str
    port: int | str | None
    database_name: str
    username: str | None
    status: str = "CONNECTED"
    connector: Any | None = field(default=None, repr=False, compare=False)
    profile: dict[str, Any] = field(default_factory=dict)
    settings_signature: str = field(default="", repr=False)
    _runtime_settings: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def connected(self) -> bool:
        return self.status == "CONNECTED" and self.connector is not None


class ConnectionRegistry:
    """Session-runtime registry containing only active, non-serialized connections."""

    def __init__(self) -> None:
        self._entries: dict[str, ConnectionEntry] = {}

    def entries(self) -> list[ConnectionEntry]:
        return list(self._entries.values())

    def get(self, connection_id: str | None) -> ConnectionEntry | None:
        return self._entries.get(connection_id) if connection_id else None

    def register(
        self,
        source_type: str,
        settings: dict[str, Any],
        connector: Any,
        settings_signature: str = "",
    ) -> ConnectionEntry:
        canonical = canonical_source_type(source_type)
        profile = _safe_profile(canonical, settings)
        connection_id = connection_id_for(canonical, settings)
        existing = self._entries.get(connection_id)
        if existing is not None and existing.connector is not None and existing.connector is not connector:
            _dispose(existing.connector)
        server_or_account = str(profile.get("host") or profile.get("account") or "").strip()
        entry = existing or ConnectionEntry(
            connection_id=connection_id,
            source_type=canonical,
            display_name=f"{canonical.replace('_', ' ').title()} / {profile.get('database', '')}",
            server_or_account=server_or_account,
            port=profile.get("port"),
            database_name=str(profile.get("database") or "").strip(),
            username=str(profile.get("username") or "").strip() or None,
        )
        entry.source_type = canonical
        entry.profile = profile
        entry.server_or_account = server_or_account
        entry.port = profile.get("port")
        entry.database_name = str(profile.get("database") or "").strip()
        entry.username = str(profile.get("username") or "").strip() or None
        entry.connector = connector
        entry.status = "CONNECTED"
        entry.settings_signature = settings_signature
        entry._runtime_settings = dict(settings)
        self._entries[connection_id] = entry
        return entry

    def find(self, source_type: str, database_name: str) -> ConnectionEntry | None:
        canonical = canonical_source_type(source_type)
        database = str(database_name).strip().casefold()
        matches = [
            entry
            for entry in self._entries.values()
            if entry.source_type == canonical and entry.database_name.casefold() == database
        ]
        return matches[0] if len(matches) == 1 else None

    def disconnect(self, connection_id: str) -> ConnectionEntry | None:
        entry = self._entries.pop(connection_id, None)
        if entry is None:
            return None
        if entry.connector is not None:
            _dispose(entry.connector)
        entry.connector = None
        return entry


def _dispose(connector: Any) -> None:
    for method_name in ("dispose", "disconnect", "close"):
        method = getattr(connector, method_name, None)
        if callable(method):
            try:
                method()
            except Exception:
                pass
            return


def get_connection_registry() -> ConnectionRegistry:
    registry = st.session_state.get(CONNECTION_REGISTRY_STATE_KEY)
    if not isinstance(registry, ConnectionRegistry):
        registry = ConnectionRegistry()
        st.session_state[CONNECTION_REGISTRY_STATE_KEY] = registry
    return registry


__all__ = [
    "CONNECTION_REGISTRY_STATE_KEY",
    "ConnectionEntry",
    "ConnectionRegistry",
    "canonical_source_type",
    "connection_id_for",
    "get_connection_registry",
    "logical_connection_key",
]
