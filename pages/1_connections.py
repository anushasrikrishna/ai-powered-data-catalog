from __future__ import annotations

import streamlit as st

from ui.components import render_page_header
from ui.connection_workflow import render_connection_workflow, render_table_preview, run_table_preview


render_page_header(
    "Connections",
    "Manage and validate your enterprise data sources.",
    "Choose a platform, test access, and browse the databases, schemas, and tables available to you.",
    icon="database",
)

selection = render_connection_workflow()

if selection is not None:
    if st.button("Preview Table", icon=":material/visibility:", key="connections_preview_button"):
        run_table_preview(selection)

    render_table_preview(selection)
