import streamlit as st

from auth.session import current_user_id, initialize_auth_state, is_authenticated, register_auth_pages
from core.connection_registry import get_connection_registry
from storage.repository import MetadataRepository
from storage.quality_repository import QualityRunRepository
from storage.user_repository import UserRepository
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
initialize_auth_state()
UserRepository().initialize()


def request_page(page_path: str) -> None:
    """Record navigation from a button callback; switch pages outside callbacks."""
    st.session_state["pending_page"] = page_path


def _pluralize(count: int, singular: str, plural: str) -> str:
    return singular if count == 1 else plural


def _load_workspace_snapshot(user_id: str | None = None) -> tuple[int, int]:
    try:
        tables = MetadataRepository().list_tables(user_id)
    except Exception:
        return 0, 0

    connected_sources = len({entry.source_type for entry in get_connection_registry().entries() if entry.connected})
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
    connected_sources, cataloged_datasets = _load_workspace_snapshot(current_user_id())
    latest_run = QualityRunRepository().get_latest_run_for_user(current_user_id())
    latest_score = "--" if latest_run is None or latest_run.report.quality_score is None else f"{latest_run.report.quality_score:g}%"

    st.markdown(
        '<section class="hero-panel"><div class="hero-layout"><div class="hero-copy-block">'
        '<div class="hero-eyebrow">DATA INTELLIGENCE WORKSPACE</div>'
        '<div class="hero-title">Connect. Catalog. Validate. Trust.</div>'
        '<div class="hero-description">Connect enterprise sources, discover metadata and continuously '
        'validate data quality from one workspace.</div></div>'
        '<div class="hero-visual" aria-hidden="true"><div class="hero-visual-line hero-visual-line--one"></div>'
        '<div class="hero-visual-line hero-visual-line--two"></div><div class="hero-visual-node hero-visual-node--one">▦</div>'
        '<div class="hero-visual-node hero-visual-node--two">≡</div><div class="hero-visual-node hero-visual-node--three">✓</div>'
        '</div></div></section>',
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
            ("quality", "Quality Score", latest_score, "Overall data quality"),
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
login_page = st.Page("pages/0_login.py", title="Login", icon=":material/login:")
create_account_page = st.Page("pages/0_create_account.py", title="Create Account", icon=":material/person_add:")
forgot_password_page = st.Page("pages/0_forgot_password.py", title="Forgot Password", icon=":material/help:")
reset_password_page = st.Page("pages/0_reset_password.py", title="Reset Password", icon=":material/lock_reset:")
register_auth_pages(overview_page, login_page)
navigation = st.navigation(pages if is_authenticated() else [login_page, create_account_page, forgot_password_page, reset_password_page], position="hidden")

# The authenticated application shell owns the product header, navigation, and sidebar.
apply_theme()
if is_authenticated():
    render_app_header()
    render_app_navigation(
        [
            (overview_page, "Overview", ":material/dashboard:"),
            (connections_page, "Connections", ":material/database:"),
            (metadata_scan_page, "Metadata Scan", ":material/manage_search:"),
            (data_catalog_page, "Data Catalog", ":material/library_books:"),
            (data_quality_page, "Data Quality", ":material/verified:"),
            (reports_page, "Reports", ":material/description:"),
        ]
    )
    render_sidebar()
navigation.run()
