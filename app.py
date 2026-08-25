import streamlit as st

from storage.repository import MetadataRepository
from ui.components import (
    render_app_header,
    render_app_navigation,
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


def _pluralize(count: int, singular: str, plural: str) -> str:
    return singular if count == 1 else plural


def _load_workspace_snapshot() -> tuple[int, int]:
    try:
        tables = MetadataRepository().list_tables()
    except Exception:
        return 0, 0

    connected_sources = len({table.source_type.strip().lower() for table in tables if table.source_type.strip()})
    cataloged_datasets = len(tables)
    return connected_sources, cataloged_datasets


def _connected_sources_detail(source_count: int) -> str:
    if source_count == 0:
        return "No sources cataloged"
    noun = _pluralize(source_count, "source", "sources")
    return f"{source_count:,} {noun} represented in catalog"


def _cataloged_datasets_detail(dataset_count: int) -> str:
    if dataset_count == 0:
        return "No datasets indexed"
    noun = _pluralize(dataset_count, "dataset", "datasets")
    return f"{dataset_count:,} cataloged {noun}"


pending_page = st.session_state.pop("pending_page", None)
if pending_page:
    st.switch_page(pending_page)

def home_page() -> None:
    connected_sources, cataloged_datasets = _load_workspace_snapshot()

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
            "Connect & Scan Data",
            icon=":material/database:",
            type="primary",
            use_container_width=True,
            on_click=request_page,
            args=("pages/2_metadata_scan.py",),
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
            (
                "database",
                "Connected Sources",
                f"{connected_sources:,}",
                "Available data sources",
            ),
            (
                "catalog",
                "Cataloged Datasets",
                f"{cataloged_datasets:,}",
                "Discoverable datasets",
            ),
            ("quality", "Quality Score", "--", "Overall data quality"),
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
        ("search", "Metadata Scan", "Connect and scan source metadata.", "pages/2_metadata_scan.py"),
        ("catalog", "Data Catalog", "Discover available datasets.", "pages/3_data_catalog.py"),
        ("quality", "Data Quality", "Review quality checks and scores.", "pages/4_data_quality.py"),
    ]
    quick_columns = st.columns(3)
    for column, (icon, title, description, page_path) in zip(quick_columns, quick_access):
        with column:
            render_quick_access_card(icon, title, description, request_page, page_path)


overview_page = st.Page(home_page, title="Overview", icon=":material/dashboard:", default=True)
connections_page = st.Page("pages/1_connections.py", title="Connections", icon=":material/database:")
metadata_scan_page = st.Page("pages/2_metadata_scan.py", title="Metadata Scan", icon=":material/manage_search:")
data_catalog_page = st.Page("pages/3_data_catalog.py", title="Data Catalog", icon=":material/library_books:")
data_quality_page = st.Page("pages/4_data_quality.py", title="Data Quality", icon=":material/verified:")
reports_page = st.Page("pages/5_reports.py", title="Reports", icon=":material/description:")

pages = [
    overview_page,
    connections_page,
    metadata_scan_page,
    data_catalog_page,
    data_quality_page,
    reports_page,
]

navigation = st.navigation(pages, position="hidden")

# The application shell owns global styling, the product header, navigation, and sidebar.
apply_theme()
render_app_header()
render_app_navigation(
    [
        (overview_page, "Overview", ":material/dashboard:"),
        (metadata_scan_page, "Metadata Scan", ":material/manage_search:"),
        (data_catalog_page, "Data Catalog", ":material/library_books:"),
        (data_quality_page, "Data Quality", ":material/verified:"),
        (reports_page, "Reports", ":material/description:"),
    ]
)
render_sidebar()
navigation.run()
