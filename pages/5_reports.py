import streamlit as st

from ui.components import render_empty_state, render_feature_card, render_page_header


render_page_header(
    "Reports",
    "Generate and export metadata and quality documentation.",
    "Package catalog context and quality findings into clear, shareable reports.",
    icon="report",
)

columns = st.columns(2)
for column, (title, description, key) in zip(
    columns,
    [
        ("HTML Report", "Browser-friendly interactive documentation.", "html"),
        ("Markdown Report", "Portable documentation for repositories and reviews.", "markdown"),
    ],
):
    with column:
        render_feature_card("report", title, description, "Not available yet")
        st.button("Generate Report", icon=":material/description:", disabled=True, key=f"report_{key}")

render_empty_state("Reports are not available yet.", "Report generation will be available after metadata and quality results exist.", "report")
