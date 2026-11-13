-- Database schema for the Decouart inventory tracker.
-- Every statement is idempotent: the app runs this file once at startup,
-- so a fresh database is set up automatically and an older one is upgraded.

CREATE TABLE IF NOT EXISTS inventory (
    id            SERIAL  PRIMARY KEY,
    phone_model   TEXT    NOT NULL UNIQUE,
    on_hand_stock INTEGER NOT NULL DEFAULT 0,
    safety_buffer INTEGER NOT NULL DEFAULT 5
);

CREATE TABLE IF NOT EXISTS order_batches (
    id            SERIAL  PRIMARY KEY,
    date_recorded DATE    NOT NULL DEFAULT CURRENT_DATE,
    phone_model   TEXT    NOT NULL
                  REFERENCES inventory (phone_model)
                  ON UPDATE CASCADE ON DELETE CASCADE,
    quantity      INTEGER NOT NULL,
    status        TEXT    NOT NULL DEFAULT 'Pending'
                  CHECK (status IN ('Pending', 'Fulfilled')),
    note          TEXT
);

-- Databases created before notes existed lack this column.
ALTER TABLE order_batches ADD COLUMN IF NOT EXISTS note TEXT;
