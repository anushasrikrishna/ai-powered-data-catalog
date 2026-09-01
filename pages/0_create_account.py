from __future__ import annotations

import streamlit as st

from auth.service import AuthenticationService
from auth.session import is_authenticated, redirect_to_login
from ui.auth_components import auth_password_hint, render_auth_shell


if is_authenticated():
    redirect_to_login()

with render_auth_shell("create-account", "Create Account", "Create your account to start building your trusted data workspace."):
    with st.form("create_account_form"):
        username = st.text_input("Username", key="username")
        email = st.text_input("Email", key="email")
        password = st.text_input("Password", type="password", key="password")
        auth_password_hint()
        confirm_password = st.text_input("Confirm Password", type="password", key="confirm_password")
        submitted = st.form_submit_button("Create Account", type="primary", use_container_width=True)
    if submitted:
        if not all((username.strip(), email.strip(), password, confirm_password)):
            st.error("Complete all fields to create your account.")
        else:
            try:
                AuthenticationService().register(username, email, password, confirm_password)
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.session_state["auth_account_created_notice"] = "Account created successfully. Please sign in."
                for key in ("username", "email", "password", "confirm_password"):
                    st.session_state.pop(key, None)
                redirect_to_login()
    if st.button("Back to Sign In", key="auth_back_to_login"):
        redirect_to_login()
