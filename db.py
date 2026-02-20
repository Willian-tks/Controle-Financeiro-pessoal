import os
import re
import sqlite3
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
SQLITE_PATH = BASE_DIR / "data" / "finance.db"

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
USE_POSTGRES = DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith("postgresql://")
DB_PATH = DATABASE_URL if USE_POSTGRES else SQLITE_PATH


class DBCursor:
    def __init__(self, cursor, use_postgres: bool):
        self._cursor = cursor
        self._use_postgres = use_postgres

    def execute(self, query: str, params: tuple | list | None = None):
        q = _adapt_query(query, self._use_postgres)
        self._cursor.execute(q, tuple(params or ()))
        return self

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    @property
    def rowcount(self):
        return self._cursor.rowcount


class DBConn:
    def __init__(self, conn, use_postgres: bool):
        self._conn = conn
        self._use_postgres = use_postgres

    def execute(self, query: str, params: tuple | list | None = None):
        q = _adapt_query(query, self._use_postgres)
        return self._conn.execute(q, tuple(params or ()))

    def cursor(self):
        return DBCursor(self._conn.cursor(), self._use_postgres)

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.rollback()
        else:
            self.commit()
        self.close()
        return False


def _adapt_query(query: str, use_postgres: bool) -> str:
    if not use_postgres:
        return query

    q = query

    # SQLite -> Postgres compatibility for "INSERT OR IGNORE"
    if re.match(r"^\s*INSERT\s+OR\s+IGNORE\s+INTO\s+", q, re.IGNORECASE):
        q = re.sub(r"^\s*INSERT\s+OR\s+IGNORE\s+INTO\s+", "INSERT INTO ", q, flags=re.IGNORECASE)
        if "ON CONFLICT" not in q.upper():
            q = q.rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"

    # sqlite qmark style -> psycopg format style
    q = q.replace("?", "%s")
    return q


def get_conn() -> DBConn:
    if USE_POSTGRES:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as e:
            raise RuntimeError(
                "PostgreSQL habilitado via DATABASE_URL, mas psycopg não está instalado."
            ) from e

        raw = psycopg.connect(DATABASE_URL, row_factory=dict_row)
        return DBConn(raw, use_postgres=True)

    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    raw = sqlite3.connect(SQLITE_PATH, check_same_thread=False)
    raw.row_factory = sqlite3.Row
    return DBConn(raw, use_postgres=False)


def _sqlite_schema(cur):
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
        amount_brl REAL NOT NULL,
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

    cur.execute("""
    CREATE TABLE IF NOT EXISTS assets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        asset_class TEXT NOT NULL,
        currency TEXT NOT NULL DEFAULT 'BRL',
        broker_account_id INTEGER,
        source_account_id INTEGER,
        issuer TEXT,
        rate_type TEXT,
        rate_value REAL,
        maturity_date TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY(broker_account_id) REFERENCES accounts(id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS asset_prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        asset_id INTEGER NOT NULL,
        px_date TEXT NOT NULL,
        price REAL NOT NULL,
        source TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(asset_id, px_date)
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
        date TEXT NOT NULL,
        price REAL NOT NULL,
        source TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(asset_id, date),
        FOREIGN KEY(asset_id) REFERENCES assets(id)
    );
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(date);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_prices_date ON prices(date);")


def _postgres_schema(cur):
    cur.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        id BIGSERIAL PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        type TEXT NOT NULL DEFAULT 'Banco',
        created_at TIMESTAMP NOT NULL DEFAULT NOW()
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id BIGSERIAL PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        kind TEXT NOT NULL DEFAULT 'Despesa',
        created_at TIMESTAMP NOT NULL DEFAULT NOW()
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id BIGSERIAL PRIMARY KEY,
        date TEXT NOT NULL,
        description TEXT NOT NULL,
        amount_brl DOUBLE PRECISION NOT NULL,
        category_id BIGINT,
        account_id BIGINT NOT NULL,
        method TEXT,
        notes TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        CONSTRAINT fk_tx_category FOREIGN KEY (category_id) REFERENCES categories(id),
        CONSTRAINT fk_tx_account FOREIGN KEY (account_id) REFERENCES accounts(id)
    );
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_date ON transactions(date);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_account ON transactions(account_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_category ON transactions(category_id);")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS assets (
        id BIGSERIAL PRIMARY KEY,
        symbol TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        asset_class TEXT NOT NULL,
        currency TEXT NOT NULL DEFAULT 'BRL',
        broker_account_id BIGINT,
        source_account_id BIGINT,
        issuer TEXT,
        rate_type TEXT,
        rate_value DOUBLE PRECISION,
        maturity_date TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        CONSTRAINT fk_assets_broker FOREIGN KEY (broker_account_id) REFERENCES accounts(id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS asset_prices (
        id BIGSERIAL PRIMARY KEY,
        asset_id BIGINT NOT NULL,
        px_date TEXT NOT NULL,
        price DOUBLE PRECISION NOT NULL,
        source TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        UNIQUE(asset_id, px_date)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS trades (
        id BIGSERIAL PRIMARY KEY,
        asset_id BIGINT NOT NULL,
        date TEXT NOT NULL,
        side TEXT NOT NULL,
        quantity DOUBLE PRECISION NOT NULL,
        price DOUBLE PRECISION NOT NULL,
        fees DOUBLE PRECISION NOT NULL DEFAULT 0,
        taxes DOUBLE PRECISION NOT NULL DEFAULT 0,
        note TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        CONSTRAINT fk_trades_asset FOREIGN KEY (asset_id) REFERENCES assets(id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS income_events (
        id BIGSERIAL PRIMARY KEY,
        asset_id BIGINT NOT NULL,
        date TEXT NOT NULL,
        type TEXT NOT NULL,
        amount DOUBLE PRECISION NOT NULL,
        note TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        CONSTRAINT fk_income_asset FOREIGN KEY (asset_id) REFERENCES assets(id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS prices (
        id BIGSERIAL PRIMARY KEY,
        asset_id BIGINT NOT NULL,
        date TEXT NOT NULL,
        price DOUBLE PRECISION NOT NULL,
        source TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        UNIQUE(asset_id, date),
        CONSTRAINT fk_prices_asset FOREIGN KEY (asset_id) REFERENCES assets(id)
    );
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(date);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_prices_date ON prices(date);")


def init_db() -> None:
    with get_conn() as conn:
        cur = conn.cursor()
        if USE_POSTGRES:
            _postgres_schema(cur)
        else:
            _sqlite_schema(cur)
