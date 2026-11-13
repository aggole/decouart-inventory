"""
app.py
JIT Inventory Tracking System — Streamlit entry point.
Made-to-order phone case business, batched 2x per week.

Layout:
  db.py          all database access and caching
  schema.sql     table definitions (applied automatically at startup)
  styles.css     the app's look
  views/         one module per tab
"""

from pathlib import Path

import streamlit as st

from views import dashboard, orders, stock
from views.common import show_flash

st.set_page_config(
    page_title="Decouart · JIT Inventory",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

css = Path(__file__).with_name("styles.css").read_text()
st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <h1>📦 JIT Inventory Tracker</h1>
  <p>Made-to-order phone case studio · Batched fulfilment · 2× per week</p>
</div>
""", unsafe_allow_html=True)

show_flash()

tab_dashboard, tab_log, tab_stock = st.tabs(
    ["📊  Dashboard", "➕  Log Order", "🔧  Stock Manager"]
)

with tab_dashboard:
    dashboard.render()

with tab_log:
    orders.render()

with tab_stock:
    stock.render()
