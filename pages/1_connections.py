from __future__ import annotations

import hashlib
from typing import Any

import streamlit as st

from connectors.exceptions import ConnectorError
from connectors.postgres_connector import PostgresConnector
from connectors.snowflake_connector import SnowflakeConnector
from connectors.sqlserver_connector import SQLServerConnector
from ui.components import render_empty_state, render_page_header


SOURCE_OPTIONS = ("SQL Server", "PostgreSQL", "Snowflake")
CONNECTOR_STATE_KEY = "connections_connector"
SIGNATURE_STATE_KEY = "connections_settings_signature"
DATABASES_STATE_KEY = "connections_databases"
STATUS_STATE_KEY = "connections_status"
CONFIGURED_DATABASE_STATE_KEY = "connections_configured_database"
CONFIGURED_SCHEMA_STATE_KEY = "connections_configured_schema"
PREVIEW_COLUMNS_KEY = "connections_preview_columns"
PREVIEW_ROWS_KEY = "connections_preview_rows"
PREVIEW_TABLE_KEY = "connections_preview_table"
PREVIEW_SCHEMA_KEY = "connections_preview_schema"
PREVIEW_DATABASE_KEY = "connections_preview_database"


def _clear_preview() -> None:
    for key in (
        PREVIEW_COLUMNS_KEY,
        PREVIEW_ROWS_KEY,
        PREVIEW_TABLE_KEY,
        PREVIEW_SCHEMA_KEY,
        PREVIEW_DATABASE_KEY,
    ):
        st.session_state.pop(key, None)


def _clear_browse_selection() -> None:
    for key in (
        "connections_selected_database",
        "connections_selected_schema",
        "connections_selected_table",
    ):
        st.session_state.pop(key, None)
    _clear_preview()


def _dispose_connector() -> None:
    connector = st.session_state.pop(CONNECTOR_STATE_KEY, None)
    st.session_state.pop(SIGNATURE_STATE_KEY, None)
    st.session_state.pop(DATABASES_STATE_KEY, None)
    st.session_state.pop(CONFIGURED_DATABASE_STATE_KEY, None)
    st.session_state.pop(CONFIGURED_SCHEMA_STATE_KEY, None)
    _clear_browse_selection()
    if connector is not None:
        connector.dispose()


def _source_changed() -> None:
    _dispose_connector()
    st.session_state[STATUS_STATE_KEY] = "not_configured"


def _settings_signature(source: str, settings: dict[str, Any]) -> str:
    values = "\x1f".join([source] + [str(settings[key]) for key in settings])
    return hashlib.sha256(values.encode("utf-8")).hexdigest()


def _safe_connection_error(message: str) -> str:
    """Keep connector errors useful without exposing credentials or URLs."""
    lowered = message.lower()
    if "password" in lowered or "secret" in lowered or "token" in lowered:
        return "The connection failed. Verify the supplied connection details."
    return message


def _connector_for(source: str, settings: dict[str, Any]) -> Any:
    if source == "SQL Server":
        return SQLServerConnector(**settings)
    if source == "PostgreSQL":
        return PostgresConnector(**settings)
    return SnowflakeConnector(**settings)


def _validated_port(settings: dict[str, Any]) -> dict[str, Any] | None:
    raw_port = str(settings["port"]).strip()
    if not raw_port.isdigit():
        st.error("Port must be a valid number.")
        return None
    port = int(raw_port)
    if not 1 <= port <= 65535:
        st.error("Port must be between 1 and 65535.")
        return None
    validated = dict(settings)
    validated["port"] = port
    return validated


def _is_localdb_host(host: str) -> bool:
    return str(host).strip().lower().startswith("(localdb)\\")


def _find_option_index(options: list[str], preferred: str | None) -> int:
    if not options or not preferred:
        return 0
    if preferred in options:
        return options.index(preferred)
    preferred_lower = preferred.casefold()
    for index, option in enumerate(options):
        if option.casefold() == preferred_lower:
            return index
    return 0


def _render_sql_server_form() -> dict[str, Any]:
    left, right = st.columns(2)
    with left:
        host = st.text_input("Host", key="connections_sqlserver_host")
        database = st.text_input("Database", key="connections_sqlserver_database")
        authentication = st.selectbox(
            "Authentication",
            ["SQL Server Authentication", "Windows Authentication"],
            key="connections_sqlserver_authentication",
        )
        windows_auth = authentication == "Windows Authentication"
        if windows_auth:
            username = None
            password = None
        else:
            username = st.text_input("Username", key="connections_sqlserver_username")
            password = st.text_input("Password", type="password", key="connections_sqlserver_password")
    with right:
        localdb_windows_auth = windows_auth and _is_localdb_host(host)
        if localdb_windows_auth:
            port = None
        else:
            port = st.text_input("Port", value="1433", key="connections_sqlserver_port")
        driver = st.text_input(
            "ODBC Driver",
            value="ODBC Driver 17 for SQL Server",
            key="connections_sqlserver_driver",
        )
        encrypt = st.selectbox(
            "Encrypt",
            ["yes", "no"],
            index=1,
            key="connections_sqlserver_encrypt",
        )
        trust_server_certificate = st.selectbox(
            "Trust Server Certificate",
            ["yes", "no"],
            key="connections_sqlserver_trust_certificate",
        )
    return {
        "host": host,
        "port": port,
        "database": database,
        "username": username,
        "password": password,
        "driver": driver,
        "encrypt": encrypt,
        "trust_server_certificate": trust_server_certificate,
        "windows_auth": windows_auth,
    }


def _render_postgres_form() -> dict[str, Any]:
    left, right = st.columns(2)
    with left:
        host = st.text_input("Host", key="connections_postgres_host")
        database = st.text_input("Database", key="connections_postgres_database")
        username = st.text_input("Username", key="connections_postgres_username")
    with right:
        port = st.text_input("Port", value="5432", key="connections_postgres_port")
        password = st.text_input("Password", type="password", key="connections_postgres_password")
    return {
        "host": host,
        "port": port,
        "database": database,
        "username": username,
        "password": password,
    }


def _render_snowflake_form() -> dict[str, Any]:
    left, right = st.columns(2)
    with left:
        account = st.text_input("Account", key="connections_snowflake_account")
        username = st.text_input("Username", key="connections_snowflake_username")
        password = st.text_input("Password", type="password", key="connections_snowflake_password")
        warehouse = st.text_input("Warehouse", key="connections_snowflake_warehouse")
    with right:
        database = st.text_input("Database", key="connections_snowflake_database")
        schema = st.text_input("Schema", key="connections_snowflake_schema")
        role = st.text_input("Role", key="connections_snowflake_role")
    return {
        "account": account,
        "username": username,
        "password": password,
        "warehouse": warehouse,
        "database": database,
        "schema": schema,
        "role": role,
    }


def _render_browse_flow(connector: Any, databases: list[str], source: str) -> None:
    if not databases:
        render_empty_state("No databases available", "The connected user has no accessible databases.", "database")
        return

    selected_database = st.selectbox(
        "Database",
        databases,
        index=_find_option_index(
            databases,
            st.session_state.get(CONFIGURED_DATABASE_STATE_KEY),
        ),
        key="connections_selected_database",
        on_change=_clear_preview,
    )
    try:
        schemas = connector.list_schemas(selected_database)
    except ConnectorError as exc:
        st.error(_safe_connection_error(str(exc)))
        return
    except Exception:
        st.error("Schemas could not be loaded. Verify the selected database and permissions.")
        return

    if not schemas:
        render_empty_state("No schemas available", "The selected database contains no browsable schemas.", "catalog")
        return

    selected_schema = st.selectbox(
        "Schema",
        schemas,
        index=_find_option_index(
            schemas,
            "dbo"
            if source == "SQL Server"
            else "public"
            if source == "PostgreSQL"
            else st.session_state.get(CONFIGURED_SCHEMA_STATE_KEY),
        ),
        key="connections_selected_schema",
        on_change=_clear_preview,
    )
    try:
        tables = connector.list_tables(selected_schema)
    except ConnectorError as exc:
        st.error(_safe_connection_error(str(exc)))
        return
    except Exception:
        st.error("Tables could not be loaded. Verify the selected schema and permissions.")
        return

    if not tables:
        render_empty_state("No tables available", "The selected schema contains no browsable tables.", "catalog")
        return

    st.markdown('<div class="section-kicker">AVAILABLE TABLES</div>', unsafe_allow_html=True)
    selected_table = st.selectbox(
        "Table",
        tables,
        key="connections_selected_table",
        on_change=_clear_preview,
    )
    st.caption(f"{len(tables)} table(s) available in {selected_schema}.")

    if st.button("Preview Table", icon=":material/visibility:", key="connections_preview_button"):
        _clear_preview()
        try:
            columns = connector.get_columns(selected_schema, selected_table)
            st.session_state[PREVIEW_COLUMNS_KEY] = columns
            st.session_state[PREVIEW_TABLE_KEY] = selected_table
            st.session_state[PREVIEW_SCHEMA_KEY] = selected_schema
            st.session_state[PREVIEW_DATABASE_KEY] = selected_database
        except ConnectorError as exc:
            st.error(_safe_connection_error(str(exc)))
        except Exception as exc:
            st.error(_safe_connection_error(str(exc)))

        if PREVIEW_COLUMNS_KEY in st.session_state:
            try:
                rows = connector.get_sample_rows(selected_schema, selected_table, limit=5)
                st.session_state[PREVIEW_ROWS_KEY] = rows[:5]
            except ConnectorError as exc:
                st.error(_safe_connection_error(str(exc)))
            except Exception as exc:
                st.error(_safe_connection_error(str(exc)))

    preview_matches_selection = (
        st.session_state.get(PREVIEW_DATABASE_KEY) == selected_database
        and st.session_state.get(PREVIEW_SCHEMA_KEY) == selected_schema
        and st.session_state.get(PREVIEW_TABLE_KEY) == selected_table
    )
    if preview_matches_selection and PREVIEW_COLUMNS_KEY in st.session_state:
        st.markdown('<div class="section-kicker">TABLE OVERVIEW</div>', unsafe_allow_html=True)
        st.subheader(st.session_state[PREVIEW_TABLE_KEY])
        st.dataframe(
            st.session_state[PREVIEW_COLUMNS_KEY],
            use_container_width=True,
            hide_index=True,
        )
        st.markdown('<div class="section-kicker">SAMPLE DATA</div>', unsafe_allow_html=True)
        st.caption("Showing up to 5 rows.")
        if PREVIEW_ROWS_KEY in st.session_state:
            st.dataframe(
                st.session_state[PREVIEW_ROWS_KEY],
                use_container_width=True,
                hide_index=True,
            )


render_page_header(
    "Connections",
    "Manage and validate your enterprise data sources.",
    "Choose a platform, test access, and browse the databases, schemas, and tables available to you.",
    icon="database",
)

st.markdown('<div class="section-kicker">CHOOSE A DATA SOURCE</div>', unsafe_allow_html=True)
source = st.radio(
    "Data source",
    SOURCE_OPTIONS,
    horizontal=True,
    key="connections_source",
    on_change=_source_changed,
    label_visibility="collapsed",
)

st.markdown('<div class="section-kicker">CONNECTION DETAILS</div>', unsafe_allow_html=True)
if source == "SQL Server":
    settings = _render_sql_server_form()
elif source == "PostgreSQL":
    settings = _render_postgres_form()
else:
    settings = _render_snowflake_form()

signature = _settings_signature(source, settings)
if st.session_state.get(SIGNATURE_STATE_KEY) not in (None, signature):
    _dispose_connector()
    st.session_state[STATUS_STATE_KEY] = "not_configured"

if st.button("Test Connection", type="primary", icon=":material/bolt:", key="connections_test_button"):
    _dispose_connector()
    st.session_state[STATUS_STATE_KEY] = "connecting"
    try:
        validated_settings = settings
        localdb_windows_auth = (
            source == "SQL Server"
            and settings.get("windows_auth")
            and _is_localdb_host(settings.get("host", ""))
        )
        if source in {"SQL Server", "PostgreSQL"} and not localdb_windows_auth:
            validated_settings = _validated_port(settings)
            if validated_settings is None:
                st.session_state[STATUS_STATE_KEY] = "failed"
                st.stop()
        if source == "SQL Server" and not settings.get("windows_auth"):
            if not str(settings.get("username") or "").strip() or not str(settings.get("password") or ""):
                st.session_state[STATUS_STATE_KEY] = "failed"
                st.error("Username and password are required for SQL Server Authentication.")
                st.stop()
        connector = _connector_for(source, validated_settings)
        if connector.test_connection() is not True:
            raise RuntimeError("The connector did not confirm a successful connection.")
        databases = connector.list_databases()
        st.session_state[CONNECTOR_STATE_KEY] = connector
        st.session_state[SIGNATURE_STATE_KEY] = signature
        st.session_state[DATABASES_STATE_KEY] = databases
        st.session_state[CONFIGURED_DATABASE_STATE_KEY] = str(
            settings.get("database") or ""
        ).strip()
        st.session_state[CONFIGURED_SCHEMA_STATE_KEY] = (
            str(settings.get("schema") or "").strip() if source == "Snowflake" else None
        )
        st.session_state[STATUS_STATE_KEY] = "connected"
        st.success("Connected successfully.")
    except ConnectorError as exc:
        if "connector" in locals():
            connector.dispose()
        st.session_state[STATUS_STATE_KEY] = "failed"
        st.error(_safe_connection_error(str(exc)))
    except Exception:
        if "connector" in locals():
            connector.dispose()
        st.session_state[STATUS_STATE_KEY] = "failed"
        st.error("Connection failed. Verify the supplied connection details and permissions.")

if st.session_state.get(STATUS_STATE_KEY) == "connected":
    st.success("Connection is ready for database, schema, and table browsing.")
    _render_browse_flow(
        st.session_state[CONNECTOR_STATE_KEY],
        st.session_state.get(DATABASES_STATE_KEY, []),
        source,
    )
elif st.session_state.get(STATUS_STATE_KEY) == "not_configured":
    st.info("Enter connection details and test the connection to begin browsing.")
