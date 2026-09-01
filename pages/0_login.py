from __future__ import annotations

import streamlit as st

from auth.service import AuthenticationService
from auth.session import is_authenticated, redirect_to_overview, sign_in
from ui.auth_components import render_auth_shell


if is_authenticated():
    redirect_to_overview()

with render_auth_shell("login", "Welcome Back", "Sign in to continue to your data workspace."):
    if notice := st.session_state.pop("auth_account_created_notice", None):
        st.success(notice)
    if notice := st.session_state.pop("auth_password_reset_notice", None):
        st.success(notice)
    with st.container(key="login-form-shell"):
        with st.form("login_form"):
            identifier = st.text_input("Username or Email", key="login_identifier")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Sign In", type="primary", use_container_width=True)
        with st.container(
            key="login-secondary-actions",
            horizontal=True,
            horizontal_alignment="distribute",
            vertical_alignment="center",
        ):
            st.page_link("pages/0_forgot_password.py", label="Forgot Password?")
            st.page_link("pages/0_create_account.py", label="Create Account")
    if submitted:
        if not identifier.strip() or not password:
            st.error("Enter your username/email and password.")
            user = None
        else:
            user = AuthenticationService().authenticate(identifier, password)
        if user is None:
            st.error("Invalid username/email or password.")
        else:
            sign_in(user)
            st.session_state.pop("login_password", None)
            st.session_state.pop("login_identifier", None)
            redirect_to_overview()
