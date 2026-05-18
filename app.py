"""
app.py
JIT Inventory Tracking System — Streamlit UI
Made-to-order phone case business, batched 2x per week.
"""

import psycopg2
from psycopg2.extras import DictCursor
from sqlalchemy import create_engine
import os
from datetime import date

import pandas as pd
import streamlit as st

# ── page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Decouart · JIT Inventory",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* ── global tokens ── */
    :root {
        --bg:      #0f1117;
        --surface: #1a1d27;
        --card:    #21253a;
        --border:  #2e3352;
        --accent:  #6c63ff;
        --danger:  #ff4c6a;
        --warn:    #f5a623;
        --success: #2dd4bf;
        --text:    #e8eaf6;
        --muted:   #8b92b8;
    }

    /* hide streamlit chrome */
    #MainMenu, footer, header { visibility: hidden; }

    /* app background */
    .stApp { background: var(--bg); color: var(--text); }

    /* sidebar */
    section[data-testid="stSidebar"] { background: var(--surface); border-right: 1px solid var(--border); }

    /* tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: var(--surface);
        padding: 8px 12px;
        border-radius: 12px;
        border: 1px solid var(--border);
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        color: var(--muted);
        border-radius: 8px;
        padding: 6px 20px;
        font-weight: 600;
        font-size: 0.9rem;
    }
    .stTabs [aria-selected="true"] {
        background: var(--accent) !important;
        color: #fff !important;
    }

    /* metric cards */
    div[data-testid="metric-container"] {
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 16px 20px;
    }
    div[data-testid="metric-container"] label { color: var(--muted) !important; font-size: 0.8rem; }
    div[data-testid="metric-container"] div[data-testid="stMetricValue"] { color: var(--text) !important; font-size: 1.6rem; }

    /* alert cards — custom */
    .alert-card {
        background: rgba(255, 76, 106, 0.10);
        border: 1px solid var(--danger);
        border-radius: 12px;
        padding: 14px 20px;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        gap: 14px;
        animation: pulse-border 2.5s infinite;
    }
    .ok-card {
        background: rgba(45, 212, 191, 0.08);
        border: 1px solid var(--success);
        border-radius: 12px;
        padding: 10px 18px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    @keyframes pulse-border {
        0%, 100% { box-shadow: 0 0 0 0 rgba(255,76,106,0.0); }
        50%       { box-shadow: 0 0 0 5px rgba(255,76,106,0.15); }
    }
    .alert-model { font-weight: 700; font-size: 1rem; color: var(--danger); }
    .alert-text  { font-size: 0.88rem; color: #ffa5b4; }
    .ok-model    { font-weight: 600; font-size: 0.95rem; color: var(--success); }
    .ok-text     { font-size: 0.85rem; color: var(--muted); }

    /* dataframe tweaks */
    .stDataFrame { border-radius: 10px; overflow: hidden; }
    thead tr th { background: var(--card) !important; color: var(--muted) !important; font-size: 0.78rem; text-transform: uppercase; }

    /* buttons */
    div.stButton > button {
        background: var(--accent);
        color: #fff;
        border: none;
        border-radius: 10px;
        padding: 10px 28px;
        font-weight: 700;
        font-size: 0.95rem;
        transition: opacity 0.2s, transform 0.1s;
    }
    div.stButton > button:hover { opacity: 0.85; transform: translateY(-1px); }
    div.stButton > button:active { transform: translateY(0); }

    /* form inputs */
    div[data-testid="stSelectbox"] > div,
    div[data-testid="stNumberInput"] > div > div {
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: 8px;
        color: var(--text);
    }

    /* success/error messages */
    div[data-testid="stAlert"] { border-radius: 10px; }

    /* section header */
    .section-head {
        font-size: 1.05rem;
        font-weight: 700;
        color: var(--accent);
        letter-spacing: 0.04em;
        text-transform: uppercase;
        margin-bottom: 6px;
    }

    /* hero banner */
    .hero {
        background: linear-gradient(135deg, #1a1d27 0%, #21253a 100%);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 28px 32px;
        margin-bottom: 24px;
    }
    .hero h1 { font-size: 1.8rem; font-weight: 800; margin: 0; }
    .hero p  { color: var(--muted); margin: 6px 0 0; font-size: 0.92rem; }
</style>
""", unsafe_allow_html=True)


# ── DB helpers ───────────────────────────────────────────────────────────────
def get_db_url():
    return st.secrets["connections"]["postgresql"]["url"]

def get_engine():
    return create_engine(get_db_url())

def get_conn():
    return psycopg2.connect(get_db_url(), cursor_factory=DictCursor)

def execute_write(query: str, params: tuple = None):
    conn = get_conn()
    cur = conn.cursor()
    try:
        if params:
            cur.execute(query, params)
        else:
            cur.execute(query)
        conn.commit()
    finally:
        cur.close()
        conn.close()

def execute_read(query: str, params: tuple = None, fetchone=False):
    conn = get_conn()
    cur = conn.cursor()
    try:
        if params:
            cur.execute(query, params)
        else:
            cur.execute(query)
        if fetchone:
            return cur.fetchone()
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


@st.cache_data(ttl=2)
def load_dashboard_data() -> pd.DataFrame:
    """Return per-model inventory with pending totals & net inventory."""
    engine = get_engine()
    df = pd.read_sql_query("""
        SELECT
            i.phone_model                        AS "Phone Model",
            i.on_hand_stock                      AS "On Hand",
            COALESCE(SUM(CASE WHEN ob.status = 'Pending'
                         THEN ob.quantity ELSE 0 END), 0)
                                                 AS "Pending Orders",
            i.on_hand_stock -
                COALESCE(SUM(CASE WHEN ob.status = 'Pending'
                             THEN ob.quantity ELSE 0 END), 0)
                                                 AS "Net Inventory",
            i.safety_buffer                      AS "Safety Buffer"
        FROM inventory i
        LEFT JOIN order_batches ob ON i.phone_model = ob.phone_model
        GROUP BY i.id
        ORDER BY i.phone_model
    """, engine)
    df["⚠️ Alert"] = df["Net Inventory"] <= df["Safety Buffer"]
    df["Order Needed"] = (df["Safety Buffer"] - df["Net Inventory"] + 1).clip(lower=0)
    return df


@st.cache_data(ttl=2)
def load_phone_models():
    rows = execute_read("SELECT phone_model FROM inventory ORDER BY phone_model")
    return [r["phone_model"] for r in rows]


@st.cache_data(ttl=2)
def load_recent_orders(limit: int = 40) -> pd.DataFrame:
    engine = get_engine()
    df = pd.read_sql_query(f"""
        SELECT date_recorded AS "Date", phone_model AS "Phone Model",
               quantity AS "Qty", status AS "Status", COALESCE(note, '') AS "Note"
        FROM order_batches
        ORDER BY id DESC
        LIMIT {limit}
    """, engine)
    return df


def submit_order(phone_model: str, quantity: int, note: str = ""):
    execute_write("""
        INSERT INTO order_batches (date_recorded, phone_model, quantity, status, note)
        VALUES (%s, %s, %s, 'Pending', %s)
    """, (date.today().isoformat(), phone_model, quantity, note.strip()))


def load_pending_orders_for_edit() -> list[dict]:
    rows = execute_read("""
        SELECT id, date_recorded, phone_model, quantity, COALESCE(note, '') AS note
        FROM order_batches 
        WHERE status = 'Pending'
        ORDER BY id DESC
    """)
    return [{"id": r["id"], "label": f"#{r['id']} — {r['phone_model']} (Qty: {r['quantity']}) — {r['date_recorded']}", "phone_model": r["phone_model"], "quantity": r["quantity"], "note": r["note"]} for r in rows]


def update_logged_order(order_id: int, new_model: str, new_qty: int, new_note: str = ""):
    execute_write("UPDATE order_batches SET phone_model = %s, quantity = %s, note = %s WHERE id = %s", (new_model, new_qty, new_note.strip(), order_id))


def delete_logged_order(order_id: int):
    execute_write("DELETE FROM order_batches WHERE id = %s", (order_id,))


def fulfill_all_pending():
    pending = execute_read("""
        SELECT phone_model, SUM(quantity) AS total_qty
        FROM order_batches
        WHERE status = 'Pending'
        GROUP BY phone_model
    """)

    if not pending:
        return 0

    conn = get_conn()
    cur = conn.cursor()
    try:
        for row in pending:
            cur.execute("""
                UPDATE inventory
                SET on_hand_stock = GREATEST(0, on_hand_stock - %s)
                WHERE phone_model = %s
            """, (row["total_qty"], row["phone_model"]))

        cur.execute("""
            UPDATE order_batches SET status = 'Fulfilled'
            WHERE status = 'Pending'
        """)
        conn.commit()
    finally:
        cur.close()
        conn.close()
        
    return len(pending)


def update_stock(phone_model: str, new_qty: int):
    execute_write("UPDATE inventory SET on_hand_stock = %s WHERE phone_model = %s", (new_qty, phone_model))


def add_new_model(phone_model: str, initial_stock: int, safety_buffer: int) -> bool:
    try:
        execute_write("""
            INSERT INTO inventory (phone_model, on_hand_stock, safety_buffer)
            VALUES (%s, %s, %s)
        """, (phone_model, initial_stock, safety_buffer))
        return True
    except psycopg2.IntegrityError:
        return False


def rename_model(old_name: str, new_name: str) -> bool:
    # PostgreSQL handles cascading updates via the ON UPDATE CASCADE constraint we created
    # Check if new name exists
    exists = execute_read("SELECT 1 FROM inventory WHERE phone_model = %s", (new_name,), fetchone=True)
    if exists:
        return False
    execute_write("UPDATE inventory SET phone_model = %s WHERE phone_model = %s", (new_name, old_name))
    return True


# ── page header ──────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
  <h1>📦 JIT Inventory Tracker</h1>
  <p>Made-to-order phone case studio · Batched fulfilment · 2× per week</p>
</div>
""", unsafe_allow_html=True)

tab_dashboard, tab_log, tab_stock = st.tabs(
    ["📊  Dashboard", "➕  Log Order", "🔧  Stock Manager"]
)

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════
with tab_dashboard:
    df = load_dashboard_data()
    alerts  = df[df["⚠️ Alert"]]
    healthy = df[~df["⚠️ Alert"]]

    # ── KPI row ──────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Models",       len(df))
    c2.metric("🔴 Alerts",          len(alerts),
              delta=f"-{len(healthy)} healthy", delta_color="inverse")
    c3.metric("Total Pending Units", int(df["Pending Orders"].sum()))
    c4.metric("Total On Hand",       int(df["On Hand"].sum()))

    st.markdown("---")

    # ── Fulfill button ────────────────────────────────────────────────────────
    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        if st.button("✅  Fulfill All Pending", key="fulfill_btn"):
            n = fulfill_all_pending()
            if n:
                st.success(f"Fulfilled orders for {n} model(s). Stock updated!")
                load_dashboard_data.clear()
                load_recent_orders.clear()
                st.rerun()
            else:
                st.info("No pending orders to fulfill.")
    with col_info:
        st.caption(
            "Clicking **Fulfill All Pending** deducts every pending batch from "
            "On-Hand stock and marks those orders as **Fulfilled**."
        )

    st.markdown("---")

    # ── Alert cards ───────────────────────────────────────────────────────────
    st.markdown('<p class="section-head">🚨 Stock Alerts</p>', unsafe_allow_html=True)

    if alerts.empty:
        st.success("✅  All models are above the safety buffer. You're good to go!")
    else:
        for _, row in alerts.iterrows():
            needed = int(row["Order Needed"])
            net    = int(row["Net Inventory"])
            st.markdown(f"""
            <div class="alert-card">
              <span style="font-size:1.6rem;">🚨</span>
              <div>
                <div class="alert-model">{row['Phone Model']}</div>
                <div class="alert-text">
                  Net inventory: <b>{net}</b> &nbsp;·&nbsp;
                  Safety buffer: <b>{int(row['Safety Buffer'])}</b> &nbsp;·&nbsp;
                  Order <b>{needed}</b> more blank{'s' if needed != 1 else ''} immediately
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<p class="section-head">✅ Healthy Stock</p>', unsafe_allow_html=True)

    if healthy.empty:
        st.warning("All models are in alert state!")
    else:
        for _, row in healthy.iterrows():
            surplus = int(row["Net Inventory"]) - int(row["Safety Buffer"])
            st.markdown(f"""
            <div class="ok-card">
              <span style="font-size:1.2rem;">✅</span>
              <div>
                <span class="ok-model">{row['Phone Model']}</span>
                <span class="ok-text"> &nbsp;·&nbsp; Net: {int(row['Net Inventory'])}
                  &nbsp;·&nbsp; {surplus} above buffer</span>
              </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # ── Full inventory table ──────────────────────────────────────────────────
    st.markdown('<p class="section-head">📋 Full Inventory Table</p>',
                unsafe_allow_html=True)

    display_df = df[["Phone Model", "On Hand", "Pending Orders",
                      "Net Inventory", "Safety Buffer"]].copy()

    def colour_row(row):
        colour = "background-color: rgba(255,76,106,0.15); color: #ff4c6a;" \
                 if row["Net Inventory"] <= row["Safety Buffer"] \
                 else ""
        return [colour] * len(row)

    styled = display_df.style.apply(colour_row, axis=1).format({
        "On Hand": "{:,}",
        "Pending Orders": "{:,}",
        "Net Inventory": "{:,}",
        "Safety Buffer": "{:,}",
    })
    st.dataframe(styled, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — LOG ORDER
# ═══════════════════════════════════════════════════════════════════════════════
with tab_log:
    st.markdown('<p class="section-head">Log Incoming Orders</p>',
                unsafe_allow_html=True)

    models = load_phone_models()

    with st.form("order_form", clear_on_submit=True):
        col_a, col_b = st.columns([2, 1])
        with col_a:
            selected_model = st.selectbox(
                "Phone Model",
                options=models,
                help="Select the phone model the case blank is for.",
                key="form_model",
            )
        with col_b:
            quantity = st.number_input(
                "Quantity",
                min_value=1,
                max_value=500,
                value=1,
                step=1,
                key="form_qty",
            )
        note = st.text_input(
            "Note (optional)",
            placeholder="e.g. Rush order, customer name, special colour...",
            max_chars=120,
            key="form_note",
        )

        submitted = st.form_submit_button("➕  Add to Pending Batch",
                                          use_container_width=True)

    if submitted:
        if quantity < 1:
            st.error("Quantity must be at least 1.")
        else:
            submit_order(selected_model, quantity, note)
            st.success(
                f"✅ Logged **{quantity}** unit(s) of **{selected_model}** "
                f"as Pending for {date.today().strftime('%b %d, %Y')}."
                + (f" Note: *{note}*" if note.strip() else "")
            )
            load_dashboard_data.clear()
            load_recent_orders.clear()

    st.markdown("---")
    st.markdown('<p class="section-head">✏️ Edit / Delete Pending Order</p>',
                unsafe_allow_html=True)
    
    pending_orders = load_pending_orders_for_edit()
    
    if not pending_orders:
        st.info("No pending orders to edit.")
    else:
        selected_order = st.selectbox(
            "Select Order to Edit",
            options=pending_orders,
            format_func=lambda o: o["label"],
            key="edit_order_sel"
        )
        
        if selected_order:
            with st.form("edit_order_form", clear_on_submit=False):
                col_m, col_q = st.columns([2, 1])
                with col_m:
                    try:
                        m_idx = models.index(selected_order["phone_model"])
                    except ValueError:
                        m_idx = 0
                        
                    edit_model = st.selectbox("Update Phone Model", options=models, index=m_idx)
                with col_q:
                    edit_qty = st.number_input("Update Quantity", min_value=1, max_value=500, value=int(selected_order["quantity"]), step=1)

                edit_note = st.text_input(
                    "Update Note (optional)",
                    value=selected_order.get("note", ""),
                    placeholder="e.g. Rush order, customer name...",
                    max_chars=120,
                )
                
                col_btn_update, col_btn_del = st.columns(2)
                with col_btn_update:
                    update_btn = st.form_submit_button("💾 Save Changes", use_container_width=True)
                with col_btn_del:
                    delete_btn = st.form_submit_button("🗑️ Delete Order", use_container_width=True)
                    
            if update_btn:
                update_logged_order(selected_order["id"], edit_model, edit_qty, edit_note)
                st.success(f"✅ Updated Order #{selected_order['id']}.")
                load_dashboard_data.clear()
                load_recent_orders.clear()
                st.rerun()
                
            if delete_btn:
                delete_logged_order(selected_order["id"])
                st.success(f"🗑️ Deleted Order #{selected_order['id']}.")
                load_dashboard_data.clear()
                load_recent_orders.clear()
                st.rerun()

    st.markdown("---")
    st.markdown('<p class="section-head">Recent Order Log</p>',
                unsafe_allow_html=True)

    orders_df = load_recent_orders()
    if orders_df.empty:
        st.info("No orders have been logged yet.")
    else:
        def colour_status(val):
            if val == "Pending":
                return "color: #f5a623; font-weight: 600;"
            elif val == "Fulfilled":
                return "color: #2dd4bf; font-weight: 600;"
            return ""
        styled_orders = orders_df.style.map(colour_status, subset=["Status"])
        st.dataframe(styled_orders, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — STOCK MANAGER
# ═══════════════════════════════════════════════════════════════════════════════
with tab_stock:
    st.markdown('<p class="section-head">Update On-Hand Stock</p>',
                unsafe_allow_html=True)
    st.caption("Use this panel after a stock delivery to set accurate on-hand counts.")

    inv_df = load_dashboard_data()

    with st.form("stock_form"):
        col_m, col_q = st.columns([2, 1])
        with col_m:
            stock_model = st.selectbox(
                "Phone Model",
                options=inv_df["Phone Model"].tolist(),
                key="stock_model",
            )
        with col_q:
            # pre-fill with current on_hand
            current_val = int(inv_df.loc[
                inv_df["Phone Model"] == stock_model, "On Hand"].values[0]
            ) if not inv_df.empty else 0

            new_stock = st.number_input(
                "New On-Hand Count",
                min_value=0,
                max_value=9999,
                value=current_val,
                step=1,
                key="stock_qty",
            )

        save_stock = st.form_submit_button("💾  Save Stock Level",
                                           use_container_width=True)

    if save_stock:
        update_stock(stock_model, new_stock)
        st.success(f"✅ Updated **{stock_model}** on-hand stock to **{new_stock}** units.")
        load_dashboard_data.clear()
        st.rerun()

    st.markdown("---")
    st.markdown('<p class="section-head">➕ Add New Phone Model</p>',
                unsafe_allow_html=True)
    st.caption("Add a brand new phone model to the inventory system.")

    with st.form("add_model_form", clear_on_submit=True):
        col_name, col_init, col_safe = st.columns([2, 1, 1])
        with col_name:
            new_model_name = st.text_input("New Phone Model Name", placeholder="e.g., iPhone 18 Pro")
        with col_init:
            new_model_init_stock = st.number_input("Initial Stock", min_value=0, value=0, step=1)
        with col_safe:
            new_model_safety = st.number_input("Safety Buffer", min_value=0, value=5, step=1)
            
        add_model_btn = st.form_submit_button("➕ Add Model", use_container_width=True)
        
    if add_model_btn:
        if not new_model_name.strip():
            st.error("Phone model name cannot be empty.")
        else:
            success = add_new_model(new_model_name.strip(), new_model_init_stock, new_model_safety)
            if success:
                st.success(f"✅ Added **{new_model_name.strip()}** to the inventory system.")
                load_dashboard_data.clear()
                load_phone_models.clear()
                st.rerun()
            else:
                st.error(f"❌ Model **{new_model_name.strip()}** already exists in the system.")

    st.markdown("---")
    st.markdown('<p class="section-head">✏️ Rename Phone Model</p>',
                unsafe_allow_html=True)
    st.caption("Change the name of an existing phone model.")

    with st.form("rename_model_form", clear_on_submit=True):
        col_old, col_new = st.columns(2)
        with col_old:
            rename_old_name = st.selectbox("Select Model to Rename", options=inv_df["Phone Model"].tolist(), key="rename_old")
        with col_new:
            rename_new_name = st.text_input("New Model Name", placeholder="e.g., iPhone 18 Pro Max")
            
        rename_model_btn = st.form_submit_button("✏️ Rename Model", use_container_width=True)
        
    if rename_model_btn:
        if not rename_new_name.strip():
            st.error("New model name cannot be empty.")
        else:
            success = rename_model(rename_old_name, rename_new_name.strip())
            if success:
                st.success(f"✅ Renamed **{rename_old_name}** to **{rename_new_name.strip()}**.")
                load_dashboard_data.clear()
                load_phone_models.clear()
                st.rerun()
            else:
                st.error(f"❌ Model **{rename_new_name.strip()}** already exists.")

    st.markdown("---")
    st.markdown('<p class="section-head">Current Stock Levels</p>',
                unsafe_allow_html=True)
    show_df = inv_df[["Phone Model", "On Hand", "Safety Buffer", "Net Inventory"]].copy()
    # Dynamically set height (approx 36px per row + 43px for header) to avoid internal scroll
    st.dataframe(show_df, use_container_width=True, hide_index=True, height=len(show_df) * 36 + 43)
