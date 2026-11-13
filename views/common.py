"""Small helpers shared by the tabs."""

import streamlit as st


def section(title: str) -> None:
    st.markdown(f'<p class="section-head">{title}</p>', unsafe_allow_html=True)


def flash(message: str, kind: str = "success") -> None:
    """Show a message on the next rerun (st.rerun() would otherwise wipe it)."""
    st.session_state["_flash"] = (kind, message)


def show_flash() -> None:
    if "_flash" in st.session_state:
        kind, message = st.session_state.pop("_flash")
        getattr(st, kind)(message)
