# db.py
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "finance.db"

def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # ===== FINANCEIRO =====
    cur.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        type TEXT NOT NULL DEFAULT 'Banco',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        kind TEXT NOT NULL DEFAULT 'Despesa',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL,
        description TEXT NOT NULL,
        amount REAL NOT NULL,
        category_id INTEGER,
        account_id INTEGER NOT NULL,
        method TEXT,
        notes TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY(category_id) REFERENCES categories(id),
        FOREIGN KEY(account_id) REFERENCES accounts(id)
    );
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_date ON transactions(date);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_account ON transactions(account_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_category ON transactions(category_id);")

    # ===== INVESTIMENTOS =====
    cur.execute("""
    CREATE TABLE IF NOT EXISTS assets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        asset_class TEXT NOT NULL,
        currency TEXT NOT NULL DEFAULT 'BRL',
        broker_account_id INTEGER,
        issuer TEXT,
        rate_type TEXT,
        rate_value REAL,
        maturity_date TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY(broker_account_id) REFERENCES accounts(id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        asset_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        side TEXT NOT NULL,
        quantity REAL NOT NULL,
        price REAL NOT NULL,
        fees REAL NOT NULL DEFAULT 0,
        taxes REAL NOT NULL DEFAULT 0,
        note TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY(asset_id) REFERENCES assets(id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS income_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        asset_id INTEGER NOT NULL,
        date TEXT NOT NULL,
        type TEXT NOT NULL,
        amount REAL NOT NULL,
        note TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY(asset_id) REFERENCES assets(id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        asset_id INTEGER NOT NULL,
        date TEXT NOT NULL,                 -- YYYY-MM-DD
        price REAL NOT NULL,                -- preço unitário
        source TEXT,                        -- 'manual'
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(asset_id, date),
        FOREIGN KEY(asset_id) REFERENCES assets(id)
);
""")

    cur.execute("CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(date);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_prices_date ON prices(date);")

    conn.commit()
    conn.close()