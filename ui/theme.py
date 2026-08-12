import streamlit as st

from ui.styles import render_global_styles


LIGHT = {"background": "#FFFFFF", "surface": "#FFFFFF", "secondary": "#F7F8F9", "elevated": "#E8EAEB", "text": "#192B37", "secondary_text": "#5E6A73", "muted": "#758087", "border": "#D1D5D7", "hover": "#F5F6F7", "accent": "#FF5640", "icon_primary": "#192B37", "icon_secondary": "#5E6A73", "icon_accent": "#FF5640", "button_secondary_text": "#192B37", "input_bg": "#FFFFFF", "input_hover": "#E8EAEB", "input_border": "#D1D5D7", "input_text": "#192B37", "input_placeholder": "#758087", "input_focus": "#FF5640", "disabled_bg": "#E8EAEB", "disabled_text": "#758087"}
DARK = {"background": "#192B37", "surface": "#30404B", "secondary": "#243640", "elevated": "#47555F", "text": "#FFFFFF", "secondary_text": "#D1D5D7", "muted": "#BABFC3", "border": "#47555F", "hover": "#3B4C57", "accent": "#FF5640", "icon_primary": "#FFFFFF", "icon_secondary": "#D1D5D7", "icon_accent": "#FF5640", "button_secondary_text": "#FFFFFF", "input_bg": "#263944", "input_hover": "#30404B", "input_border": "#47555F", "input_text": "#FFFFFF", "input_placeholder": "#BABFC3", "input_focus": "#FF5640", "disabled_bg": "#30404B", "disabled_text": "#8C959B"}


def apply_theme() -> None:
    if "dark_mode" not in st.session_state:
        st.session_state["dark_mode"] = False
    colors = DARK if st.session_state.get("dark_mode", False) else LIGHT
    render_global_styles(colors)


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown('<div class="sidebar-heading">WORKSPACE</div>', unsafe_allow_html=True)
        for label, value in [
            ("Environment", "Local Development"),
            ("Data Sources", "0 connected"),
            ("AI", "Optional / Offline"),
            ("Appearance", "Dark" if st.session_state.get("dark_mode", False) else "Light"),
        ]:
            st.markdown(
                f'<div class="sidebar-item"><span class="sidebar-label">{label}</span><span class="sidebar-value">{value}</span></div>',
                unsafe_allow_html=True,
            )
        st.markdown('<div class="sidebar-footer">Enterprise Data Intelligence</div>', unsafe_allow_html=True)
