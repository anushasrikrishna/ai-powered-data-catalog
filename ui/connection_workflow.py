from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

import streamlit as st

from connectors.exceptions import ConnectorError
from connectors.postgres_connector import PostgresConnector
from connectors.snowflake_connector import SnowflakeConnector
from connectors.sqlserver_connector import SQLServerConnector
from core.connection_registry import ConnectionEntry, connection_id_for, get_connection_registry
from ui.components import loading_indicator, render_empty_state, render_html_table


SOURCE_OPTIONS = ("SQL Server", "PostgreSQL", "Snowflake")
CHOOSE_SCHEMA = "Choose a schema"
CHOOSE_TABLE = "Choose a table"

CONNECTOR_STATE_KEY = "connections_connector"
ACTIVE_CONNECTION_ID_KEY = "connections_active_connection_id"
SOURCE_STATE_KEY = "connections_source"
SIGNATURE_STATE_KEY = "connections_settings_signature"
STATUS_STATE_KEY = "connections_status"
ACTIVE_SOURCE_STATE_KEY = "connections_active_source"
ACTIVE_DATABASE_STATE_KEY = "connections_active_database"
CONFIGURED_DATABASE_STATE_KEY = "connections_configured_database"
SCHEMAS_STATE_KEY = "connections_schemas"
SCHEMAS_CONNECTION_KEY = "connections_schemas_connection"
TABLES_STATE_KEY = "connections_tables"
TABLES_SCHEMA_STATE_KEY = "connections_tables_schema"
TABLES_CONNECTION_KEY = "connections_tables_connection"
SELECTED_SCHEMA_STATE_KEY = "connections_selected_schema"
SELECTED_TABLE_STATE_KEY = "connections_selected_table"
PREVIEW_COLUMNS_KEY = "connections_preview_columns"
PREVIEW_ROWS_KEY = "connections_preview_rows"
PREVIEW_TABLE_KEY = "connections_preview_table"
PREVIEW_SCHEMA_KEY = "connections_preview_schema"
PREVIEW_DATABASE_KEY = "connections_preview_database"

SOURCE_TYPE_BY_DISPLAY_NAME = {
    "SQL Server": "sqlserver",
    "PostgreSQL": "postgresql",
    "Snowflake": "snowflake",
}
SOURCE_DISPLAY_NAME_BY_TYPE = {
    "sqlserver": "SQL Server",
    "postgresql": "PostgreSQL",
    "snowflake": "Snowflake",
}


@dataclass(frozen=True)
class ConnectionWorkflowSelection:
    connector: Any
    source_display_name: str
    source_type: str
    database_name: str
    schema_name: str
    table_name: str


def source_type(source_display_name: str) -> str:
    return SOURCE_TYPE_BY_DISPLAY_NAME.get(source_display_name, source_display_name.strip().lower())


def source_display_name(source_value: str) -> str:
    normalized = source_value.strip().lower()
    return SOURCE_DISPLAY_NAME_BY_TYPE.get(normalized, source_value)


def safe_connection_error(message: str) -> str:
    lowered = message.lower()
    if "password" in lowered or "secret" in lowered or "token" in lowered:
        return "The connection failed. Verify the supplied connection details."
    return message


def _connection_status_cell(value: Any, _row: dict[Any, Any]) -> str:
    return '<span class="connection-status connection-status--connected"><span aria-hidden="true">●</span> Connected</span>'


def _connection_rows() -> list[dict[str, Any]]:
    rows = []
    for entry in get_connection_registry().entries():
        rows.append(
            {
                "Source": source_display_name(entry.source_type),
                "Database": entry.database_name or "—",
                "Server / Account": entry.server_or_account or "—",
                "Status": "CONNECTED",
                "Action": entry.connection_id,
            }
        )
    return rows


def _invalidate_quality_result_for(entry: ConnectionEntry) -> None:
    target = str(st.session_state.get("quality_execution_result_dataset", ""))
    prefix = f"{entry.source_type}|{entry.database_name.strip().lower()}|"
    if target.startswith(prefix):
        for key in (
            "quality_execution_result",
            "quality_execution_result_dataset",
            "quality_execution_result_rule_signature",
        ):
            st.session_state.pop(key, None)
        st.session_state["quality_review_ready"] = False
        st.session_state["quality_run_status"] = "ready"


def _disconnect_connection(index: int) -> None:
    entries = get_connection_registry().entries()
    if index < len(entries):
        connection_id = entries[index].connection_id
        entry = get_connection_registry().disconnect(connection_id)
        if entry is not None:
            _invalidate_quality_result_for(entry)
        if st.session_state.get(ACTIVE_CONNECTION_ID_KEY) == connection_id:
            _clear_browse_selection()
            st.session_state.pop(ACTIVE_CONNECTION_ID_KEY, None)
            st.session_state.pop(CONNECTOR_STATE_KEY, None)
            st.session_state[STATUS_STATE_KEY] = "not_configured"
        st.rerun()


def render_connections_table() -> None:
    """Render active session connections using the shared table UI."""
    st.markdown('<div class="section-kicker">CONNECTIONS</div>', unsafe_allow_html=True)
    rows = _connection_rows()
    if not rows:
        st.caption("No active source connections in this session.")
        return
    action_items = [
        {"label": "Disconnect", "key_prefix": "disconnect-connection", "help": "Disconnect", "callback": _disconnect_connection},
    ]
    render_html_table(
        rows,
        table_id="session-connections",
        download=False,
        column_widths=[20, 22, 27, 16, 15],
        cell_renderers={"Status": _connection_status_cell},
        action={"header": "Action", "actions": action_items},
    )


def render_connected_sources_table() -> None:
    """Render connected registry entries as read-only Data Quality context."""
    st.markdown('<div class="section-kicker">CONNECTED SOURCES</div>', unsafe_allow_html=True)
    entries = [entry for entry in get_connection_registry().entries() if entry.connected]
    if not entries:
        st.caption("No live source connections are currently available.")
        return
    rows = [
        {
            "Source": source_display_name(entry.source_type),
            "Database": entry.database_name or "—",
            "Server / Account": entry.server_or_account or "—",
            "Status": "CONNECTED",
        }
        for entry in entries
    ]
    render_html_table(
        rows,
        table_id="connected-quality-sources",
        download=False,
        column_widths=[20, 22, 27, 31],
        cell_renderers={"Status": _connection_status_cell},
    )


def clear_preview() -> None:
    for key in (
        PREVIEW_COLUMNS_KEY,
        PREVIEW_ROWS_KEY,
        PREVIEW_TABLE_KEY,
        PREVIEW_SCHEMA_KEY,
        PREVIEW_DATABASE_KEY,
    ):
        st.session_state.pop(key, None)


def clear_keys(keys: tuple[str, ...] = ()) -> None:
    for key in keys:
        st.session_state.pop(key, None)


def _clear_browse_selection(extra_clear_keys: tuple[str, ...] = ()) -> None:
    for key in (
        SELECTED_SCHEMA_STATE_KEY,
        SELECTED_TABLE_STATE_KEY,
        SCHEMAS_STATE_KEY,
        TABLES_STATE_KEY,
        TABLES_SCHEMA_STATE_KEY,
        SCHEMAS_CONNECTION_KEY,
        TABLES_CONNECTION_KEY,
    ):
        st.session_state.pop(key, None)
    clear_preview()
    clear_keys(extra_clear_keys)


def dispose_connector(extra_clear_keys: tuple[str, ...] = ()) -> None:
    registry = get_connection_registry()
    connection_id = st.session_state.pop(ACTIVE_CONNECTION_ID_KEY, None)
    if connection_id:
        registry.disconnect(connection_id)
    st.session_state.pop(CONNECTOR_STATE_KEY, None)
    st.session_state.pop(SIGNATURE_STATE_KEY, None)
    st.session_state.pop(ACTIVE_SOURCE_STATE_KEY, None)
    st.session_state.pop(ACTIVE_DATABASE_STATE_KEY, None)
    st.session_state.pop(CONFIGURED_DATABASE_STATE_KEY, None)
    _clear_browse_selection(extra_clear_keys)


def _source_changed(extra_clear_keys: tuple[str, ...] = ()) -> None:
    st.session_state.pop(ACTIVE_CONNECTION_ID_KEY, None)
    st.session_state.pop(CONNECTOR_STATE_KEY, None)
    st.session_state.pop(ACTIVE_SOURCE_STATE_KEY, None)
    st.session_state.pop(ACTIVE_DATABASE_STATE_KEY, None)
    st.session_state.pop(CONFIGURED_DATABASE_STATE_KEY, None)
    _clear_browse_selection(extra_clear_keys)
    st.session_state[STATUS_STATE_KEY] = "not_configured"


def _schema_changed(extra_clear_keys: tuple[str, ...] = ()) -> None:
    st.session_state.pop(SELECTED_TABLE_STATE_KEY, None)
    st.session_state.pop(TABLES_STATE_KEY, None)
    st.session_state.pop(TABLES_SCHEMA_STATE_KEY, None)
    clear_preview()
    clear_keys(extra_clear_keys)


def _table_changed(extra_clear_keys: tuple[str, ...] = ()) -> None:
    clear_preview()
    clear_keys(extra_clear_keys)


def _settings_signature(source: str, settings: dict[str, Any]) -> str:
    values = "\x1f".join([source] + [str(settings[key]) for key in settings])
    return hashlib.sha256(values.encode("utf-8")).hexdigest()


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


def find_option_index(options: list[str], preferred: str | None) -> int:
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
    row_one_left, row_one_right = st.columns(2)
    with row_one_left:
        account = st.text_input("Account", key="connections_snowflake_account")
    with row_one_right:
        database = st.text_input("Database", key="connections_snowflake_database")

    row_two_left, row_two_right = st.columns(2)
    with row_two_left:
        username = st.text_input("Username", key="connections_snowflake_username")
    with row_two_right:
        password = st.text_input("Password", type="password", key="connections_snowflake_password")

    row_three_left, row_three_right = st.columns(2)
    with row_three_left:
        role = st.text_input("Role", key="connections_snowflake_role")
    with row_three_right:
        warehouse = st.text_input("Warehouse", key="connections_snowflake_warehouse")

    return {
        "account": account,
        "username": username,
        "password": password,
        "warehouse": warehouse,
        "database": database,
        "role": role,
    }


def _preferred_schema(source: str, schemas: list[str]) -> str | None:
    if source == "SQL Server":
        preferred = "dbo"
    elif source == "PostgreSQL":
        preferred = "public"
    elif source == "Snowflake":
        preferred = st.session_state.get(SELECTED_SCHEMA_STATE_KEY)
    else:
        preferred = None

    if preferred:
        return schemas[find_option_index(schemas, preferred)] if schemas else None
    return schemas[0] if schemas else None


def _render_connection_form(source: str) -> dict[str, Any]:
    if source == "SQL Server":
        return _render_sql_server_form()
    if source == "PostgreSQL":
        return _render_postgres_form()
    return _render_snowflake_form()


def _test_connection(source: str, settings: dict[str, Any], signature: str, extra_clear_keys: tuple[str, ...]) -> None:
    st.session_state[STATUS_STATE_KEY] = "connecting"
    connector = None
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
                return
        if source == "SQL Server" and not settings.get("windows_auth"):
            if not str(settings.get("username") or "").strip() or not str(settings.get("password") or ""):
                st.session_state[STATUS_STATE_KEY] = "failed"
                st.error("Username and password are required for SQL Server Authentication.")
                return
        with loading_indicator(f"Connecting to {source}..."):
            connector = _connector_for(source, validated_settings)
            if connector.test_connection() is not True:
                raise RuntimeError("The connector did not confirm a successful connection.")
            connector.list_databases()
        with loading_indicator("Loading schemas..."):
            schemas = connector.list_schemas()
        registry = get_connection_registry()
        previous_id = st.session_state.get(ACTIVE_CONNECTION_ID_KEY)
        entry = registry.register(source, validated_settings, connector, settings_signature=signature)
        if previous_id != entry.connection_id:
            _clear_browse_selection(extra_clear_keys)
        st.session_state[ACTIVE_CONNECTION_ID_KEY] = entry.connection_id
        st.session_state[CONNECTOR_STATE_KEY] = entry.connector
        st.session_state[SIGNATURE_STATE_KEY] = entry.settings_signature
        st.session_state[ACTIVE_SOURCE_STATE_KEY] = entry.source_type
        st.session_state[CONFIGURED_DATABASE_STATE_KEY] = entry.database_name
        st.session_state[ACTIVE_DATABASE_STATE_KEY] = entry.database_name
        st.session_state[SCHEMAS_STATE_KEY] = schemas
        st.session_state[SCHEMAS_CONNECTION_KEY] = entry.connection_id
        st.session_state[STATUS_STATE_KEY] = "connected"
    except ConnectorError as exc:
        if connector is not None:
            connector.dispose()
        st.session_state[STATUS_STATE_KEY] = "failed"
        st.error(safe_connection_error(str(exc)))
    except Exception:
        if connector is not None:
            connector.dispose()
        st.session_state[STATUS_STATE_KEY] = "failed"
        st.error("Connection failed. Verify the supplied connection details and permissions.")


def _render_browse_selectors(connector: Any, source: str, extra_clear_keys: tuple[str, ...]) -> ConnectionWorkflowSelection | None:
    connected_database = st.session_state.get(ACTIVE_DATABASE_STATE_KEY) or st.session_state.get(
        CONFIGURED_DATABASE_STATE_KEY, ""
    )
    st.markdown('<div class="section-kicker">CONNECTED DATABASE</div>', unsafe_allow_html=True)
    st.write(connected_database)

    connection_id = st.session_state.get(ACTIVE_CONNECTION_ID_KEY)
    schemas = st.session_state.get(SCHEMAS_STATE_KEY) if st.session_state.get(SCHEMAS_CONNECTION_KEY) == connection_id else None
    if schemas is None:
        try:
            with loading_indicator("Loading schemas..."):
                schemas = connector.list_schemas()
            st.session_state[SCHEMAS_STATE_KEY] = schemas
            st.session_state[SCHEMAS_CONNECTION_KEY] = connection_id
        except ConnectorError as exc:
            st.error(safe_connection_error(str(exc)))
            return None
        except Exception:
            st.error("Schemas could not be loaded. Verify the selected database and permissions.")
            return None

    if not schemas:
        render_empty_state("No schemas available", "The selected database contains no browsable schemas.", "catalog")
        return None

    schema_options = [CHOOSE_SCHEMA] + list(schemas)
    if st.session_state.get(SELECTED_SCHEMA_STATE_KEY) not in schema_options:
        st.session_state[SELECTED_SCHEMA_STATE_KEY] = CHOOSE_SCHEMA
        clear_preview()
        clear_keys(extra_clear_keys)

    selected_schema = st.selectbox(
        "Schema",
        schema_options,
        key=SELECTED_SCHEMA_STATE_KEY,
        on_change=_schema_changed,
        args=(extra_clear_keys,),
    )

    if selected_schema == CHOOSE_SCHEMA:
        st.caption("Choose a schema to browse its tables.")
        return None

    tables_schema = st.session_state.get(TABLES_SCHEMA_STATE_KEY)
    tables = st.session_state.get(TABLES_STATE_KEY) if st.session_state.get(TABLES_CONNECTION_KEY) == connection_id else None
    if tables_schema != selected_schema or tables is None:
        try:
            with loading_indicator("Loading tables..."):
                tables = connector.list_tables(selected_schema)
            st.session_state[TABLES_STATE_KEY] = tables
            st.session_state[TABLES_SCHEMA_STATE_KEY] = selected_schema
            st.session_state[TABLES_CONNECTION_KEY] = connection_id
        except ConnectorError as exc:
            st.error(safe_connection_error(str(exc)))
            return None
        except Exception:
            st.error("Tables could not be loaded. Verify the selected schema and permissions.")
            return None

    if not tables:
        render_empty_state("No tables available", "The selected schema contains no browsable tables.", "catalog")
        return None

    table_options = [CHOOSE_TABLE] + list(tables)
    if st.session_state.get(SELECTED_TABLE_STATE_KEY) not in table_options:
        st.session_state[SELECTED_TABLE_STATE_KEY] = CHOOSE_TABLE
        clear_preview()
        clear_keys(extra_clear_keys)

    selected_table = st.selectbox(
        "Table",
        table_options,
        key=SELECTED_TABLE_STATE_KEY,
        on_change=_table_changed,
        args=(extra_clear_keys,),
    )
    st.caption(f"{len(tables)} table(s) available in {selected_schema}.")

    if selected_table == CHOOSE_TABLE:
        st.caption("Choose a table to preview or scan metadata.")
        return None

    return ConnectionWorkflowSelection(
        connector=connector,
        source_display_name=source,
        source_type=source_type(source),
        database_name=str(connected_database).strip(),
        schema_name=selected_schema,
        table_name=selected_table,
    )


def render_connection_workflow(extra_clear_keys: tuple[str, ...] = ()) -> ConnectionWorkflowSelection | None:
    registry = get_connection_registry()
    if STATUS_STATE_KEY not in st.session_state:
        st.session_state[STATUS_STATE_KEY] = "not_configured"

    st.markdown('<div class="section-kicker">CHOOSE A DATA SOURCE</div>', unsafe_allow_html=True)
    source = st.radio(
        "Data source",
        SOURCE_OPTIONS,
        index=find_option_index(list(SOURCE_OPTIONS), st.session_state.get(ACTIVE_SOURCE_STATE_KEY)),
        horizontal=True,
        key=SOURCE_STATE_KEY,
        on_change=_source_changed,
        args=(extra_clear_keys,),
        label_visibility="collapsed",
    )

    source_entries = [entry for entry in registry.entries() if entry.source_type == source_type(source)]
    active_connection_id = st.session_state.get(ACTIVE_CONNECTION_ID_KEY)
    selected_entry = registry.get(active_connection_id)
    if selected_entry is not None and selected_entry.source_type != source_type(source):
        selected_entry = None
        st.session_state.pop(ACTIVE_CONNECTION_ID_KEY, None)
    if selected_entry is not None:
        _populate_form_state(source, selected_entry)
        st.session_state[ACTIVE_CONNECTION_ID_KEY] = selected_entry.connection_id
    elif active_connection_id not in {entry.connection_id for entry in source_entries}:
        st.session_state.pop(ACTIVE_CONNECTION_ID_KEY, None)

    st.markdown('<div class="section-kicker">CONNECTION DETAILS</div>', unsafe_allow_html=True)
    settings = _render_connection_form(source)
    signature = _settings_signature(source, settings)

    active_entry = registry.get(st.session_state.get(ACTIVE_CONNECTION_ID_KEY))
    active_matches_form = active_entry is not None and active_entry.settings_signature == signature
    if not active_matches_form and selected_entry is None:
        active_entry = registry.get(connection_id_for(source, settings))
        if active_entry is not None:
            st.session_state[ACTIVE_CONNECTION_ID_KEY] = active_entry.connection_id
            active_matches_form = active_entry.settings_signature == signature

    if active_entry is not None and active_entry.connected and active_matches_form:
        st.session_state[CONNECTOR_STATE_KEY] = active_entry.connector
        st.session_state[SIGNATURE_STATE_KEY] = active_entry.settings_signature
        st.session_state[ACTIVE_SOURCE_STATE_KEY] = active_entry.source_type
        st.session_state[CONFIGURED_DATABASE_STATE_KEY] = active_entry.database_name
        st.session_state[ACTIVE_DATABASE_STATE_KEY] = active_entry.database_name
        st.session_state[STATUS_STATE_KEY] = "connected"
    else:
        st.session_state[STATUS_STATE_KEY] = "not_configured"

    if st.button("Test Connection", type="primary", icon=":material/bolt:", key="connections_test_button"):
        _test_connection(source, settings, signature, extra_clear_keys)

    if st.session_state.get(STATUS_STATE_KEY) == "connected" and active_entry is not None:
        st.success("Connected successfully.")
        return _render_browse_selectors(
            active_entry.connector,
            source,
            extra_clear_keys,
        )

    if st.session_state.get(STATUS_STATE_KEY) == "not_configured":
        st.info("Enter connection details and test the connection to begin browsing.")

    return None


def _populate_form_state(source: str, entry: ConnectionEntry) -> None:
    prefix = {
        "SQL Server": "connections_sqlserver_",
        "PostgreSQL": "connections_postgres_",
        "Snowflake": "connections_snowflake_",
    }[source]
    for key, value in entry._runtime_settings.items():
        st.session_state[f"{prefix}{key}"] = value


def run_table_preview(selection: ConnectionWorkflowSelection) -> None:
    clear_preview()
    with loading_indicator("Loading table preview..."):
        try:
            columns = selection.connector.get_columns(selection.schema_name, selection.table_name)
            rows = selection.connector.get_sample_rows(selection.schema_name, selection.table_name, limit=5)
            st.session_state[PREVIEW_COLUMNS_KEY] = columns
            st.session_state[PREVIEW_ROWS_KEY] = rows[:5]
            st.session_state[PREVIEW_TABLE_KEY] = selection.table_name
            st.session_state[PREVIEW_SCHEMA_KEY] = selection.schema_name
            st.session_state[PREVIEW_DATABASE_KEY] = selection.database_name
        except ConnectorError as exc:
            st.error(safe_connection_error(str(exc)))
        except Exception as exc:
            st.error(safe_connection_error(str(exc)))


def render_table_preview(selection: ConnectionWorkflowSelection) -> None:
    preview_matches_selection = (
        st.session_state.get(PREVIEW_DATABASE_KEY) == selection.database_name
        and st.session_state.get(PREVIEW_SCHEMA_KEY) == selection.schema_name
        and st.session_state.get(PREVIEW_TABLE_KEY) == selection.table_name
    )
    if not preview_matches_selection or PREVIEW_COLUMNS_KEY not in st.session_state:
        return

    st.markdown('<div class="section-kicker">TABLE OVERVIEW</div>', unsafe_allow_html=True)
    st.subheader(st.session_state[PREVIEW_TABLE_KEY])
    render_html_table(
        st.session_state[PREVIEW_COLUMNS_KEY],
        table_id="preview-column-overview",
        download_filename="preview_column_overview.csv",
    )
    st.markdown('<div class="section-kicker">SAMPLE DATA</div>', unsafe_allow_html=True)
    st.caption("Showing up to 5 rows.")
    if PREVIEW_ROWS_KEY in st.session_state:
        render_html_table(
            st.session_state[PREVIEW_ROWS_KEY],
            table_id="preview-sample-data",
            download_filename="preview_sample_data.csv",
        )
