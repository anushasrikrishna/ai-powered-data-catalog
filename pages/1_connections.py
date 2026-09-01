from __future__ import annotations

import streamlit as st

from auth.session import require_authenticated
from ui.components import render_page_header
from ui.connection_workflow import render_connection_workflow, render_connections_table


require_authenticated()


render_page_header(
    "Connections",
    "Manage and validate your enterprise data sources.",
    "Choose a platform, test access, and browse the databases, schemas, and tables available to you.",
    icon="database",
)

render_connections_table()
render_connection_workflow(include_browse=False)
