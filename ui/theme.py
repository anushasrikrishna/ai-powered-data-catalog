import streamlit as st

from ui.styles import render_global_styles


LIGHT = {"background": "#FFFFFF", "surface": "#FFFFFF", "secondary": "#F7F8F9", "elevated": "#E8EAEB", "text": "#192B37", "secondary_text": "#5E6A73", "muted": "#758087", "border": "#D1D5D7", "hover": "#F5F6F7", "accent": "#FF5640", "icon_primary": "#192B37", "icon_secondary": "#5E6A73", "icon_accent": "#FF5640", "button_secondary_text": "#192B37"}
DARK = {"background": "#192B37", "surface": "#30404B", "secondary": "#243640", "elevated": "#47555F", "text": "#FFFFFF", "secondary_text": "#D1D5D7", "muted": "#BABFC3", "border": "#47555F", "hover": "#3B4C57", "accent": "#FF5640", "icon_primary": "#FFFFFF", "icon_secondary": "#D1D5D7", "icon_accent": "#FF5640", "button_secondary_text": "#FFFFFF"}


def apply_theme() -> None:
    colors = DARK if st.session_state.get("dark_mode", False) else LIGHT
    render_global_styles(colors)


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown('<div class="sidebar-heading">WORKSPACE</div>', unsafe_allow_html=True)
        for label, value in [
            ("Environment", "Local Development"),
            ("Data Sources", "0 connected"),
            ("AI", "Optional / Offline"),
            ("Appearance", "Dark mode" if st.session_state.get("dark_mode", False) else "Light mode"),
        ]:
            st.markdown(
                f'<div class="sidebar-item"><span class="sidebar-label">{label}</span><span class="sidebar-value">{value}</span></div>',
                unsafe_allow_html=True,
            )
        st.markdown('<div class="sidebar-footer">Enterprise Data Intelligence</div>', unsafe_allow_html=True)
