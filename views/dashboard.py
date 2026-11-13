"""Dashboard tab: KPIs, fulfil button, stock alerts and the inventory table."""

from html import escape

import streamlit as st

import db
from views.common import flash, section


def render() -> None:
    df = db.load_inventory()
    alerts = df[df["Alert"]]
    healthy = df[~df["Alert"]]

    # ── KPI row ──────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Models", len(df))
    c2.metric("🔴 Alerts", len(alerts),
              delta=f"-{len(healthy)} healthy", delta_color="inverse")
    c3.metric("Total Pending Units", int(df["Pending Orders"].sum()))
    c4.metric("Total On Hand", int(df["On Hand"].sum()))

    st.markdown("---")
    _fulfil_button()
    st.markdown("---")

    # ── alert cards ──────────────────────────────────────────────────────────
    section("🚨 Stock Alerts")
    if alerts.empty:
        st.success("✅  All models are above the safety buffer. You're good to go!")
    for _, row in alerts.iterrows():
        needed = int(row["Order Needed"])
        st.markdown(f"""
        <div class="alert-card">
          <span style="font-size:1.6rem;">🚨</span>
          <div>
            <div class="alert-model">{escape(row["Phone Model"])}</div>
            <div class="alert-text">
              Net inventory: <b>{int(row["Net Inventory"])}</b> &nbsp;·&nbsp;
              Safety buffer: <b>{int(row["Safety Buffer"])}</b> &nbsp;·&nbsp;
              Order <b>{needed}</b> more blank{'s' if needed != 1 else ''} immediately
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    section("✅ Healthy Stock")
    if healthy.empty:
        st.warning("All models are in alert state!")
    for _, row in healthy.iterrows():
        net, buffer = int(row["Net Inventory"]), int(row["Safety Buffer"])
        st.markdown(f"""
        <div class="ok-card">
          <span style="font-size:1.2rem;">✅</span>
          <div>
            <span class="ok-model">{escape(row["Phone Model"])}</span>
            <span class="ok-text"> &nbsp;·&nbsp; Net: {net}
              &nbsp;·&nbsp; {net - buffer} above buffer</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ── full table ───────────────────────────────────────────────────────────
    section("📋 Full Inventory Table")
    table = df[["Phone Model", "On Hand", "Pending Orders", "Net Inventory", "Safety Buffer"]]

    def colour_row(row):
        alert = row["Net Inventory"] <= row["Safety Buffer"]
        return ["background-color: rgba(255,76,106,0.15); color: #ff4c6a;" if alert else ""] * len(row)

    st.dataframe(table.style.apply(colour_row, axis=1), width="stretch", hide_index=True)


def _fulfil_button() -> None:
    col_btn, col_info = st.columns([1, 3])
    with col_info:
        st.caption(
            "Clicking **Fulfill All Pending** deducts every pending batch from "
            "On-Hand stock and marks those orders as **Fulfilled**."
        )
    with col_btn:
        if not st.button("✅  Fulfill All Pending", key="fulfill_btn"):
            return

    n, shortfalls = db.fulfill_all_pending()
    if not n:
        st.info("No pending orders to fulfill.")
        return
    message = f"Fulfilled orders for {n} model(s). Stock updated!"
    if shortfalls:
        lines = "\n".join(
            f"- **{s['model']}**: {s['ordered']} ordered but only {s['on_hand']} on hand"
            for s in shortfalls
        )
        flash(f"{message}\n\n⚠️ Not enough stock for these, so they were set to 0:\n{lines}",
              "warning")
    else:
        flash(message)
    st.rerun()
