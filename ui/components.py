import streamlit as st

from ui.icons import svg_icon


def render_app_header() -> None:
    """Render the persistent product header and the single theme control."""
    with st.container():
        left, right = st.columns([4, 1], vertical_alignment="center")
        with left:
            st.markdown(
                f'<div class="app-header"><div class="app-brand"><span class="brand-mark">{svg_icon("dashboard", 18)}</span>'
                '<div><div class="brand-name">AI-Powered Data Catalog</div><div class="brand-subtitle">Metadata &amp; Quality Assistant</div></div></div></div>',
                unsafe_allow_html=True,
            )
        with right:
            st.toggle("Dark mode", key="dark_mode", help="Switch between light and dark application themes.")


def render_page_header(title: str, subtitle: str, description: str, icon: str | None = None) -> None:
    icon_html = svg_icon(icon, 22) if icon else ""
    st.markdown(
        f'<div class="page-content"><div class="page-title-row">{icon_html}<h1>{title}</h1></div>'
        f'<div class="page-subtitle">{subtitle}</div><div class="hero-copy">{description}</div></div>',
        unsafe_allow_html=True,
    )


def render_metric_card(value: str, label: str, detail: str) -> None:
    st.markdown(
        f'<div class="metric-card"><div class="metric-value">{value}</div><div class="metric-label">{label}</div><div class="metric-detail">{detail}</div></div>',
        unsafe_allow_html=True,
    )


def render_workspace_status(cards: list[tuple[str, str, str, str]]) -> None:
    columns = st.columns(len(cards))
    for column, (icon, label, value, detail) in zip(columns, cards):
        with column:
            st.markdown(
                f'<div class="status-card"><div class="status-icon">{svg_icon(icon, 18)}</div>'
                f'<div class="status-label">{label}</div><div class="status-value">{value}</div>'
                f'<div class="status-detail">{detail}</div></div>',
                unsafe_allow_html=True,
            )


def render_feature_card(icon: str, title: str, description: str, badge: str | None = None) -> None:
    badge_html = f'<div class="badge">{badge}</div>' if badge else ""
    st.markdown(
        f'<div class="feature-card"><div class="card-icon">{svg_icon(icon, 24)}</div><div class="card-title">{title}</div><div class="card-description">{description}</div>{badge_html}</div>',
        unsafe_allow_html=True,
    )


def render_source_card(name: str, description: str) -> None:
    render_feature_card("database", name, description, "Not configured")


def render_empty_state(title: str, description: str, icon: str = "search") -> None:
    st.markdown(
        f'<div class="empty-state"><div class="empty-icon">{svg_icon(icon, 28)}</div><div class="empty-title">{title}</div><div class="empty-description">{description}</div></div>',
        unsafe_allow_html=True,
    )


def render_stepper(steps: list[str]) -> None:
    parts = ['<div class="stepper">']
    for index, label in enumerate(steps):
        parts.append(f'<div class="step"><span class="step-number">{index + 1}</span><span>{label}</span></div>')
        if index < len(steps) - 1:
            parts.append('<span class="step-connector"></span>')
    parts.append('</div>')
    st.markdown("".join(parts), unsafe_allow_html=True)


def render_get_started_workflow(steps: list[tuple[str, str]]) -> None:
    parts = ['<div class="get-started-workflow">']
    for index, (icon, title) in enumerate(steps):
        parts.append(
            f'<div class="workflow-item"><div class="workflow-number">{index + 1:02d}</div>'
            f'<div class="workflow-icon">{svg_icon(icon, 19)}</div><div class="workflow-title">{title}</div></div>'
        )
        if index < len(steps) - 1:
            parts.append('<div class="workflow-connector">→</div>')
    parts.append('</div>')
    st.markdown("".join(parts), unsafe_allow_html=True)


def render_quick_access_card(icon: str, title: str, description: str, callback, page_path: str) -> None:
    st.markdown(
        f'<div class="quick-card"><div class="quick-icon">{svg_icon(icon, 20)}</div>'
        f'<div class="quick-title">{title}</div><div class="quick-description">{description}</div></div>',
        unsafe_allow_html=True,
    )
    st.button("Open", icon=":material/arrow_forward:", on_click=callback, args=(page_path,), key=f"open_{title}")
