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
    raw = sqlite3.connect(SQLITE_PATH, check_same_thread=False, timeout=30.0)
    # Reduce SQLITE_BUSY / "database is locked" on concurrent local usage
    # (API + frontend actions, dev reloads, etc.).
    raw.execute("PRAGMA journal_mode=WAL;")
    raw.execute("PRAGMA busy_timeout=30000;")
    raw.execute("PRAGMA synchronous=NORMAL;")
    raw.row_factory = sqlite3.Row
    return DBConn(raw, use_postgres=False)


def _sqlite_schema(cur):
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        display_name TEXT,
        role TEXT NOT NULL DEFAULT 'user',
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS invites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        token TEXT NOT NULL UNIQUE,
        invited_email TEXT,
        created_by INTEGER NOT NULL,
        used_by INTEGER,
        expires_at TEXT NOT NULL,
        used_at TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        type TEXT NOT NULL DEFAULT 'Banco',
        currency TEXT NOT NULL DEFAULT 'BRL',
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
    CREATE TABLE IF NOT EXISTS credit_cards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        brand TEXT NOT NULL DEFAULT 'Visa',
        model TEXT NOT NULL DEFAULT 'Black',
        card_type TEXT NOT NULL DEFAULT 'Credito',
        card_account_id INTEGER NOT NULL,
        source_account_id INTEGER NOT NULL,
        due_day INTEGER NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        user_id INTEGER,
        FOREIGN KEY(card_account_id) REFERENCES accounts(id),
        FOREIGN KEY(source_account_id) REFERENCES accounts(id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS credit_card_invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        card_id INTEGER NOT NULL,
        invoice_period TEXT NOT NULL,
        due_date TEXT NOT NULL,
        total_amount REAL NOT NULL DEFAULT 0,
        paid_amount REAL NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'OPEN',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        user_id INTEGER,
        FOREIGN KEY(card_id) REFERENCES credit_cards(id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS credit_card_charges (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        card_id INTEGER NOT NULL,
        purchase_date TEXT NOT NULL,
        amount REAL NOT NULL,
        category_id INTEGER,
        description TEXT,
        invoice_period TEXT NOT NULL,
        due_date TEXT NOT NULL,
        paid INTEGER NOT NULL DEFAULT 0,
        note TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        user_id INTEGER,
        FOREIGN KEY(card_id) REFERENCES credit_cards(id),
        FOREIGN KEY(category_id) REFERENCES categories(id)
    );
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_cc_cards_user ON credit_cards(user_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cc_cards_user_acc_type ON credit_cards(user_id, card_account_id, card_type);")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_cc_cards_user_name_type_acc ON credit_cards(user_id, name, card_type, card_account_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cc_inv_user ON credit_card_invoices(user_id);")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_cc_inv_user_period ON credit_card_invoices(user_id, card_id, invoice_period);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cc_chg_user ON credit_card_charges(user_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cc_chg_period ON credit_card_charges(user_id, card_id, invoice_period);")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS assets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        asset_class TEXT NOT NULL,
        sector TEXT,
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
        exchange_rate REAL NOT NULL DEFAULT 1,
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
    CREATE TABLE IF NOT EXISTS users (
        id BIGSERIAL PRIMARY KEY,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        display_name TEXT,
        role TEXT NOT NULL DEFAULT 'user',
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        created_at TIMESTAMP NOT NULL DEFAULT NOW()
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS invites (
        id BIGSERIAL PRIMARY KEY,
        token TEXT NOT NULL UNIQUE,
        invited_email TEXT,
        created_by BIGINT NOT NULL,
        used_by BIGINT,
        expires_at TIMESTAMP NOT NULL,
        used_at TIMESTAMP,
        created_at TIMESTAMP NOT NULL DEFAULT NOW()
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        id BIGSERIAL PRIMARY KEY,
        name TEXT NOT NULL UNIQUE,
        type TEXT NOT NULL DEFAULT 'Banco',
        currency TEXT NOT NULL DEFAULT 'BRL',
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
    CREATE TABLE IF NOT EXISTS credit_cards (
        id BIGSERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        brand TEXT NOT NULL DEFAULT 'Visa',
        model TEXT NOT NULL DEFAULT 'Black',
        card_type TEXT NOT NULL DEFAULT 'Credito',
        card_account_id BIGINT NOT NULL,
        source_account_id BIGINT NOT NULL,
        due_day INTEGER NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        user_id BIGINT,
        CONSTRAINT fk_cc_card_account FOREIGN KEY (card_account_id) REFERENCES accounts(id),
        CONSTRAINT fk_cc_source_account FOREIGN KEY (source_account_id) REFERENCES accounts(id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS credit_card_invoices (
        id BIGSERIAL PRIMARY KEY,
        card_id BIGINT NOT NULL,
        invoice_period TEXT NOT NULL,
        due_date TEXT NOT NULL,
        total_amount DOUBLE PRECISION NOT NULL DEFAULT 0,
        paid_amount DOUBLE PRECISION NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'OPEN',
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        user_id BIGINT,
        CONSTRAINT fk_cc_inv_card FOREIGN KEY (card_id) REFERENCES credit_cards(id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS credit_card_charges (
        id BIGSERIAL PRIMARY KEY,
        card_id BIGINT NOT NULL,
        purchase_date TEXT NOT NULL,
        amount DOUBLE PRECISION NOT NULL,
        category_id BIGINT,
        description TEXT,
        invoice_period TEXT NOT NULL,
        due_date TEXT NOT NULL,
        paid BOOLEAN NOT NULL DEFAULT FALSE,
        note TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        user_id BIGINT,
        CONSTRAINT fk_cc_chg_card FOREIGN KEY (card_id) REFERENCES credit_cards(id),
        CONSTRAINT fk_cc_chg_category FOREIGN KEY (category_id) REFERENCES categories(id)
    );
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_cc_cards_user ON credit_cards(user_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cc_cards_user_acc_type ON credit_cards(user_id, card_account_id, card_type);")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_cc_cards_user_name_type_acc ON credit_cards(user_id, name, card_type, card_account_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cc_inv_user ON credit_card_invoices(user_id);")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_cc_inv_user_period ON credit_card_invoices(user_id, card_id, invoice_period);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cc_chg_user ON credit_card_charges(user_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cc_chg_period ON credit_card_charges(user_id, card_id, invoice_period);")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS assets (
        id BIGSERIAL PRIMARY KEY,
        symbol TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        asset_class TEXT NOT NULL,
        sector TEXT,
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
        exchange_rate DOUBLE PRECISION NOT NULL DEFAULT 1,
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


def _migrate_multitenant_postgres(cur):
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'user'")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE")

    cur.execute("ALTER TABLE accounts ADD COLUMN IF NOT EXISTS user_id BIGINT")
    cur.execute("ALTER TABLE accounts ADD COLUMN IF NOT EXISTS currency TEXT NOT NULL DEFAULT 'BRL'")
    cur.execute("ALTER TABLE categories ADD COLUMN IF NOT EXISTS user_id BIGINT")
    cur.execute("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS user_id BIGINT")
    cur.execute("ALTER TABLE assets ADD COLUMN IF NOT EXISTS user_id BIGINT")
    cur.execute("ALTER TABLE assets ADD COLUMN IF NOT EXISTS sector TEXT")
    cur.execute("ALTER TABLE trades ADD COLUMN IF NOT EXISTS user_id BIGINT")
    cur.execute("ALTER TABLE trades ADD COLUMN IF NOT EXISTS exchange_rate DOUBLE PRECISION NOT NULL DEFAULT 1")
    cur.execute("ALTER TABLE income_events ADD COLUMN IF NOT EXISTS user_id BIGINT")
    cur.execute("ALTER TABLE prices ADD COLUMN IF NOT EXISTS user_id BIGINT")
    cur.execute("ALTER TABLE asset_prices ADD COLUMN IF NOT EXISTS user_id BIGINT")
    cur.execute("ALTER TABLE credit_cards ADD COLUMN IF NOT EXISTS user_id BIGINT")
    cur.execute("ALTER TABLE credit_cards ADD COLUMN IF NOT EXISTS brand TEXT NOT NULL DEFAULT 'Visa'")
    cur.execute("ALTER TABLE credit_cards ADD COLUMN IF NOT EXISTS model TEXT NOT NULL DEFAULT 'Black'")
    cur.execute("ALTER TABLE credit_cards ADD COLUMN IF NOT EXISTS card_type TEXT NOT NULL DEFAULT 'Credito'")
    cur.execute("ALTER TABLE credit_card_invoices ADD COLUMN IF NOT EXISTS user_id BIGINT")
    cur.execute("ALTER TABLE credit_card_charges ADD COLUMN IF NOT EXISTS user_id BIGINT")
    cur.execute("ALTER TABLE credit_card_charges ADD COLUMN IF NOT EXISTS category_id BIGINT")
    cur.execute("ALTER TABLE credit_card_charges ADD COLUMN IF NOT EXISTS description TEXT")

    cur.execute("ALTER TABLE accounts DROP CONSTRAINT IF EXISTS accounts_name_key")
    cur.execute("ALTER TABLE categories DROP CONSTRAINT IF EXISTS categories_name_key")
    cur.execute("ALTER TABLE assets DROP CONSTRAINT IF EXISTS assets_symbol_key")

    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_accounts_user_name ON accounts(user_id, name)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_categories_user_name ON categories(user_id, name)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_assets_user_symbol ON assets(user_id, symbol)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_prices_user_asset_date ON prices(user_id, asset_id, date)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_asset_prices_user_asset_date ON asset_prices(user_id, asset_id, px_date)")

    cur.execute("CREATE INDEX IF NOT EXISTS idx_accounts_user ON accounts(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_categories_user ON categories(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_user ON transactions(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_assets_user ON assets(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_trades_user ON trades(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_income_user ON income_events(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_prices_user ON prices(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cc_cards_user ON credit_cards(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cc_inv_user ON credit_card_invoices(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cc_chg_user ON credit_card_charges(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_invites_created_by ON invites(created_by)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_invites_expires_at ON invites(expires_at)")
    cur.execute("DROP INDEX IF EXISTS ux_cc_cards_user_acc")
    cur.execute("DROP INDEX IF EXISTS ux_cc_cards_user_name")
    cur.execute("DROP INDEX IF EXISTS ux_cc_cards_user_acc_type")
    cur.execute("DROP INDEX IF EXISTS ux_cc_cards_user_name_type")
    cur.execute("DROP INDEX IF EXISTS ux_cc_cards_user_name_type_acc")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cc_cards_user_acc_type ON credit_cards(user_id, card_account_id, card_type)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_cc_cards_user_name_type_acc ON credit_cards(user_id, name, card_type, card_account_id)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_cc_inv_user_period ON credit_card_invoices(user_id, card_id, invoice_period)")


def _add_column_sqlite(cur, table: str, column_def: str):
    col_name = column_def.split()[0]
    cols = cur.execute(f"PRAGMA table_info({table})").fetchall()
    existing = {c[1] for c in cols}
    if col_name not in existing:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")


def _migrate_multitenant_sqlite(cur):
    _add_column_sqlite(cur, "users", "role TEXT NOT NULL DEFAULT 'user'")
    _add_column_sqlite(cur, "users", "is_active INTEGER NOT NULL DEFAULT 1")

    _add_column_sqlite(cur, "accounts", "user_id INTEGER")
    _add_column_sqlite(cur, "accounts", "currency TEXT NOT NULL DEFAULT 'BRL'")
    _add_column_sqlite(cur, "categories", "user_id INTEGER")
    _add_column_sqlite(cur, "transactions", "user_id INTEGER")
    _add_column_sqlite(cur, "assets", "user_id INTEGER")
    _add_column_sqlite(cur, "assets", "sector TEXT")
    _add_column_sqlite(cur, "trades", "user_id INTEGER")
    _add_column_sqlite(cur, "trades", "exchange_rate REAL NOT NULL DEFAULT 1")
    _add_column_sqlite(cur, "income_events", "user_id INTEGER")
    _add_column_sqlite(cur, "prices", "user_id INTEGER")
    _add_column_sqlite(cur, "asset_prices", "user_id INTEGER")
    _add_column_sqlite(cur, "credit_cards", "user_id INTEGER")
    _add_column_sqlite(cur, "credit_cards", "brand TEXT NOT NULL DEFAULT 'Visa'")
    _add_column_sqlite(cur, "credit_cards", "model TEXT NOT NULL DEFAULT 'Black'")
    _add_column_sqlite(cur, "credit_cards", "card_type TEXT NOT NULL DEFAULT 'Credito'")
    _add_column_sqlite(cur, "credit_card_invoices", "user_id INTEGER")
    _add_column_sqlite(cur, "credit_card_charges", "user_id INTEGER")
    _add_column_sqlite(cur, "credit_card_charges", "category_id INTEGER")
    _add_column_sqlite(cur, "credit_card_charges", "description TEXT")

    cur.execute("CREATE INDEX IF NOT EXISTS idx_accounts_user ON accounts(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_categories_user ON categories(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_user ON transactions(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_assets_user ON assets(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_trades_user ON trades(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_income_user ON income_events(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_prices_user ON prices(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cc_cards_user ON credit_cards(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cc_inv_user ON credit_card_invoices(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cc_chg_user ON credit_card_charges(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_invites_created_by ON invites(created_by)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_invites_expires_at ON invites(expires_at)")
    _rebuild_sqlite_unique_tables(cur)
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_accounts_user_name ON accounts(user_id, name)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_categories_user_name ON categories(user_id, name)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_assets_user_symbol ON assets(user_id, symbol)")
    cur.execute("DROP INDEX IF EXISTS ux_cc_cards_user_acc")
    cur.execute("DROP INDEX IF EXISTS ux_cc_cards_user_name")
    cur.execute("DROP INDEX IF EXISTS ux_cc_cards_user_acc_type")
    cur.execute("DROP INDEX IF EXISTS ux_cc_cards_user_name_type")
    cur.execute("DROP INDEX IF EXISTS ux_cc_cards_user_name_type_acc")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cc_cards_user_acc_type ON credit_cards(user_id, card_account_id, card_type)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_cc_cards_user_name_type_acc ON credit_cards(user_id, name, card_type, card_account_id)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_cc_inv_user_period ON credit_card_invoices(user_id, card_id, invoice_period)")


def _table_sql(cur, table: str) -> str:
    row = cur.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    if not row:
        return ""
    return row[0] if isinstance(row, tuple) else row["sql"]


def _rebuild_sqlite_unique_tables(cur):
    accounts_sql = _table_sql(cur, "accounts").upper()
    categories_sql = _table_sql(cur, "categories").upper()
    assets_sql = _table_sql(cur, "assets").upper()

    need_accounts = "NAME TEXT NOT NULL UNIQUE" in accounts_sql
    need_categories = "NAME TEXT NOT NULL UNIQUE" in categories_sql
    need_assets = "SYMBOL TEXT NOT NULL UNIQUE" in assets_sql

    if not (need_accounts or need_categories or need_assets):
        return

    cur.execute("PRAGMA foreign_keys=OFF")

    if need_accounts:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS accounts_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT NOT NULL DEFAULT 'Banco',
            currency TEXT NOT NULL DEFAULT 'BRL',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            user_id INTEGER
        );
        """)
        cur.execute("""
        INSERT INTO accounts_new(id, name, type, currency, created_at, user_id)
        SELECT id, name, type, COALESCE(currency, 'BRL'), created_at, user_id
        FROM accounts
        """)
        cur.execute("DROP TABLE accounts")
        cur.execute("ALTER TABLE accounts_new RENAME TO accounts")

    if need_categories:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS categories_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            kind TEXT NOT NULL DEFAULT 'Despesa',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            user_id INTEGER
        );
        """)
        cur.execute("""
        INSERT INTO categories_new(id, name, kind, created_at, user_id)
        SELECT id, name, kind, created_at, user_id
        FROM categories
        """)
        cur.execute("DROP TABLE categories")
        cur.execute("ALTER TABLE categories_new RENAME TO categories")

    if need_assets:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS assets_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            name TEXT NOT NULL,
            asset_class TEXT NOT NULL,
            sector TEXT,
            currency TEXT NOT NULL DEFAULT 'BRL',
            broker_account_id INTEGER,
            source_account_id INTEGER,
            issuer TEXT,
            rate_type TEXT,
            rate_value REAL,
            maturity_date TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            user_id INTEGER,
            FOREIGN KEY(broker_account_id) REFERENCES accounts(id)
        );
        """)
        cur.execute("""
        INSERT INTO assets_new(
            id, symbol, name, asset_class, sector, currency,
            broker_account_id, source_account_id, issuer, rate_type, rate_value, maturity_date, created_at, user_id
        )
        SELECT
            id, symbol, name, asset_class, sector, currency,
            broker_account_id, source_account_id, issuer, rate_type, rate_value, maturity_date, created_at, user_id
        FROM assets
        """)
        cur.execute("DROP TABLE assets")
        cur.execute("ALTER TABLE assets_new RENAME TO assets")

    cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_date ON transactions(date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_account ON transactions(account_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_category ON transactions(category_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_trades_date ON trades(date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_prices_date ON prices(date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_accounts_user ON accounts(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_categories_user ON categories(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_assets_user ON assets(user_id)")
    cur.execute("PRAGMA foreign_keys=ON")


def init_db() -> None:
    with get_conn() as conn:
        cur = conn.cursor()
        if USE_POSTGRES:
            _postgres_schema(cur)
            _migrate_multitenant_postgres(cur)
        else:
            _sqlite_schema(cur)
            _migrate_multitenant_sqlite(cur)
