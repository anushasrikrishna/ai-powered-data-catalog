from __future__ import annotations

from contextlib import contextmanager
from html import escape
from typing import Iterator

import streamlit as st

from ui.illustrations import product_mark


def _toggle_theme() -> None:
    st.session_state["dark_mode"] = not st.session_state.get("dark_mode", False)


@contextmanager
def render_auth_shell(page_key: str, title: str, subtitle: str) -> Iterator[object]:
    """Render the shared unauthenticated shell and yield the form column."""
    dark_mode = st.session_state.get("dark_mode", False)
    icon = ":material/light_mode:" if dark_mode else ":material/dark_mode:"
    with st.container(key="auth-page-shell"):
        brand, form_column = st.columns([1.08, 0.92], gap="large")
        with brand:
            st.markdown(
                '<div class="auth-brand-panel">'
                f'<div class="auth-brand-mark">{product_mark(42)}</div>'
                '<div class="auth-data-visual" aria-hidden="true"><i></i><i></i><i></i><i></i><b></b><b></b></div>'
                '<div class="auth-brand-eyebrow">ENTERPRISE DATA INTELLIGENCE</div>'
                '<div class="auth-brand-heading">Connect. Catalog. Validate. Trust.</div>'
                '<div class="auth-brand-copy">Discover your data, understand its context and validate its quality from one workspace.</div>'
                '<div class="auth-brand-note">AI-Powered Data Catalog · Metadata &amp; Quality Assistant</div>'
                '</div>',
                unsafe_allow_html=True,
            )
        with form_column:
            with st.container(key=f"auth-card-{page_key}"):
                with st.container(key=f"auth-card-topbar-{page_key}"):
                    st.markdown(
                        f'<div class="auth-card-eyebrow-row"><span class="auth-card-mark">{product_mark(18)}</span>'
                        '<span class="auth-card-eyebrow">AI-POWERED DATA CATALOG</span></div>',
                        unsafe_allow_html=True,
                    )
                    with st.container(key=f"auth-theme-control-{page_key}"):
                        st.button(
                            "",
                            icon=icon,
                            key=f"auth-theme-toggle-{page_key}",
                            on_click=_toggle_theme,
                            type="tertiary",
                        )
                st.markdown(
                    f'<h1 class="auth-title">{escape(title)}</h1>'
                    f'<p class="auth-copy">{escape(subtitle)}</p>',
                    unsafe_allow_html=True,
                )
                yield form_column


def auth_password_hint() -> None:
    st.caption("Use at least 8 characters with uppercase, lowercase, and a number.")


def render_auth_header(title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="auth-shell"><div class="auth-eyebrow">AI-POWERED DATA CATALOG</div>'
        f'<h1>{title}</h1><p class="auth-copy">{subtitle}</p></div>',
        unsafe_allow_html=True,
    )
