"""
database_setup.py
Initializes the SQLite database for the JIT Inventory Tracking app
and seeds it with mock data for iPhone 15, 16, and 17.
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "inventory.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_db():
    conn = get_connection()
    cursor = conn.cursor()

    # ── inventory table ──────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            phone_model   TEXT    NOT NULL UNIQUE,
            on_hand_stock INTEGER NOT NULL DEFAULT 0,
            safety_buffer INTEGER NOT NULL DEFAULT 5
        )
    """)

    # ── order_batches table ──────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_batches (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            date_recorded DATE    NOT NULL DEFAULT (date('now')),
            phone_model   TEXT    NOT NULL,
            quantity      INTEGER NOT NULL,
            status        TEXT    NOT NULL DEFAULT 'Pending'
                          CHECK(status IN ('Pending', 'Fulfilled')),
            FOREIGN KEY (phone_model) REFERENCES inventory(phone_model)
        )
    """)

    # ── seed mock inventory data ─────────────────────────────────────────────
    seed_models = [
        ("iPhone 15",   18, 5),
        ("iPhone 15 Plus", 12, 5),
        ("iPhone 15 Pro", 20, 5),
        ("iPhone 15 Pro Max", 8, 5),
        ("iPhone 16",   25, 5),
        ("iPhone 16 Plus", 10, 5),
        ("iPhone 16 Pro", 15, 5),
        ("iPhone 16 Pro Max", 6, 5),
        ("iPhone 17",   30, 5),
        ("iPhone 17 Plus", 4, 5),
        ("iPhone 17 Pro", 22, 5),
        ("iPhone 17 Pro Max", 3, 5),
    ]

    cursor.executemany("""
        INSERT OR IGNORE INTO inventory (phone_model, on_hand_stock, safety_buffer)
        VALUES (?, ?, ?)
    """, seed_models)

    # ── seed some pending orders so the dashboard has something to show ──────
    seed_orders = [
        ("2026-05-18", "iPhone 15",          3),
        ("2026-05-18", "iPhone 15 Pro Max",  5),
        ("2026-05-18", "iPhone 16",          8),
        ("2026-05-18", "iPhone 16 Plus",     7),
        ("2026-05-18", "iPhone 17 Plus",     4),
        ("2026-05-18", "iPhone 17 Pro Max",  3),
    ]

    for date, model, qty in seed_orders:
        cursor.execute("""
            INSERT INTO order_batches (date_recorded, phone_model, quantity, status)
            SELECT ?, ?, ?, 'Pending'
            WHERE NOT EXISTS (
                SELECT 1 FROM order_batches
                WHERE phone_model = ? AND status = 'Pending'
            )
        """, (date, model, qty, model))

    conn.commit()
    conn.close()
    print("✅  Database initialized and seeded successfully.")
    print(f"   Location: {DB_PATH}")


if __name__ == "__main__":
    initialize_db()
