"""Stock Manager tab: set on-hand counts, add and rename phone models."""

import streamlit as st

import db
from views.common import flash, section


def render() -> None:
    inventory = db.load_inventory()
    models = inventory["Phone Model"].tolist()

    _update_stock(inventory, models)
    st.markdown("---")
    _add_model()
    st.markdown("---")
    _rename_model(models)
    st.markdown("---")

    section("Current Stock Levels")
    table = inventory[["Phone Model", "On Hand", "Safety Buffer", "Net Inventory"]]
    # ~36px per row + header, so the whole table shows without an inner scrollbar
    st.dataframe(table, width="stretch", hide_index=True, height=len(table) * 36 + 43)


def _update_stock(inventory, models: list[str]) -> None:
    section("Update On-Hand Stock")
    st.caption("Use this panel after a stock delivery to set accurate on-hand counts.")
    if not models:
        st.info("Add a phone model below to get started.")
        return

    # Picked outside the form so the count below pre-fills with the chosen model's stock.
    col_m, col_q = st.columns([2, 1])
    with col_m:
        model = st.selectbox("Phone Model", options=models, key="stock_model")
    current = int(inventory.loc[inventory["Phone Model"] == model, "On Hand"].iloc[0])
    with col_q:
        new_stock = st.number_input("New On-Hand Count", min_value=0, max_value=9999,
                                    value=current, step=1, key=f"stock_qty_{model}")

    if st.button("💾  Save Stock Level", width="stretch", key="save_stock"):
        db.set_stock(model, int(new_stock))
        flash(f"✅ Updated **{model}** on-hand stock to **{new_stock}** units.")
        st.rerun()


def _add_model() -> None:
    section("➕ Add New Phone Model")
    st.caption("Add a brand new phone model to the inventory system.")
    with st.form("add_model_form", clear_on_submit=True):
        col_name, col_init, col_safe = st.columns([2, 1, 1])
        with col_name:
            name = st.text_input("New Phone Model Name", placeholder="e.g., iPhone 18 Pro")
        with col_init:
            initial = st.number_input("Initial Stock", min_value=0, value=0, step=1)
        with col_safe:
            buffer = st.number_input("Safety Buffer", min_value=0, value=5, step=1)
        submitted = st.form_submit_button("➕ Add Model", width="stretch")

    if not submitted:
        return
    name = name.strip()
    if not name:
        st.error("Phone model name cannot be empty.")
    elif db.add_model(name, int(initial), int(buffer)):
        flash(f"✅ Added **{name}** to the inventory system.")
        st.rerun()
    else:
        st.error(f"❌ Model **{name}** already exists in the system.")


def _rename_model(models: list[str]) -> None:
    section("✏️ Rename Phone Model")
    st.caption("Change the name of an existing phone model.")
    with st.form("rename_model_form", clear_on_submit=True):
        col_old, col_new = st.columns(2)
        with col_old:
            old = st.selectbox("Select Model to Rename", options=models, key="rename_old")
        with col_new:
            new = st.text_input("New Model Name", placeholder="e.g., iPhone 18 Pro Max")
        submitted = st.form_submit_button("✏️ Rename Model", width="stretch")

    if not submitted:
        return
    new = new.strip()
    if not new:
        st.error("New model name cannot be empty.")
    elif db.rename_model(old, new):
        flash(f"✅ Renamed **{old}** to **{new}**.")
        st.rerun()
    else:
        st.error(f"❌ Model **{new}** already exists.")
