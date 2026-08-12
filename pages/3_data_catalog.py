import streamlit as st

from ui.components import render_empty_state, render_page_header


render_page_header(
    "Data Catalog",
    "Discover trusted datasets across your connected platforms.",
    "Search the shared inventory of documented datasets and their business context.",
    icon="catalog",
)

st.markdown('<div class="toolbar-panel">', unsafe_allow_html=True)
search_column, source_column, schema_column = st.columns([2, 1, 1])
with search_column:
    st.text_input("Search datasets", placeholder="Search datasets, tables or columns", disabled=True)
with source_column:
    st.selectbox("Source", ["All sources"], disabled=True)
with schema_column:
    st.selectbox("Schema", ["All schemas"], disabled=True)
st.markdown('</div>', unsafe_allow_html=True)

render_empty_state("Catalog workspace is empty", "Scan metadata to populate the catalog with trusted dataset documentation.", "catalog")
