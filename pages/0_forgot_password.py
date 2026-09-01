from __future__ import annotations

import streamlit as st

from auth.service import AuthenticationService
from auth.session import is_authenticated, redirect_to_overview
from ui.auth_components import render_auth_shell


if is_authenticated():
    redirect_to_overview()

with render_auth_shell("forgot-password", "Forgot Password", "Reset your password and return to your workspace."):
    with st.form("forgot_password_form"):
        email = st.text_input("Email", key="forgot_password_email")
        submitted = st.form_submit_button("Continue", type="primary", use_container_width=True)
    if submitted:
        if not email.strip():
            st.error("Enter your email address.")
        else:
            token = AuthenticationService().begin_password_reset(email)
            if token:
                st.session_state["auth_reset_token"] = token
                st.session_state.pop("forgot_password_email", None)
                st.session_state["auth_reset_notice"] = "A local password reset request is ready on this device."
                st.switch_page("pages/0_reset_password.py")
            else:
                st.info("If an account exists for this email, a local reset request can be started.")
    st.page_link("pages/0_login.py", label="Back to Sign In")
