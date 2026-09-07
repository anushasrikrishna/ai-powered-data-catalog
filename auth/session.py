from __future__ import annotations

import streamlit as st
from streamlit.errors import StreamlitAPIException

from auth.models import AuthenticatedUser
from core.connection_registry import get_connection_registry


AUTHENTICATED_KEY = "authenticated"
CURRENT_USER_KEY = "current_user"
AUTH_OVERVIEW_PAGE_KEY = "auth_overview_page"
AUTH_LOGIN_PAGE_KEY = "auth_login_page"
PAGE_STATE_PREFIXES = ("connections_", "metadata_", "catalog_", "quality_", "reports_", "ai_")


def initialize_auth_state() -> None:
    if AUTHENTICATED_KEY not in st.session_state:
        st.session_state[AUTHENTICATED_KEY] = False
    if not st.session_state.get(AUTHENTICATED_KEY):
        st.session_state.pop(CURRENT_USER_KEY, None)


def is_authenticated() -> bool:
    initialize_auth_state()
    return bool(st.session_state.get(AUTHENTICATED_KEY)) and isinstance(st.session_state.get(CURRENT_USER_KEY), AuthenticatedUser)


def sign_in(user: AuthenticatedUser) -> None:
    st.session_state[AUTHENTICATED_KEY] = True
    st.session_state[CURRENT_USER_KEY] = user


def register_auth_pages(overview_page: object, login_page: object) -> None:
    st.session_state[AUTH_OVERVIEW_PAGE_KEY] = overview_page
    st.session_state[AUTH_LOGIN_PAGE_KEY] = login_page


def redirect_to_overview() -> None:
    page = st.session_state.get(AUTH_OVERVIEW_PAGE_KEY)
    if page is not None:
        st.switch_page(page)
    st.rerun()


def redirect_to_login() -> None:
    page = st.session_state.get(AUTH_LOGIN_PAGE_KEY)
    if page is not None:
        st.switch_page(page)
    st.rerun()


def current_user() -> AuthenticatedUser | None:
    return st.session_state.get(CURRENT_USER_KEY) if is_authenticated() else None


def current_user_id() -> str:
    user = current_user()
    if user is None:
        raise RuntimeError("An authenticated user is required")
    return user.user_id


def logout() -> None:
    registry = get_connection_registry()
    for entry in list(registry.entries()):
        registry.disconnect(entry.connection_id)
    for key in list(st.session_state.keys()):
        if key in {"dark_mode", AUTHENTICATED_KEY, CURRENT_USER_KEY}:
            continue
        lowered_key = str(key).casefold()
        page_state_key = lowered_key.lstrip("_")
        if page_state_key.startswith(PAGE_STATE_PREFIXES) or any(token in lowered_key for token in ("quality", "ai", "report", "connector", "connection", "scan", "catalog_selected", "pending_page", "auth_reset")):
            st.session_state.pop(key, None)
    st.session_state[AUTHENTICATED_KEY] = False
    st.session_state.pop(CURRENT_USER_KEY, None)


def require_authenticated() -> None:
    if not is_authenticated():
        try:
            st.switch_page("pages/0_login.py")
        except StreamlitAPIException:
            # A page executed directly resolves switch_page paths from pages/.
            try:
                st.switch_page("0_login.py")
            except StreamlitAPIException:
                # Standalone page smoke tests do not register the app pages;
                # fail closed without rendering any protected content.
                st.markdown("<h1>Sign in</h1><p>Please sign in to access this page.</p>", unsafe_allow_html=True)
        st.stop()


__all__ = ["AUTHENTICATED_KEY", "AUTH_LOGIN_PAGE_KEY", "AUTH_OVERVIEW_PAGE_KEY", "CURRENT_USER_KEY", "PAGE_STATE_PREFIXES", "current_user", "current_user_id", "initialize_auth_state", "is_authenticated", "logout", "redirect_to_login", "redirect_to_overview", "register_auth_pages", "require_authenticated", "sign_in"]
