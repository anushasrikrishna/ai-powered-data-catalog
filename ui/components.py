import streamlit as st
from contextlib import contextmanager
from html import escape
from pathlib import Path
from typing import Any

from ui.icons import svg_icon

LOADER_SVG_PATH = Path(__file__).resolve().parent / "assets" / "loader.svg"
LOADER_SVG = LOADER_SVG_PATH.read_text(encoding="utf-8")


@contextmanager
def loading_indicator(message: str):
    placeholder = st.empty()
    with placeholder.container():
        st.markdown(
            f'<div role="status" aria-live="polite" style="align-items:center;color:var(--text);display:flex;gap:.5rem;line-height:1.5;">'
            f'<span style="color:var(--spinner-active);display:inline-flex;height:1.25rem;width:1.25rem;">{LOADER_SVG}</span>'
            f'<span>{escape(message)}</span></div>',
            unsafe_allow_html=True,
        )
    try:
        yield
    finally:
        placeholder.empty()


def render_app_header() -> None:
    """Render the persistent product header and the single theme control."""
    dark_mode = st.session_state.get("dark_mode", False)
    next_icon = ":material/light_mode:" if dark_mode else ":material/dark_mode:"

    def toggle_theme() -> None:
        st.session_state["dark_mode"] = not st.session_state.get("dark_mode", False)

    with st.container():
        left, right = st.columns([4, 0.35], vertical_alignment="center")
        with left:
            st.markdown(
                f'<div class="app-header"><div class="app-brand"><span class="brand-mark">{svg_icon("dashboard", 18)}</span>'
                '<div><div class="brand-name">AI-Powered Data Catalog</div><div class="brand-subtitle">Metadata &amp; Quality Assistant</div></div></div></div>',
                unsafe_allow_html=True,
            )
        with right:
            st.button(
                "",
                icon=next_icon,
                key="theme_mode_button",
                on_click=toggle_theme,
                type="tertiary",
            )


def render_app_navigation(nav_items: list[tuple[object, str, str]]) -> None:
    st.markdown('<div class="app-nav-spacer"></div>', unsafe_allow_html=True)
    columns = st.columns(len(nav_items), gap="small", vertical_alignment="center")
    for column, (page, label, icon) in zip(columns, nav_items):
        with column:
            st.page_link(
                page,
                label=label,
                icon=icon,
                use_container_width=True,
            )
    st.markdown('<div class="app-nav-divider"></div>', unsafe_allow_html=True)


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


def render_html_table(data: Any) -> None:
    """Render tabular data without Streamlit's Arrow serialization path."""
    if hasattr(data, "to_dict") and hasattr(data, "columns"):
        rows = data.to_dict(orient="records")
        column_keys = list(data.columns)
        headers = [str(column) for column in column_keys]
    else:
        rows = list(data or [])
        column_keys = list(rows[0].keys()) if rows else []
        headers = [str(header) for header in column_keys]

    if not rows or not headers:
        st.markdown('<div class="html-table-empty">No data available.</div>', unsafe_allow_html=True)
        return

    def format_value(value: Any) -> str:
        return "—" if value is None else escape(str(value))

    def datatype_kind(value: Any) -> str:
        normalized = str(value or "").casefold()
        if any(token in normalized for token in ("bool",)):
            return "boolean"
        if any(token in normalized for token in ("date", "time", "year")):
            return "date"
        if any(token in normalized for token in ("char", "text", "string", "clob", "varchar")):
            return "text"
        if any(token in normalized for token in ("int", "number", "numeric", "decimal", "float", "double", "real")):
            return "number"
        return "other"

    def badge(value: Any, kind: str) -> str:
        return f'<span class="html-table-badge html-table-badge--{kind}">{format_value(value)}</span>'

    def source_cell(value: Any) -> str:
        source_kind = str(value or "").casefold().replace(" ", "-")
        icon = {"snowflake": "❄", "sql-server": "▦", "postgresql": "▦"}.get(source_kind, "•")
        return (
            f'<span class="html-table-source html-table-source--{escape(source_kind)}">'
            f'<span class="html-table-source-icon" aria-hidden="true">{icon}</span>'
            f"{format_value(value)}</span>"
        )

    def column_cell(value: Any, row: dict[Any, Any]) -> str:
        kind = datatype_kind(
            row.get("Normalized Type", row.get("Source Type", row.get("data_type", row.get("data type"))))
        )
        icon = {"number": "#", "text": "A", "date": "◷", "boolean": "✓", "other": "•"}[kind]
        return (
            f'<span class="html-table-column-name"><span class="html-table-column-icon html-table-column-icon--{kind}" '
            f'aria-hidden="true">{icon}</span>{format_value(value)}</span>'
        )

    def formatted_cell(header: str, value: Any, row: dict[Any, Any]) -> str:
        normalized = header.casefold()
        if normalized in {"source type", "normalized type", "data_type", "data type"}:
            return badge(value, f"datatype-{datatype_kind(value)}")
        if normalized == "nullable":
            is_nullable = value is True or str(value).casefold() in {"yes", "true"}
            return badge(value, "nullable-yes" if is_nullable else "nullable-no")
        if normalized == "type":
            return badge(value, "table-type")
        if normalized == "source":
            return source_cell(value)
        if normalized in {"column", "name"}:
            return column_cell(value, row)
        return format_value(value)

    def cell_class(header: str) -> str:
        normalized = header.casefold()
        if normalized in {"position", "ordinal_position", "ordinal position", "null count", "distinct count", "rows", "columns"}:
            return "html-table-cell--numeric"
        if normalized in {"column", "name", "database", "schema", "table", "source", "type", "source type", "normalized type", "data_type", "data type"}:
            return "html-table-cell--identifier"
        if normalized in {"minimum", "maximum", "sample values"}:
            return "html-table-cell--wide"
        return ""

    table_kind = "catalog" if headers == ["Source", "Database", "Schema", "Table", "Type", "Rows", "Columns"] else "metadata"
    header_html = "".join(
        f"<th class='html-table-cell {cell_class(header)}' scope='col'>{escape(header)}</th>"
        for header in headers
    )
    body_html = "".join(
        "<tr>"
        + "".join(
            f"<td class='html-table-cell {cell_class(header)}'>{formatted_cell(header, row.get(key), row)}</td>"
            for key, header in zip(column_keys, headers)
        )
        + "</tr>"
        for row in rows
    )
    st.markdown(
        f'<div class="html-table-wrapper"><div class="html-table-scroll"><table class="html-table html-table--{table_kind}"><thead><tr>{header_html}</tr></thead>'
        f"<tbody>{body_html}</tbody></table></div></div>",
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


def render_get_started_workflow(steps: list[tuple[str, str]], class_name: str = "get-started-workflow") -> None:
    parts = [f'<div class="{class_name}">']
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
