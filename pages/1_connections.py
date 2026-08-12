import streamlit as st

from ui.components import render_page_header, render_source_card


render_page_header(
    "Connections",
    "Manage and validate your enterprise data sources.",
    "Configure source access and confirm connectivity before discovering metadata.",
    icon="database",
)

columns = st.columns(3)
sources = [
    ("SQL Server", "Microsoft SQL Server environments and relational workloads."),
    ("PostgreSQL", "Open-source PostgreSQL databases and analytical stores."),
    ("Snowflake", "Cloud data warehouse accounts and shared datasets."),
]
for column, (name, description) in zip(columns, sources):
    with column:
        render_source_card(name, description)
        st.button("Configure", icon=":material/settings:", disabled=True, key=f"configure_{name}")
