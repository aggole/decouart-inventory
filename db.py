"""
db.py
All database access for the inventory tracker.

Speed notes:
- One SQLAlchemy engine is created per server process (st.cache_resource) and
  its connections are reused across reruns and users. Opening a new connection
  to Supabase costs several network round trips, so reusing them is the
  biggest speed win.
- Reads are cached with st.cache_data. Every write calls clear_caches(), so
  the cache can be long-lived without showing stale data from this app.
"""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError

CACHE_TTL = 300  # seconds; also refreshes changes made outside the app
SCHEMA_FILE = Path(__file__).with_name("schema.sql")
DEFAULT_TIMEZONE = "Asia/Tokyo"


# ── connection ───────────────────────────────────────────────────────────────
@st.cache_resource
def get_engine() -> Engine:
    url = st.secrets["connections"]["postgresql"]["url"]
    # Be explicit about the driver so the installed psycopg2 is always used.
    url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    engine = create_engine(
        url,
        pool_size=2,
        max_overflow=3,
        pool_pre_ping=True,   # transparently replace connections the server dropped
        pool_recycle=300,     # don't keep connections around longer than 5 minutes
    )
    _ensure_schema(engine)
    return engine


def _ensure_schema(engine: Engine) -> None:
    """Create missing tables/columns. Runs once per server process."""
    with engine.begin() as conn:
        conn.exec_driver_sql(SCHEMA_FILE.read_text())


def clear_caches() -> None:
    """Call after every write so the next rerun reads fresh data."""
    load_inventory.clear()
    load_pending_orders.clear()
    load_order_history.clear()


def today() -> str:
    """Today's date in the business's timezone (the server clock is UTC)."""
    tz = st.secrets.get("app", {}).get("timezone", DEFAULT_TIMEZONE)
    return datetime.now(ZoneInfo(tz)).date().isoformat()


# ── reads ────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def load_inventory() -> pd.DataFrame:
    """Per-model stock with pending totals, net inventory and alert flags."""
    df = pd.read_sql_query(text("""
        SELECT
            i.phone_model                       AS "Phone Model",
            i.on_hand_stock                     AS "On Hand",
            COALESCE(p.pending, 0)              AS "Pending Orders",
            i.on_hand_stock - COALESCE(p.pending, 0)
                                                AS "Net Inventory",
            i.safety_buffer                     AS "Safety Buffer"
        FROM inventory i
        LEFT JOIN (
            SELECT phone_model, SUM(quantity) AS pending
            FROM order_batches
            WHERE status = 'Pending'
            GROUP BY phone_model
        ) p ON p.phone_model = i.phone_model
        ORDER BY i.phone_model
    """), get_engine())
    df["Alert"] = df["Net Inventory"] <= df["Safety Buffer"]
    df["Order Needed"] = (df["Safety Buffer"] - df["Net Inventory"] + 1).clip(lower=0)
    return df


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def load_pending_orders() -> pd.DataFrame:
    """Every pending order, newest first."""
    return pd.read_sql_query(text("""
        SELECT id, date_recorded, phone_model, quantity, COALESCE(note, '') AS note
        FROM order_batches
        WHERE status = 'Pending'
        ORDER BY id DESC
    """), get_engine())


@st.cache_data(ttl=CACHE_TTL, show_spinner=False)
def load_order_history(limit: int = 100) -> pd.DataFrame:
    """The most recent orders of any status, newest first."""
    return pd.read_sql_query(text("""
        SELECT id, date_recorded, phone_model, quantity, status, COALESCE(note, '') AS note
        FROM order_batches
        ORDER BY id DESC
        LIMIT :limit
    """), get_engine(), params={"limit": limit})


# ── writes ───────────────────────────────────────────────────────────────────
def _write(sql: str, **params) -> None:
    with get_engine().begin() as conn:
        conn.execute(text(sql), params)
    clear_caches()


def add_order(phone_model: str, quantity: int, note: str = "") -> None:
    _write("""
        INSERT INTO order_batches (date_recorded, phone_model, quantity, status, note)
        VALUES (:day, :model, :qty, 'Pending', :note)
    """, day=today(), model=phone_model, qty=quantity, note=note.strip())


def update_order(order_id: int, phone_model: str, quantity: int, note: str = "") -> None:
    _write("""
        UPDATE order_batches SET phone_model = :model, quantity = :qty, note = :note
        WHERE id = :id AND status = 'Pending'
    """, id=order_id, model=phone_model, qty=quantity, note=note.strip())


def delete_order(order_id: int) -> None:
    _write("DELETE FROM order_batches WHERE id = :id AND status = 'Pending'", id=order_id)


def fulfill_all_pending() -> tuple[int, list[dict]]:
    """
    Mark every pending order fulfilled and deduct it from stock, in a single
    statement so an order logged at the same moment can't be marked fulfilled
    without being deducted.

    Returns (number of models fulfilled, shortfalls) where each shortfall is
    {"model", "ordered", "on_hand"} for models that didn't have enough stock
    (their stock is set to 0).
    """
    with get_engine().begin() as conn:
        rows = conn.execute(text("""
            WITH fulfilled AS (
                UPDATE order_batches SET status = 'Fulfilled'
                WHERE status = 'Pending'
                RETURNING phone_model, quantity
            ),
            totals AS (
                SELECT phone_model, SUM(quantity) AS qty
                FROM fulfilled
                GROUP BY phone_model
            ),
            deducted AS (
                UPDATE inventory i
                SET on_hand_stock = GREATEST(0, i.on_hand_stock - t.qty)
                FROM totals t
                WHERE i.phone_model = t.phone_model
            )
            SELECT t.phone_model, t.qty, i.on_hand_stock AS before
            FROM totals t
            JOIN inventory i ON i.phone_model = t.phone_model
            ORDER BY t.phone_model
        """)).mappings().all()
    clear_caches()
    shortfalls = [
        {"model": r["phone_model"], "ordered": int(r["qty"]), "on_hand": int(r["before"])}
        for r in rows if r["qty"] > r["before"]
    ]
    return len(rows), shortfalls


def receive_stock(quantities: dict[str, int]) -> None:
    """Add a delivery to on-hand stock, e.g. {"iPhone 17": 20, "iPhone 15": 20}.
    All models are updated together in one transaction."""
    rows = [{"model": m, "qty": q} for m, q in quantities.items() if q > 0]
    if not rows:
        return
    with get_engine().begin() as conn:
        conn.execute(text("""
            UPDATE inventory SET on_hand_stock = on_hand_stock + :qty
            WHERE phone_model = :model
        """), rows)
    clear_caches()


def set_stock(phone_model: str, quantity: int) -> None:
    _write("UPDATE inventory SET on_hand_stock = :qty WHERE phone_model = :model",
           qty=quantity, model=phone_model)


def add_model(phone_model: str, initial_stock: int, safety_buffer: int) -> bool:
    """Returns False if the model already exists."""
    try:
        _write("""
            INSERT INTO inventory (phone_model, on_hand_stock, safety_buffer)
            VALUES (:model, :stock, :buffer)
        """, model=phone_model, stock=initial_stock, buffer=safety_buffer)
        return True
    except IntegrityError:
        return False


def rename_model(old_name: str, new_name: str) -> bool:
    """Returns False if new_name is already taken. Orders follow via ON UPDATE CASCADE."""
    try:
        _write("UPDATE inventory SET phone_model = :new WHERE phone_model = :old",
               new=new_name, old=old_name)
        return True
    except IntegrityError:
        return False
