import sqlite3
import psycopg2
import os

DB_URI = "postgresql://postgres.kussgclzjroauawnabnc:c8tsehcQvJpt$fT@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres"
SQLITE_PATH = os.path.join(os.path.dirname(__file__), "inventory.db")

def migrate():
    # 1. Connect to both DBs
    print("Connecting to PostgreSQL...")
    pg_conn = psycopg2.connect(DB_URI)
    pg_cur = pg_conn.cursor()
    
    print("Connecting to SQLite...")
    sl_conn = sqlite3.connect(SQLITE_PATH)
    sl_conn.row_factory = sqlite3.Row
    sl_cur = sl_conn.cursor()
    
    # 2. Create tables in PostgreSQL
    print("Creating tables in PostgreSQL...")
    pg_cur.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id SERIAL PRIMARY KEY,
            phone_model TEXT NOT NULL UNIQUE,
            on_hand_stock INTEGER NOT NULL DEFAULT 0,
            safety_buffer INTEGER NOT NULL DEFAULT 5
        )
    """)
    
    pg_cur.execute("""
        CREATE TABLE IF NOT EXISTS order_batches (
            id SERIAL PRIMARY KEY,
            date_recorded DATE NOT NULL DEFAULT CURRENT_DATE,
            phone_model TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending' CHECK (status IN ('Pending', 'Fulfilled')),
            FOREIGN KEY (phone_model) REFERENCES inventory(phone_model) ON UPDATE CASCADE ON DELETE CASCADE
        )
    """)
    pg_conn.commit()

    # 3. Read and insert inventory
    print("Migrating inventory table...")
    sl_cur.execute("SELECT phone_model, on_hand_stock, safety_buffer FROM inventory")
    inv_rows = sl_cur.fetchall()
    
    # clear existing data if script run multiple times
    pg_cur.execute("TRUNCATE TABLE order_batches, inventory RESTART IDENTITY")
    
    for row in inv_rows:
        pg_cur.execute(
            "INSERT INTO inventory (phone_model, on_hand_stock, safety_buffer) VALUES (%s, %s, %s)",
            (row["phone_model"], row["on_hand_stock"], row["safety_buffer"])
        )
        
    # 4. Read and insert order_batches
    print("Migrating order_batches table...")
    sl_cur.execute("SELECT date_recorded, phone_model, quantity, status FROM order_batches")
    ord_rows = sl_cur.fetchall()
    
    for row in ord_rows:
        pg_cur.execute(
            "INSERT INTO order_batches (date_recorded, phone_model, quantity, status) VALUES (%s, %s, %s, %s)",
            (row["date_recorded"], row["phone_model"], row["quantity"], row["status"])
        )

    pg_conn.commit()
    
    print("✅ Migration to PostgreSQL completed successfully!")
    
    pg_conn.close()
    sl_conn.close()

if __name__ == "__main__":
    migrate()
