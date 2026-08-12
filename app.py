import streamlit as st

from ui.components import (
    render_app_header,
    render_get_started_workflow,
    render_quick_access_card,
    render_workspace_status,
)
from ui.theme import apply_theme, render_sidebar


st.set_page_config(
    page_title="AI-Powered Data Catalog",
    page_icon=":material/database:",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False


def request_page(page_path: str) -> None:
    """Record navigation from a button callback; switch pages outside callbacks."""
    st.session_state["pending_page"] = page_path


pending_page = st.session_state.pop("pending_page", None)
if pending_page:
    st.switch_page(pending_page)

# The application shell owns global styling, the product header, and sidebar.
apply_theme()
render_app_header()
render_sidebar()


def home_page() -> None:
    st.markdown(
        '<section class="hero-panel"><div class="hero-eyebrow">DATA INTELLIGENCE WORKSPACE</div>'
        '<div class="hero-title">Discover, understand and trust your enterprise data.</div>'
        '<div class="hero-description">Connect SQL Server, PostgreSQL and Snowflake, '
        'standardize metadata, discover datasets, monitor quality and export documentation '
        'from one workspace.</div></section>',
        unsafe_allow_html=True,
    )

    action_columns = st.columns([1.35, 1.2, 3.45])
    with action_columns[0]:
        st.button(
            "Connect Data Source",
            icon=":material/database:",
            type="primary",
            use_container_width=True,
            on_click=request_page,
            args=("pages/1_connections.py",),
        )
    with action_columns[1]:
        st.button(
            "Explore Catalog",
            icon=":material/library_books:",
            type="secondary",
            use_container_width=True,
            on_click=request_page,
            args=("pages/3_data_catalog.py",),
        )

    st.markdown('<div class="section-kicker">WORKSPACE SNAPSHOT</div>', unsafe_allow_html=True)
    render_workspace_status(
        [
            ("database", "Connected Sources", "0", "No sources connected"),
            ("catalog", "Cataloged Datasets", "0", "No datasets indexed"),
            ("quality", "Quality Score", "--", "Run quality checks to calculate"),
        ]
    )

    st.markdown('<div class="section-kicker">GET STARTED</div>', unsafe_allow_html=True)
    st.subheader("From connection to trusted data")
    render_get_started_workflow(
        [
            ("database", "Connect"),
            ("search", "Scan"),
            ("catalog", "Catalog"),
            ("quality", "Quality"),
            ("report", "Export"),
        ]
    )

    st.markdown('<div class="section-kicker">QUICK ACCESS</div>', unsafe_allow_html=True)
    quick_access = [
        ("database", "Connections", "Configure and manage data sources.", "pages/1_connections.py"),
        ("catalog", "Data Catalog", "Discover available datasets.", "pages/3_data_catalog.py"),
        ("quality", "Data Quality", "Review quality checks and scores.", "pages/4_data_quality.py"),
    ]
    quick_columns = st.columns(3)
    for column, (icon, title, description, page_path) in zip(quick_columns, quick_access):
        with column:
            render_quick_access_card(icon, title, description, request_page, page_path)


pages = [
    st.Page(home_page, title="Overview", icon=":material/dashboard:", default=True),
    st.Page("pages/1_connections.py", title="Connections", icon=":material/database:"),
    st.Page("pages/2_metadata_scan.py", title="Metadata Scan", icon=":material/manage_search:"),
    st.Page("pages/3_data_catalog.py", title="Data Catalog", icon=":material/library_books:"),
    st.Page("pages/4_data_quality.py", title="Data Quality", icon=":material/verified:"),
    st.Page("pages/5_reports.py", title="Reports", icon=":material/description:"),
]

navigation = st.navigation(pages, position="top")
navigation.run()
