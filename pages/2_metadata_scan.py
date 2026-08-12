import streamlit as st

from ui.components import render_empty_state, render_page_header, render_stepper


render_page_header(
    "Metadata Scan",
    "Inspect and standardize metadata from connected data sources.",
    "Follow a guided workflow to collect the structural context that powers the catalog.",
    icon="search",
)

render_stepper(["Source", "Database", "Schema", "Table", "Scan"])
render_empty_state("Metadata workspace is empty", "Connect a source and select a table to begin scanning metadata.")
st.button("Go to Connections", icon=":material/database:", disabled=True)
