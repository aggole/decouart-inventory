"""Log Order tab: add orders, edit/delete pending ones, and the order log."""

import streamlit as st

import db
from views.common import flash, section

STATUS_COLOURS = {
    "Pending": "color: #f5a623; font-weight: 600;",
    "Fulfilled": "color: #2dd4bf; font-weight: 600;",
}


def render() -> None:
    models = db.load_inventory()["Phone Model"].tolist()
    pending = db.load_pending_orders()

    _new_order_form(models)
    st.markdown("---")
    _edit_pending_order(models, pending)
    st.markdown("---")
    _order_log(pending)


def _new_order_form(models: list[str]) -> None:
    section("Log Incoming Orders")
    with st.form("order_form", clear_on_submit=True):
        col_a, col_b = st.columns([2, 1])
        with col_a:
            model = st.selectbox("Phone Model", options=models, key="form_model",
                                 help="Select the phone model the case blank is for.")
        with col_b:
            quantity = st.number_input("Quantity", min_value=1, max_value=500,
                                       value=1, step=1, key="form_qty")
        note = st.text_input("Note (optional)", max_chars=120, key="form_note",
                             placeholder="e.g. Rush order, customer name, special colour...")
        submitted = st.form_submit_button("➕  Add to Pending Batch", width="stretch")

    if submitted and model:
        db.add_order(model, int(quantity), note)
        flash(f"✅ Logged **{quantity}** unit(s) of **{model}** as Pending for {db.today()}."
              + (f" Note: *{note.strip()}*" if note.strip() else ""))
        st.rerun()


def _edit_pending_order(models: list[str], pending) -> None:
    section("✏️ Edit / Delete Pending Order")
    if pending.empty:
        st.info("No pending orders to edit.")
        return

    order_ids = pending["id"].tolist()
    by_id = pending.set_index("id")
    order_id = st.selectbox(
        "Select Order to Edit",
        options=order_ids,
        format_func=lambda i: (f"#{i} — {by_id.at[i, 'phone_model']} "
                               f"(Qty: {by_id.at[i, 'quantity']}) — {by_id.at[i, 'date_recorded']}"),
        key="edit_order_sel",
    )
    order = by_id.loc[order_id]

    # key the form by order so its fields reset when another order is picked
    with st.form(f"edit_order_form_{order_id}"):
        col_m, col_q = st.columns([2, 1])
        with col_m:
            index = models.index(order["phone_model"]) if order["phone_model"] in models else 0
            model = st.selectbox("Update Phone Model", options=models, index=index)
        with col_q:
            quantity = st.number_input("Update Quantity", min_value=1, max_value=500,
                                       value=int(order["quantity"]), step=1)
        note = st.text_input("Update Note (optional)", value=order["note"], max_chars=120,
                             placeholder="e.g. Rush order, customer name...")
        col_save, col_delete = st.columns(2)
        with col_save:
            save = st.form_submit_button("💾 Save Changes", width="stretch")
        with col_delete:
            delete = st.form_submit_button("🗑️ Delete Order", width="stretch")

    if save:
        db.update_order(int(order_id), model, int(quantity), note)
        flash(f"✅ Updated Order #{order_id}.")
        st.rerun()
    if delete:
        db.delete_order(int(order_id))
        flash(f"🗑️ Deleted Order #{order_id}.")
        st.rerun()


def _order_log(pending) -> None:
    col_head, col_toggle = st.columns([3, 1])
    with col_head:
        section("Recent Order Log")
    with col_toggle:
        show_fulfilled = st.toggle("Show Fulfilled", value=False, key="show_fulfilled_toggle")

    # Pending orders are always shown in full; history is only fetched on request.
    orders = db.load_order_history() if show_fulfilled else pending.assign(status="Pending")
    if orders.empty:
        st.info("No pending orders. Toggle **Show Fulfilled** above to see past orders."
                if not show_fulfilled else "No orders have been logged yet.")
        return

    table = orders.rename(columns={
        "date_recorded": "Date", "phone_model": "Phone Model",
        "quantity": "Qty", "status": "Status", "note": "Note",
    })[["Date", "Phone Model", "Qty", "Status", "Note"]]
    styled = table.style.map(lambda v: STATUS_COLOURS.get(v, ""), subset=["Status"])
    st.dataframe(styled, width="stretch", hide_index=True)
