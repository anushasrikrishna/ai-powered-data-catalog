import streamlit as st

from ui.components import render_empty_state, render_metric_card, render_page_header


render_page_header(
    "Data Quality",
    "Monitor the reliability and completeness of your data.",
    "Review deterministic checks and quality signals for the datasets in your catalog.",
    icon="quality",
)

metric_columns = st.columns(3)
for column, card in zip(
    metric_columns,
    [
        ("--", "Quality Score", "Overall dataset health"),
        ("--", "Passed Checks", "Checks meeting expectations"),
        ("--", "Failed Checks", "Checks needing attention"),
    ],
):
    with column:
        render_metric_card(*card)

st.markdown('<div class="section-kicker">QUALITY CHECKS</div>', unsafe_allow_html=True)
st.subheader("Quality Checks")
render_empty_state("No quality checks have been run.", "Quality results will appear here after datasets and checks are available.", "quality")
