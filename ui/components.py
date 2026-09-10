import streamlit as st
from contextlib import contextmanager
import csv
from html import escape
import io
from pathlib import Path
import re
from typing import Any, Callable

from ui.icons import svg_icon
from ui.illustrations import product_mark
from auth.session import current_user, logout

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
    """Render the persistent product header, theme control, and user menu."""
    dark_mode = st.session_state.get("dark_mode", False)
    next_icon = ":material/light_mode:" if dark_mode else ":material/dark_mode:"

    def toggle_theme() -> None:
        st.session_state["dark_mode"] = not st.session_state.get("dark_mode", False)

    with st.container(key="authenticated-header-row"):
        left, actions = st.columns([3, 1], vertical_alignment="center")
        with left:
            st.markdown(
                f'<div class="app-header"><div class="app-brand"><span class="brand-mark">{product_mark(19)}</span>'
                '<div><div class="brand-name">AI-Powered Data Catalog</div><div class="brand-subtitle">Metadata &amp; Quality Assistant</div></div></div></div>',
                unsafe_allow_html=True,
            )
        with actions:
            user = current_user()
            username = user.username if user is not None else "Account"
            display_name = username if len(username) <= 22 else f"{username[:19]}…"
            with st.container(key="header-actions"):
                account, theme = st.columns([1.35, 0.35], gap="small", vertical_alignment="center")
                with account:
                    with st.container(key="authenticated-account-control"):
                        name_column, arrow_column = st.columns([4, 1], gap="small", vertical_alignment="center")
                        with name_column:
                            st.markdown(f'<div class="authenticated-username" title="{escape(username)}">{escape(display_name)}</div>', unsafe_allow_html=True)
                        with arrow_column:
                            with st.popover("", use_container_width=True):
                                st.caption(username)
                                if st.button("Logout", icon=":material/logout:", key="authenticated_logout"):
                                    logout()
                                    st.rerun()
                with theme:
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


def render_metric_card(value: str, label: str, detail: str, decoration: str | None = None) -> None:
    decoration_class = f" card-decoration-{decoration}" if decoration else ""
    st.markdown(
        f'<div class="metric-card{decoration_class}"><div class="card-content"><div class="metric-value">{value}</div><div class="metric-label">{label}</div><div class="metric-detail">{detail}</div></div></div>',
        unsafe_allow_html=True,
    )


def render_workspace_status(
    cards: list[tuple[str, str, str, str]],
    compact: bool = False,
    show_detail: bool = True,
    decorations: list[str | None] | None = None,
) -> None:
    columns = st.columns(len(cards))
    card_classes = ["status-card"]
    if compact:
        card_classes.append("status-card--compact")
    if not show_detail:
        card_classes.append("status-card--no-detail")
    card_class = " ".join(card_classes)
    for index, (column, (icon, label, value, detail)) in enumerate(zip(columns, cards)):
        with column:
            decoration = decorations[index] if decorations and index < len(decorations) else None
            decoration_class = f" card-decoration-{decoration}" if decoration else ""
            detail_html = f'<div class="status-detail">{detail}</div>'
            st.markdown(
                f'<div class="{card_class}{decoration_class}"><div class="card-content"><div class="status-heading"><div class="status-icon">{svg_icon(icon, 18)}</div>'
                f'<div class="status-label">{label}</div></div><div class="status-value">{value}</div>'
                f'{detail_html if show_detail else ""}</div></div>',
                unsafe_allow_html=True,
            )


def render_feature_card(icon: str, title: str, description: str, badge: str | None = None, decoration: str | None = None) -> None:
    badge_html = f'<div class="badge">{badge}</div>' if badge else ""
    decoration_class = f" card-decoration-{decoration}" if decoration else ""
    st.markdown(
        f'<div class="feature-card{decoration_class}"><div class="card-content"><div class="card-icon">{svg_icon(icon, 24)}</div><div class="card-title">{title}</div><div class="card-description">{description}</div>{badge_html}</div></div>',
        unsafe_allow_html=True,
    )


def render_source_card(name: str, description: str) -> None:
    render_feature_card("database", name, description, "Not configured")


def render_empty_state(title: str, description: str, icon: str = "search", decoration: str | None = None) -> None:
    decoration_class = f" card-decoration-{decoration}" if decoration else ""
    st.markdown(
        f'<div class="empty-state{decoration_class}"><div class="card-content"><div class="empty-icon">{svg_icon(icon, 28)}</div><div class="empty-title">{title}</div><div class="empty-description">{description}</div></div></div>',
        unsafe_allow_html=True,
    )


def sanitize_table_id(table_id: str) -> str:
    """Return a stable DOM/session key safe for a rendered table."""
    sanitized = re.sub(r"[^a-zA-Z0-9_-]+", "-", str(table_id)).strip("-")
    return sanitized or "table"


def resolve_table_action_value(value: Any, row: dict[Any, Any], row_index: int) -> Any:
    """Resolve static or row-aware table action metadata for one rendered row."""
    return value(row, row_index) if callable(value) else value


def table_to_csv(data: Any) -> str:
    """Serialize table input to UTF-8-compatible CSV without HTML markup."""
    headers, rows = _table_records(data)
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                header: "" if row.get(key) is None else str(row.get(key))
                for key, header in zip(row.keys(), headers)
            }
        )
    return output.getvalue()


def _table_records(data: Any) -> tuple[list[str], list[dict[Any, Any]]]:
    if hasattr(data, "to_dict") and hasattr(data, "columns"):
        rows = data.to_dict(orient="records")
        column_keys = list(data.columns)
    else:
        rows = list(data or [])
        column_keys = list(rows[0].keys()) if rows else []
    return [str(column) for column in column_keys], rows


def render_html_table(
    data: Any,
    *,
    table_id: str = "table",
    download_filename: str = "table.csv",
    download: bool = True,
    column_widths: list[float] | None = None,
    cell_renderers: dict[str, Callable[[Any, dict[Any, Any]], str]] | None = None,
    action: dict[str, Any] | None = None,
    table_class: str | None = None,
    max_visible_rows: int | None = None,
    sticky_header: bool = False,
    scrollable: bool = False,
    compact: bool = False,
    max_width: str | None = None,
    fill_available_width: bool = False,
) -> None:
    """Render tabular data without Streamlit's Arrow serialization path."""
    headers, rows = _table_records(data)
    column_keys = list(rows[0].keys()) if rows else []

    if not rows or not headers:
        st.markdown('<div class="html-table-empty">No data available.</div>', unsafe_allow_html=True)
        return

    safe_table_id = sanitize_table_id(table_id)
    table_shell = None
    if action is None:
        table_shell = st.container(key=f"table-shell-{safe_table_id}")
        if download:
            download_column = table_shell.columns([1, 0.05], vertical_alignment="center")[1]
            download_column.download_button(
                "",
                data=table_to_csv(data),
                file_name=download_filename,
                mime="text/csv",
                icon=":material/download:",
                key=f"{safe_table_id}_download_button",
                help="Download CSV",
                type="tertiary",
            )
    visible_columns = column_keys
    visible_headers = headers
    if column_widths is not None and len(column_widths) != len(visible_headers):
        raise ValueError("column_widths must match the table column count")

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

    def category_kind(value: Any) -> str:
        return {
            "identifier": "identifier",
            "contact information": "contact",
            "date/time": "date-time",
            "financial/measure": "financial",
            "quantity/measure": "quantity",
            "boolean/flag": "boolean",
            "name": "name",
            "location": "location",
            "text/description": "text",
            "other": "other",
        }.get(str(value or "").casefold(), "other")

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
        if cell_renderers and header in cell_renderers:
            return cell_renderers[header](value, row)
        normalized = header.casefold()
        if normalized in {"source type", "normalized type", "data_type", "data type"}:
            return badge(value, f"datatype-{datatype_kind(value)}")
        if normalized == "nullable":
            is_nullable = value is True or str(value).casefold() in {"yes", "true"}
            return badge(value, "nullable-yes" if is_nullable else "nullable-no")
        if normalized == "type":
            return badge(value, "table-type")
        if normalized == "possible category":
            return badge(value, f"category-{category_kind(value)}")
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

    if action:
        action_header = str(action["header"])
        interactive_columns = list(column_widths or [1.0] * len(visible_headers))
        if len(interactive_columns) != len(visible_headers):
            raise ValueError("column_widths must match the table column count")
        with st.container(key=f"html-table-interactive-{safe_table_id}"):
            header_columns = st.columns(interactive_columns, gap="small", vertical_alignment="center")
            for column, header in zip(header_columns, visible_headers):
                with column:
                    st.markdown(f'<div class="html-table-interactive-header">{escape(header)}</div>', unsafe_allow_html=True)
            for index, row in enumerate(rows):
                with st.container(key=f"html-table-interactive-row-{safe_table_id}-{index}"):
                    row_columns = st.columns(interactive_columns, gap="small", vertical_alignment="center")
                    for column, key, header in zip(row_columns, visible_columns, visible_headers):
                        with column:
                            if header == action_header:
                                continue
                            content = formatted_cell(header, row.get(key), row)
                            special_class = " html-table-interactive-cell--special" if header in {"Rule", "Status"} else ""
                            st.markdown(f'<div class="html-table-interactive-cell{special_class}">{content}</div>', unsafe_allow_html=True)
                    with row_columns[-1]:
                        actions = action.get("actions") or [action]
                        actions = [
                            action_item
                            for action_item in actions
                            if action_item.get("visible_if", lambda _row: True)(row)
                        ]
                        action_columns = st.columns(len(actions), gap="small") if len(actions) > 1 else [row_columns[-1]]
                        for action_column, action_item in zip(action_columns, actions):
                            with action_column:
                                action_button_kwargs = {
                                    "key": f'{action_item["key_prefix"]}-{index}',
                                    "help": str(action_item["help"]),
                                    "type": "tertiary",
                                }
                                if action_item.get("icon"):
                                    action_button_kwargs["icon"] = str(action_item["icon"])
                                action_button_label = str(
                                    resolve_table_action_value(action_item.get("label", ""), row, index)
                                )
                                disabled = resolve_table_action_value(action_item.get("disabled", False), row, index)
                                if disabled:
                                    action_button_kwargs["disabled"] = True
                                with st.container(key=f'html-table-action-{safe_table_id}-{index}-{action_item["key_prefix"]}'):
                                    clicked = st.button(action_button_label, **action_button_kwargs)
                                if clicked:
                                    action_item["callback"](index)
        return

    table_kind = "catalog" if headers == ["Source", "Database", "Schema", "Table", "Type", "Rows", "Columns"] else "metadata"
    table_width_class = f" {sanitize_table_id(table_class)}" if table_class else ""
    if fill_available_width:
        table_width_class += " html-table--fill-available"
    table_behavior_classes = []
    if compact:
        table_behavior_classes.append("html-table-wrapper--compact")
    if sticky_header:
        table_behavior_classes.append("html-table-wrapper--sticky-header")
    should_scroll = bool(scrollable and max_visible_rows and len(rows) > max_visible_rows)
    if should_scroll:
        table_behavior_classes.append("html-table-wrapper--scrollable")
    wrapper_class = " " + " ".join(table_behavior_classes) if table_behavior_classes else ""
    wrapper_style = f' style="max-width:{escape(str(max_width))};"' if max_width else ""
    scroll_style = ""
    if should_scroll:
        header_height = 46
        row_height = 43 if compact else 46
        visible_rows = min(len(rows), max_visible_rows or 5)
        scroll_style = f' style="max-height:{header_height + visible_rows * row_height}px;"'
    def width_attribute(index: int) -> str:
        return f' style="width:{column_widths[index]}%"' if column_widths is not None else ""

    header_html = "".join(
        f"<th class='html-table-cell {cell_class(header)}' scope='col'{width_attribute(index)}>{escape(header)}</th>"
        for index, header in enumerate(visible_headers)
    )
    body_html = "".join(
        "<tr>"
        + "".join(
            f"<td class='html-table-cell {cell_class(header)}{' html-table-cell--special' if cell_renderers and header in cell_renderers else ''}'{width_attribute(index)}>{formatted_cell(header, row.get(key), row)}</td>"
            for index, (key, header) in enumerate(zip(visible_columns, visible_headers))
        )
        + "</tr>"
        for row in rows
    )
    if not rows:
        assert table_shell is not None
        table_shell.markdown(
            f'<div id="html-table-{safe_table_id}" data-table-id="{safe_table_id}" class="html-table-wrapper"><div class="html-table-empty">No matching rows.</div></div>',
            unsafe_allow_html=True,
        )
        return
    assert table_shell is not None
    table_shell.markdown(
        f'<div id="html-table-{safe_table_id}" data-table-id="{safe_table_id}" class="html-table-wrapper{wrapper_class}"{wrapper_style}><div class="html-table-scroll"{scroll_style}><table class="html-table html-table--{table_kind}{table_width_class}"><thead><tr>{header_html}</tr></thead>'
        f"<tbody>{body_html}</tbody></table></div></div>",
        unsafe_allow_html=True,
    )


def render_count_chips(
    title: str,
    items: list[tuple[str, int]],
    description: str | None = None,
    kind: str = "default",
    footer: str | None = None,
    decoration: str | None = None,
) -> None:
    """Render compact labeled counts for deterministic documentation summaries."""
    if not items:
        return
    description_html = f'<div class="documentation-count-description">{escape(description)}</div>' if description else ""
    footer_html = f'<div class="documentation-count-footer">{escape(footer)}</div>' if footer else ""
    decoration_class = f" card-decoration-{decoration}" if decoration else ""
    chips = "".join(
        f'<span class="documentation-count-item documentation-count-item--{escape(kind)}">'
        f'<span class="documentation-count-label">{escape(label)}</span>'
        f'<span class="documentation-count-value">{count:,}</span></span>'
        for label, count in items
    )
    st.markdown(
        f'<div class="documentation-count-breakdown documentation-count-breakdown--{escape(kind)}{decoration_class}">'
        f'<div class="documentation-count-title">{escape(title)}</div>{description_html}{chips}{footer_html}</div>',
        unsafe_allow_html=True,
    )


def render_stepper(steps: list[str]) -> None:
    render_process_stepper([("catalog", label) for label in steps])


def render_process_stepper(steps: list[tuple[str, str]], class_name: str = "process-stepper") -> None:
    """Render the shared non-interactive process journey used across pages."""
    parts = [f'<div class="{escape(class_name)}">']
    for index, (icon, label) in enumerate(steps):
        parts.append(
            f'<div class="process-step"><div class="process-step-number">{index + 1:02d}</div>'
            f'<div class="process-step-node">{svg_icon(icon, 18)}</div>'
            f'<div class="process-step-label">{escape(label)}</div></div>'
        )
        if index < len(steps) - 1:
            parts.append('<div class="process-step-connector" aria-hidden="true"><span></span></div>')
    parts.append('</div>')
    st.markdown("".join(parts), unsafe_allow_html=True)


def render_get_started_workflow(steps: list[tuple[str, str]], class_name: str = "get-started-workflow") -> None:
    render_process_stepper(steps, class_name=f"{class_name} process-stepper")


def render_quick_access_card(icon: str, title: str, description: str, callback, page_path: str, decoration: str | None = None) -> None:
    decoration_class = f" card-decoration-{decoration}" if decoration else ""
    with st.container(key=f"quick-card-{sanitize_table_id(title)}"):
        st.markdown(
            f'<div class="quick-card{decoration_class}"><div class="card-content"><div class="quick-card-content"><div class="quick-icon">{svg_icon(icon, 20)}</div>'
            f'<div><div class="quick-title">{title}</div><div class="quick-description">{description}</div></div></div></div></div>',
            unsafe_allow_html=True,
        )
        st.page_link(page_path, label="Open", icon=":material/arrow_forward:")
