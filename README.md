# Decouart JIT Inventory Tracker

Streamlit app for tracking phone case blanks against pending orders, backed by Supabase Postgres.

## Files

| File | What it does |
| --- | --- |
| `app.py` | Entry point: page setup and the three tabs |
| `views/` | One module per tab (`dashboard.py`, `orders.py`, `stock.py`) |
| `db.py` | All database queries, the shared connection and caching |
| `schema.sql` | Table definitions, applied automatically on startup |
| `styles.css` | The app's look |

## Setup

Add the database URL to Streamlit secrets (`.streamlit/secrets.toml` locally, or the app's Secrets on Streamlit Cloud):

```toml
[connections.postgresql]
url = "postgresql://USER:PASSWORD@HOST:6543/postgres"

# optional: timezone used for order dates (default Asia/Tokyo)
[app]
timezone = "Asia/Tokyo"
```

Then run `pip install -r requirements.txt` and `streamlit run app.py`.
A new, empty database gets its tables created on first start.
