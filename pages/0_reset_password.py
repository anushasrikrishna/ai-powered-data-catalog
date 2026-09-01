from __future__ import annotations

import streamlit as st

from auth.service import AuthenticationService
from auth.session import is_authenticated, redirect_to_overview
from ui.auth_components import auth_password_hint, render_auth_shell


if is_authenticated():
    redirect_to_overview()

with render_auth_shell("reset-password", "Reset Password", "Choose a new password for your account."):
    token = st.session_state.get("auth_reset_token")
    if not token:
        st.error("This password reset request is no longer valid.")
        st.page_link("pages/0_forgot_password.py", label="Start Again")
        st.page_link("pages/0_login.py", label="Back to Sign In")
    else:
        if notice := st.session_state.pop("auth_reset_notice", None):
            st.info(notice)
        with st.form("reset_password_form"):
            password = st.text_input("New Password", type="password", key="reset_password")
            auth_password_hint()
            confirm_password = st.text_input("Confirm New Password", type="password", key="reset_confirm_password")
            submitted = st.form_submit_button("Reset Password", type="primary", use_container_width=True)
        if submitted:
            if not password or not confirm_password:
                st.error("Complete both password fields.")
            else:
                try:
                    reset = AuthenticationService().reset_password(token, password, confirm_password)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.session_state.pop("auth_reset_token", None)
                    st.session_state.pop("reset_password", None)
                    st.session_state.pop("reset_confirm_password", None)
                    if not reset:
                        st.error("This password reset request is no longer valid.")
                    else:
                        st.session_state["auth_password_reset_notice"] = "Password updated successfully. Please sign in."
                        st.switch_page("pages/0_login.py")
        st.page_link("pages/0_login.py", label="Back to Sign In")
