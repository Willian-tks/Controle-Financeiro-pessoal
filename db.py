import os
import re
import sqlite3
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
SQLITE_PATH = BASE_DIR / "data" / "finance.db"

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
FORCE_SQLITE = str(os.getenv("LOCAL_DEV_FORCE_SQLITE", "")).strip().lower() in {"1", "true", "yes", "on"}
USE_POSTGRES = (not FORCE_SQLITE) and (
    DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith("postgresql://")
)
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
        token_version INTEGER NOT NULL DEFAULT 0,
        password_changed_at TEXT,
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
    CREATE TABLE IF NOT EXISTS password_reset_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        token_hash TEXT NOT NULL UNIQUE,
        expires_at TEXT NOT NULL,
        requested_ip TEXT,
        requested_user_agent TEXT,
        consumed_ip TEXT,
        consumed_user_agent TEXT,
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
        show_on_dashboard INTEGER NOT NULL DEFAULT 0,
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
        recurrence_id TEXT,
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
        close_day INTEGER,
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
        rentability_type TEXT,
        index_name TEXT,
        index_pct REAL,
        spread_rate REAL,
        fixed_rate REAL,
        principal_amount REAL,
        current_value REAL,
        fair_price REAL,
        safety_margin_pct REAL,
        user_objective TEXT,
        last_update TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY(broker_account_id) REFERENCES accounts(id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS index_rates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        index_name TEXT NOT NULL,
        ref_date TEXT NOT NULL,
        value REAL NOT NULL,
        source TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        user_id INTEGER
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS benchmark_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        index_name TEXT NOT NULL,
        display_name TEXT,
        provider TEXT,
        symbol TEXT,
        is_active INTEGER NOT NULL DEFAULT 1,
        update_at_midday INTEGER NOT NULL DEFAULT 1,
        update_at_close INTEGER NOT NULL DEFAULT 1,
        default_asset_class TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        user_id INTEGER,
        workspace_id INTEGER
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS lists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workspace_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        description TEXT,
        status TEXT NOT NULL DEFAULT 'ativa',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS list_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workspace_id INTEGER NOT NULL,
        list_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        quantity REAL NOT NULL,
        unit TEXT NOT NULL DEFAULT 'un',
        suggested_value REAL NOT NULL DEFAULT 0,
        total_value REAL NOT NULL DEFAULT 0,
        acquired INTEGER NOT NULL DEFAULT 0,
        completion_date TEXT,
        notes TEXT,
        sort_order INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY(list_id) REFERENCES lists(id)
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
    CREATE TABLE IF NOT EXISTS asset_valuation_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        asset_id INTEGER NOT NULL,
        file_name TEXT NOT NULL,
        content_type TEXT NOT NULL DEFAULT 'application/pdf',
        file_data BLOB NOT NULL,
        uploaded_at TEXT NOT NULL DEFAULT (datetime('now')),
        user_id INTEGER,
        workspace_id INTEGER,
        UNIQUE(asset_id, user_id),
        FOREIGN KEY(asset_id) REFERENCES assets(id)
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
        credit_account_id INTEGER,
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
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_index_rates_name_date ON index_rates(index_name, ref_date);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_index_rates_ref_date ON index_rates(ref_date);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_lists_workspace ON lists(workspace_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_lists_workspace_status ON lists(workspace_id, status);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_lists_workspace_type ON lists(workspace_id, type);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_list_items_workspace ON list_items(workspace_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_list_items_workspace_list ON list_items(workspace_id, list_id);")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS quote_job_status (
        workspace_id INTEGER PRIMARY KEY,
        last_started_at TEXT,
        last_finished_at TEXT,
        last_status TEXT,
        last_reason TEXT,
        last_saved_total INTEGER NOT NULL DEFAULT 0,
        last_total INTEGER NOT NULL DEFAULT 0,
        last_error_total INTEGER NOT NULL DEFAULT 0,
        last_run_scope TEXT,
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """)


def _postgres_schema(cur):
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id BIGSERIAL PRIMARY KEY,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        display_name TEXT,
        role TEXT NOT NULL DEFAULT 'user',
        token_version INTEGER NOT NULL DEFAULT 0,
        password_changed_at TIMESTAMP,
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
    CREATE TABLE IF NOT EXISTS password_reset_tokens (
        id BIGSERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        token_hash TEXT NOT NULL UNIQUE,
        expires_at TIMESTAMP NOT NULL,
        requested_ip TEXT,
        requested_user_agent TEXT,
        consumed_ip TEXT,
        consumed_user_agent TEXT,
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
        show_on_dashboard BOOLEAN NOT NULL DEFAULT FALSE,
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
        recurrence_id TEXT,
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
        close_day INTEGER,
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
        rentability_type TEXT,
        index_name TEXT,
        index_pct DOUBLE PRECISION,
        spread_rate DOUBLE PRECISION,
        fixed_rate DOUBLE PRECISION,
        principal_amount DOUBLE PRECISION,
        current_value DOUBLE PRECISION,
        fair_price DOUBLE PRECISION,
        safety_margin_pct DOUBLE PRECISION,
        user_objective TEXT,
        last_update TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        CONSTRAINT fk_assets_broker FOREIGN KEY (broker_account_id) REFERENCES accounts(id)
    );
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS index_rates (
        id BIGSERIAL PRIMARY KEY,
        index_name TEXT NOT NULL,
        ref_date TEXT NOT NULL,
        value DOUBLE PRECISION NOT NULL,
        source TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
        user_id BIGINT
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS benchmark_settings (
        id BIGSERIAL PRIMARY KEY,
        index_name TEXT NOT NULL,
        display_name TEXT,
        provider TEXT,
        symbol TEXT,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        update_at_midday BOOLEAN NOT NULL DEFAULT TRUE,
        update_at_close BOOLEAN NOT NULL DEFAULT TRUE,
        default_asset_class TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
        user_id BIGINT,
        workspace_id BIGINT
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS lists (
        id BIGSERIAL PRIMARY KEY,
        workspace_id BIGINT NOT NULL,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        description TEXT,
        status TEXT NOT NULL DEFAULT 'ativa',
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS list_items (
        id BIGSERIAL PRIMARY KEY,
        workspace_id BIGINT NOT NULL,
        list_id BIGINT NOT NULL,
        name TEXT NOT NULL,
        quantity DOUBLE PRECISION NOT NULL,
        unit TEXT NOT NULL DEFAULT 'un',
        suggested_value DOUBLE PRECISION NOT NULL DEFAULT 0,
        total_value DOUBLE PRECISION NOT NULL DEFAULT 0,
        acquired BOOLEAN NOT NULL DEFAULT FALSE,
        completion_date TEXT,
        notes TEXT,
        sort_order INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
        CONSTRAINT fk_list_items_list FOREIGN KEY (list_id) REFERENCES lists(id)
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sync_runs (
        id BIGSERIAL PRIMARY KEY,
        scope_kind TEXT NOT NULL,
        scope_id BIGINT NOT NULL,
        sync_type TEXT NOT NULL,
        sync_key TEXT NOT NULL,
        ref_date TEXT NOT NULL,
        created_at TIMESTAMP NOT NULL DEFAULT NOW()
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
    CREATE TABLE IF NOT EXISTS asset_valuation_reports (
        id BIGSERIAL PRIMARY KEY,
        asset_id BIGINT NOT NULL,
        file_name TEXT NOT NULL,
        content_type TEXT NOT NULL DEFAULT 'application/pdf',
        file_data BYTEA NOT NULL,
        uploaded_at TIMESTAMP NOT NULL DEFAULT NOW(),
        user_id BIGINT,
        workspace_id BIGINT,
        UNIQUE(asset_id, user_id),
        CONSTRAINT fk_asset_valuation_reports_asset FOREIGN KEY (asset_id) REFERENCES assets(id)
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
        credit_account_id BIGINT,
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
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_index_rates_name_date ON index_rates(index_name, ref_date);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_index_rates_ref_date ON index_rates(ref_date);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_lists_workspace ON lists(workspace_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_lists_workspace_status ON lists(workspace_id, status);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_lists_workspace_type ON lists(workspace_id, type);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_list_items_workspace ON list_items(workspace_id);")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_list_items_workspace_list ON list_items(workspace_id, list_id);")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS quote_job_status (
        workspace_id BIGINT PRIMARY KEY,
        last_started_at TEXT,
        last_finished_at TEXT,
        last_status TEXT,
        last_reason TEXT,
        last_saved_total INTEGER NOT NULL DEFAULT 0,
        last_total INTEGER NOT NULL DEFAULT 0,
        last_error_total INTEGER NOT NULL DEFAULT 0,
        last_run_scope TEXT,
        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
    );
    """)


def _row_value(row: Any, key: str, default: Any = None) -> Any:
    if row is None:
        return default
    try:
        return row[key]
    except Exception:
        try:
            return row.get(key, default)  # type: ignore[attr-defined]
        except Exception:
            return default


def _workspace_default_name(email: str | None, user_id: int) -> str:
    base = (str(email or "").strip().split("@", 1)[0] or "").strip()
    if not base:
        base = f"Usuario {int(user_id)}"
    return f"Workspace {base}"


def _backfill_multiworkspace_phase1(cur) -> None:
    user_rows = cur.execute(
        """
        SELECT id, email
        FROM users
        ORDER BY id
        """
    ).fetchall()
    if not user_rows:
        return

    owner_workspace_by_user: dict[int, int] = {}
    for u in user_rows:
        uid = int(_row_value(u, "id", 0) or 0)
        if uid <= 0:
            continue
        email = str(_row_value(u, "email", "") or "")

        # If the user already belongs to any workspace, do not auto-create
        # a private owner workspace during backfill. This preserves guest-only
        # users and avoids recreating deleted personal workspaces on startup.
        membership_row = cur.execute(
            """
            SELECT workspace_id, role
            FROM workspace_users
            WHERE user_id = ?
            ORDER BY id
            LIMIT 1
            """,
            (uid,),
        ).fetchone()
        if membership_row:
            existing_ws_id = int(_row_value(membership_row, "workspace_id", 0) or 0)
            if existing_ws_id > 0:
                owner_workspace_by_user[uid] = existing_ws_id
                continue

        ws_row = cur.execute(
            """
            SELECT w.id
            FROM workspaces w
            JOIN workspace_users wu ON wu.workspace_id = w.id
            WHERE wu.user_id = ?
              AND UPPER(COALESCE(wu.role, '')) = 'OWNER'
            ORDER BY w.id
            LIMIT 1
            """,
            (uid,),
        ).fetchone()
        ws_id = int(_row_value(ws_row, "id", 0) or 0)

        if ws_id <= 0:
            ws_row = cur.execute(
                """
                SELECT id
                FROM workspaces
                WHERE owner_user_id = ?
                ORDER BY id
                LIMIT 1
                """,
                (uid,),
            ).fetchone()
            ws_id = int(_row_value(ws_row, "id", 0) or 0)

        if ws_id <= 0:
            cur.execute(
                """
                INSERT INTO workspaces(name, owner_user_id, status)
                VALUES (?, ?, 'active')
                """,
                (_workspace_default_name(email, uid), uid),
            )
            ws_row = cur.execute(
                """
                SELECT id
                FROM workspaces
                WHERE owner_user_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (uid,),
            ).fetchone()
            ws_id = int(_row_value(ws_row, "id", 0) or 0)

        if ws_id <= 0:
            continue

        cur.execute(
            """
            INSERT OR IGNORE INTO workspace_users(workspace_id, user_id, role, created_by)
            VALUES (?, ?, 'OWNER', ?)
            """,
            (ws_id, uid, uid),
        )
        cur.execute(
            """
            UPDATE workspace_users
            SET role = 'OWNER'
            WHERE workspace_id = ? AND user_id = ?
            """,
            (ws_id, uid),
        )
        owner_workspace_by_user[uid] = ws_id

    if not owner_workspace_by_user:
        return

    domain_tables = [
        "accounts",
        "categories",
        "transactions",
        "assets",
        "trades",
        "income_events",
        "prices",
        "asset_prices",
        "credit_cards",
        "credit_card_invoices",
        "credit_card_charges",
        "index_rates",
    ]
    for table in domain_tables:
        for uid, ws_id in owner_workspace_by_user.items():
            cur.execute(
                f"UPDATE {table} SET workspace_id = ? WHERE workspace_id IS NULL AND user_id = ?",
                (ws_id, uid),
            )

    fallback_ws = min(owner_workspace_by_user.values())
    for table in domain_tables:
        cur.execute(
            f"UPDATE {table} SET workspace_id = ? WHERE workspace_id IS NULL",
            (fallback_ws,),
        )


def _migrate_multitenant_postgres(cur):
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'user'")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS global_role TEXT")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS avatar_data TEXT")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 0")
    cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMP")
    cur.execute("""
    UPDATE users
    SET global_role = CASE
        WHEN LOWER(COALESCE(role, '')) = 'admin' THEN 'SUPER_ADMIN'
        ELSE 'USER'
    END
    WHERE global_role IS NULL OR TRIM(global_role) = ''
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS workspaces (
        id BIGSERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        owner_user_id BIGINT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMP NOT NULL DEFAULT NOW()
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS workspace_users (
        id BIGSERIAL PRIMARY KEY,
        workspace_id BIGINT NOT NULL,
        user_id BIGINT NOT NULL,
        role TEXT NOT NULL,
        created_by BIGINT,
        created_at TIMESTAMP NOT NULL DEFAULT NOW()
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS permissions (
        id BIGSERIAL PRIMARY KEY,
        workspace_user_id BIGINT NOT NULL,
        module TEXT NOT NULL,
        can_view BOOLEAN NOT NULL DEFAULT FALSE,
        can_add BOOLEAN NOT NULL DEFAULT FALSE,
        can_edit BOOLEAN NOT NULL DEFAULT FALSE,
        can_delete BOOLEAN NOT NULL DEFAULT FALSE
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS password_reset_tokens (
        id BIGSERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL,
        token_hash TEXT NOT NULL UNIQUE,
        expires_at TIMESTAMP NOT NULL,
        requested_ip TEXT,
        requested_user_agent TEXT,
        consumed_ip TEXT,
        consumed_user_agent TEXT,
        used_at TIMESTAMP,
        created_at TIMESTAMP NOT NULL DEFAULT NOW()
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS lists (
        id BIGSERIAL PRIMARY KEY,
        workspace_id BIGINT NOT NULL,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        description TEXT,
        status TEXT NOT NULL DEFAULT 'ativa',
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP NOT NULL DEFAULT NOW()
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS list_items (
        id BIGSERIAL PRIMARY KEY,
        workspace_id BIGINT NOT NULL,
        list_id BIGINT NOT NULL,
        name TEXT NOT NULL,
        quantity DOUBLE PRECISION NOT NULL,
        unit TEXT NOT NULL DEFAULT 'un',
        suggested_value DOUBLE PRECISION NOT NULL DEFAULT 0,
        total_value DOUBLE PRECISION NOT NULL DEFAULT 0,
        acquired BOOLEAN NOT NULL DEFAULT FALSE,
        completion_date TEXT,
        notes TEXT,
        sort_order INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
        CONSTRAINT fk_list_items_list FOREIGN KEY (list_id) REFERENCES lists(id)
    );
    """)

    cur.execute("ALTER TABLE accounts ADD COLUMN IF NOT EXISTS user_id BIGINT")
    cur.execute("ALTER TABLE accounts ADD COLUMN IF NOT EXISTS workspace_id BIGINT")
    cur.execute("ALTER TABLE accounts ADD COLUMN IF NOT EXISTS currency TEXT NOT NULL DEFAULT 'BRL'")
    cur.execute("ALTER TABLE accounts ADD COLUMN IF NOT EXISTS show_on_dashboard BOOLEAN NOT NULL DEFAULT FALSE")
    cur.execute("ALTER TABLE categories ADD COLUMN IF NOT EXISTS user_id BIGINT")
    cur.execute("ALTER TABLE categories ADD COLUMN IF NOT EXISTS workspace_id BIGINT")
    cur.execute("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS user_id BIGINT")
    cur.execute("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS workspace_id BIGINT")
    cur.execute("ALTER TABLE transactions ADD COLUMN IF NOT EXISTS recurrence_id TEXT")
    cur.execute("ALTER TABLE assets ADD COLUMN IF NOT EXISTS user_id BIGINT")
    cur.execute("ALTER TABLE assets ADD COLUMN IF NOT EXISTS workspace_id BIGINT")
    cur.execute("ALTER TABLE assets ADD COLUMN IF NOT EXISTS sector TEXT")
    cur.execute("ALTER TABLE assets ADD COLUMN IF NOT EXISTS source_account_id BIGINT")
    cur.execute("ALTER TABLE assets ADD COLUMN IF NOT EXISTS issuer TEXT")
    cur.execute("ALTER TABLE assets ADD COLUMN IF NOT EXISTS rate_type TEXT")
    cur.execute("ALTER TABLE assets ADD COLUMN IF NOT EXISTS rate_value DOUBLE PRECISION")
    cur.execute("ALTER TABLE assets ADD COLUMN IF NOT EXISTS maturity_date TEXT")
    cur.execute("ALTER TABLE assets ADD COLUMN IF NOT EXISTS rentability_type TEXT")
    cur.execute("ALTER TABLE assets ADD COLUMN IF NOT EXISTS index_name TEXT")
    cur.execute("ALTER TABLE assets ADD COLUMN IF NOT EXISTS index_pct DOUBLE PRECISION")
    cur.execute("ALTER TABLE assets ADD COLUMN IF NOT EXISTS spread_rate DOUBLE PRECISION")
    cur.execute("ALTER TABLE assets ADD COLUMN IF NOT EXISTS fixed_rate DOUBLE PRECISION")
    cur.execute("ALTER TABLE assets ADD COLUMN IF NOT EXISTS principal_amount DOUBLE PRECISION")
    cur.execute("ALTER TABLE assets ADD COLUMN IF NOT EXISTS current_value DOUBLE PRECISION")
    cur.execute("ALTER TABLE assets ADD COLUMN IF NOT EXISTS fair_price DOUBLE PRECISION")
    cur.execute("ALTER TABLE assets ADD COLUMN IF NOT EXISTS safety_margin_pct DOUBLE PRECISION")
    cur.execute("ALTER TABLE assets ADD COLUMN IF NOT EXISTS user_objective TEXT")
    cur.execute("ALTER TABLE assets ADD COLUMN IF NOT EXISTS last_update TEXT")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS asset_valuation_reports (
        id BIGSERIAL PRIMARY KEY,
        asset_id BIGINT NOT NULL,
        file_name TEXT NOT NULL,
        content_type TEXT NOT NULL DEFAULT 'application/pdf',
        file_data BYTEA NOT NULL,
        uploaded_at TIMESTAMP NOT NULL DEFAULT NOW(),
        user_id BIGINT,
        workspace_id BIGINT,
        UNIQUE(asset_id, user_id),
        CONSTRAINT fk_asset_valuation_reports_asset FOREIGN KEY (asset_id) REFERENCES assets(id)
    );
    """)
    cur.execute("ALTER TABLE trades ADD COLUMN IF NOT EXISTS user_id BIGINT")
    cur.execute("ALTER TABLE trades ADD COLUMN IF NOT EXISTS workspace_id BIGINT")
    cur.execute("ALTER TABLE trades ADD COLUMN IF NOT EXISTS exchange_rate DOUBLE PRECISION NOT NULL DEFAULT 1")
    cur.execute("ALTER TABLE income_events ADD COLUMN IF NOT EXISTS user_id BIGINT")
    cur.execute("ALTER TABLE income_events ADD COLUMN IF NOT EXISTS workspace_id BIGINT")
    cur.execute("ALTER TABLE income_events ADD COLUMN IF NOT EXISTS credit_account_id BIGINT")
    cur.execute("ALTER TABLE prices ADD COLUMN IF NOT EXISTS user_id BIGINT")
    cur.execute("ALTER TABLE prices ADD COLUMN IF NOT EXISTS workspace_id BIGINT")
    cur.execute("ALTER TABLE asset_prices ADD COLUMN IF NOT EXISTS user_id BIGINT")
    cur.execute("ALTER TABLE asset_prices ADD COLUMN IF NOT EXISTS workspace_id BIGINT")
    cur.execute("ALTER TABLE credit_cards ADD COLUMN IF NOT EXISTS user_id BIGINT")
    cur.execute("ALTER TABLE credit_cards ADD COLUMN IF NOT EXISTS workspace_id BIGINT")
    cur.execute("ALTER TABLE credit_cards ADD COLUMN IF NOT EXISTS brand TEXT NOT NULL DEFAULT 'Visa'")
    cur.execute("ALTER TABLE credit_cards ADD COLUMN IF NOT EXISTS model TEXT NOT NULL DEFAULT 'Black'")
    cur.execute("ALTER TABLE credit_cards ADD COLUMN IF NOT EXISTS card_type TEXT NOT NULL DEFAULT 'Credito'")
    cur.execute("ALTER TABLE credit_cards ADD COLUMN IF NOT EXISTS close_day INTEGER")
    cur.execute("ALTER TABLE credit_card_invoices ADD COLUMN IF NOT EXISTS user_id BIGINT")
    cur.execute("ALTER TABLE credit_card_invoices ADD COLUMN IF NOT EXISTS workspace_id BIGINT")
    cur.execute("ALTER TABLE credit_card_charges ADD COLUMN IF NOT EXISTS user_id BIGINT")
    cur.execute("ALTER TABLE credit_card_charges ADD COLUMN IF NOT EXISTS workspace_id BIGINT")
    cur.execute("ALTER TABLE credit_card_charges ADD COLUMN IF NOT EXISTS category_id BIGINT")
    cur.execute("ALTER TABLE credit_card_charges ADD COLUMN IF NOT EXISTS description TEXT")
    cur.execute("ALTER TABLE credit_card_charges ADD COLUMN IF NOT EXISTS note TEXT")
    cur.execute("ALTER TABLE list_items ADD COLUMN IF NOT EXISTS unit TEXT NOT NULL DEFAULT 'un'")
    cur.execute("UPDATE list_items SET unit = 'un' WHERE unit IS NULL OR TRIM(unit) = ''")
    cur.execute("ALTER TABLE index_rates ADD COLUMN IF NOT EXISTS workspace_id BIGINT")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS index_rates (
        id BIGSERIAL PRIMARY KEY,
        index_name TEXT NOT NULL,
        ref_date TEXT NOT NULL,
        value DOUBLE PRECISION NOT NULL,
        source TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
        user_id BIGINT
    );
    """)

    cur.execute("ALTER TABLE accounts DROP CONSTRAINT IF EXISTS accounts_name_key")
    cur.execute("ALTER TABLE categories DROP CONSTRAINT IF EXISTS categories_name_key")
    cur.execute("ALTER TABLE assets DROP CONSTRAINT IF EXISTS assets_symbol_key")

    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_accounts_user_name ON accounts(user_id, name)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_categories_user_name ON categories(user_id, name)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_assets_user_symbol ON assets(user_id, symbol)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_prices_user_asset_date ON prices(user_id, asset_id, date)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_asset_prices_user_asset_date ON asset_prices(user_id, asset_id, px_date)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_index_rates_name_date ON index_rates(index_name, ref_date)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_sync_runs_scope_type_key_date ON sync_runs(scope_kind, scope_id, sync_type, sync_key, ref_date)")

    cur.execute("CREATE INDEX IF NOT EXISTS idx_accounts_user ON accounts(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_categories_user ON categories(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tx_user ON transactions(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_assets_user ON assets(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_trades_user ON trades(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_income_user ON income_events(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_prices_user ON prices(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_index_rates_ref_date ON index_rates(ref_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cc_cards_user ON credit_cards(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cc_inv_user ON credit_card_invoices(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cc_chg_user ON credit_card_charges(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_invites_created_by ON invites(created_by)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_invites_expires_at ON invites(expires_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_user ON password_reset_tokens(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_expires_at ON password_reset_tokens(expires_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_used_at ON password_reset_tokens(used_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sync_runs_ref_date ON sync_runs(ref_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_workspaces_owner ON workspaces(owner_user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_workspaces_status ON workspaces(status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_workspace_users_workspace ON workspace_users(workspace_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_workspace_users_user ON workspace_users(user_id)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_workspace_users_workspace_user ON workspace_users(workspace_id, user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_permissions_workspace_user ON permissions(workspace_user_id)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_permissions_workspace_user_module ON permissions(workspace_user_id, module)")

    cur.execute("CREATE INDEX IF NOT EXISTS idx_accounts_workspace ON accounts(workspace_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_categories_workspace ON categories(workspace_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_transactions_workspace ON transactions(workspace_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_assets_workspace ON assets(workspace_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_trades_workspace ON trades(workspace_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_income_events_workspace ON income_events(workspace_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_prices_workspace ON prices(workspace_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_asset_prices_workspace ON asset_prices(workspace_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_credit_cards_workspace ON credit_cards(workspace_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_credit_card_invoices_workspace ON credit_card_invoices(workspace_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_credit_card_charges_workspace ON credit_card_charges(workspace_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_index_rates_workspace ON index_rates(workspace_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_benchmark_settings_workspace ON benchmark_settings(workspace_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_lists_workspace ON lists(workspace_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_lists_workspace_status ON lists(workspace_id, status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_lists_workspace_type ON lists(workspace_id, type)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_list_items_workspace ON list_items(workspace_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_list_items_workspace_list ON list_items(workspace_id, list_id)")

    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_accounts_workspace_name ON accounts(workspace_id, name)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_categories_workspace_name ON categories(workspace_id, name)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_assets_workspace_symbol ON assets(workspace_id, symbol)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_prices_workspace_asset_date ON prices(workspace_id, asset_id, date)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_asset_prices_workspace_asset_date ON asset_prices(workspace_id, asset_id, px_date)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_index_rates_workspace_name_date ON index_rates(workspace_id, index_name, ref_date)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_benchmark_settings_workspace_name ON benchmark_settings(workspace_id, index_name)")
    cur.execute("DROP INDEX IF EXISTS ux_cc_cards_user_acc")
    cur.execute("DROP INDEX IF EXISTS ux_cc_cards_user_name")
    cur.execute("DROP INDEX IF EXISTS ux_cc_cards_user_acc_type")
    cur.execute("DROP INDEX IF EXISTS ux_cc_cards_user_name_type")
    cur.execute("DROP INDEX IF EXISTS ux_cc_cards_user_name_type_acc")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cc_cards_user_acc_type ON credit_cards(user_id, card_account_id, card_type)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_cc_cards_user_name_type_acc ON credit_cards(user_id, name, card_type, card_account_id)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_cc_inv_user_period ON credit_card_invoices(user_id, card_id, invoice_period)")
    _backfill_fixed_income_assets_phase1(cur)
    _backfill_multiworkspace_phase1(cur)


def _add_column_sqlite(cur, table: str, column_def: str):
    col_name = column_def.split()[0]
    cols = cur.execute(f"PRAGMA table_info({table})").fetchall()
    existing = {c[1] for c in cols}
    if col_name not in existing:
        cur.execute(f"ALTER TABLE {table} ADD COLUMN {column_def}")


def _migrate_multitenant_sqlite(cur):
    _add_column_sqlite(cur, "users", "role TEXT NOT NULL DEFAULT 'user'")
    _add_column_sqlite(cur, "users", "is_active INTEGER NOT NULL DEFAULT 1")
    _add_column_sqlite(cur, "users", "global_role TEXT")
    _add_column_sqlite(cur, "users", "avatar_data TEXT")
    _add_column_sqlite(cur, "users", "token_version INTEGER NOT NULL DEFAULT 0")
    _add_column_sqlite(cur, "users", "password_changed_at TEXT")
    cur.execute("""
    UPDATE users
    SET global_role = CASE
        WHEN LOWER(COALESCE(role, '')) = 'admin' THEN 'SUPER_ADMIN'
        ELSE 'USER'
    END
    WHERE global_role IS NULL OR TRIM(global_role) = ''
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS workspaces (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        owner_user_id INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS workspace_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workspace_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        role TEXT NOT NULL,
        created_by INTEGER,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS permissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workspace_user_id INTEGER NOT NULL,
        module TEXT NOT NULL,
        can_view INTEGER NOT NULL DEFAULT 0,
        can_add INTEGER NOT NULL DEFAULT 0,
        can_edit INTEGER NOT NULL DEFAULT 0,
        can_delete INTEGER NOT NULL DEFAULT 0
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS password_reset_tokens (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        token_hash TEXT NOT NULL UNIQUE,
        expires_at TEXT NOT NULL,
        requested_ip TEXT,
        requested_user_agent TEXT,
        consumed_ip TEXT,
        consumed_user_agent TEXT,
        used_at TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS lists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workspace_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        type TEXT NOT NULL,
        description TEXT,
        status TEXT NOT NULL DEFAULT 'ativa',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS list_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workspace_id INTEGER NOT NULL,
        list_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        quantity REAL NOT NULL,
        unit TEXT NOT NULL DEFAULT 'un',
        suggested_value REAL NOT NULL DEFAULT 0,
        total_value REAL NOT NULL DEFAULT 0,
        acquired INTEGER NOT NULL DEFAULT 0,
        completion_date TEXT,
        notes TEXT,
        sort_order INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY(list_id) REFERENCES lists(id)
    );
    """)

    _add_column_sqlite(cur, "accounts", "user_id INTEGER")
    _add_column_sqlite(cur, "accounts", "currency TEXT NOT NULL DEFAULT 'BRL'")
    _add_column_sqlite(cur, "accounts", "show_on_dashboard INTEGER NOT NULL DEFAULT 0")
    _add_column_sqlite(cur, "categories", "user_id INTEGER")
    _add_column_sqlite(cur, "transactions", "user_id INTEGER")
    _add_column_sqlite(cur, "transactions", "recurrence_id TEXT")
    _add_column_sqlite(cur, "assets", "user_id INTEGER")
    _add_column_sqlite(cur, "assets", "sector TEXT")
    _add_column_sqlite(cur, "assets", "source_account_id INTEGER")
    _add_column_sqlite(cur, "assets", "issuer TEXT")
    _add_column_sqlite(cur, "assets", "rate_type TEXT")
    _add_column_sqlite(cur, "assets", "rate_value REAL")
    _add_column_sqlite(cur, "assets", "maturity_date TEXT")
    _add_column_sqlite(cur, "assets", "rentability_type TEXT")
    _add_column_sqlite(cur, "assets", "index_name TEXT")
    _add_column_sqlite(cur, "assets", "index_pct REAL")
    _add_column_sqlite(cur, "assets", "spread_rate REAL")
    _add_column_sqlite(cur, "assets", "fixed_rate REAL")
    _add_column_sqlite(cur, "assets", "principal_amount REAL")
    _add_column_sqlite(cur, "assets", "current_value REAL")
    _add_column_sqlite(cur, "assets", "fair_price REAL")
    _add_column_sqlite(cur, "assets", "safety_margin_pct REAL")
    _add_column_sqlite(cur, "assets", "user_objective TEXT")
    _add_column_sqlite(cur, "assets", "last_update TEXT")
    cur.execute("""
    CREATE TABLE IF NOT EXISTS asset_valuation_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        asset_id INTEGER NOT NULL,
        file_name TEXT NOT NULL,
        content_type TEXT NOT NULL DEFAULT 'application/pdf',
        file_data BLOB NOT NULL,
        uploaded_at TEXT NOT NULL DEFAULT (datetime('now')),
        user_id INTEGER,
        workspace_id INTEGER,
        UNIQUE(asset_id, user_id),
        FOREIGN KEY(asset_id) REFERENCES assets(id)
    );
    """)
    _add_column_sqlite(cur, "trades", "user_id INTEGER")
    _add_column_sqlite(cur, "trades", "exchange_rate REAL NOT NULL DEFAULT 1")
    _add_column_sqlite(cur, "income_events", "user_id INTEGER")
    _add_column_sqlite(cur, "income_events", "credit_account_id INTEGER")
    _add_column_sqlite(cur, "prices", "user_id INTEGER")
    _add_column_sqlite(cur, "asset_prices", "user_id INTEGER")
    _add_column_sqlite(cur, "credit_cards", "user_id INTEGER")
    _add_column_sqlite(cur, "credit_cards", "brand TEXT NOT NULL DEFAULT 'Visa'")
    _add_column_sqlite(cur, "credit_cards", "model TEXT NOT NULL DEFAULT 'Black'")
    _add_column_sqlite(cur, "credit_cards", "card_type TEXT NOT NULL DEFAULT 'Credito'")
    _add_column_sqlite(cur, "credit_cards", "close_day INTEGER")
    _add_column_sqlite(cur, "credit_card_invoices", "user_id INTEGER")
    _add_column_sqlite(cur, "credit_card_charges", "user_id INTEGER")
    _add_column_sqlite(cur, "credit_card_charges", "category_id INTEGER")
    _add_column_sqlite(cur, "credit_card_charges", "description TEXT")
    _add_column_sqlite(cur, "credit_card_charges", "note TEXT")
    _add_column_sqlite(cur, "list_items", "unit TEXT NOT NULL DEFAULT 'un'")
    cur.execute("UPDATE list_items SET unit = 'un' WHERE unit IS NULL OR TRIM(unit) = ''")

    cur.execute("""
    CREATE TABLE IF NOT EXISTS index_rates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        index_name TEXT NOT NULL,
        ref_date TEXT NOT NULL,
        value REAL NOT NULL,
        source TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        user_id INTEGER
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sync_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        scope_kind TEXT NOT NULL,
        scope_id INTEGER NOT NULL,
        sync_type TEXT NOT NULL,
        sync_key TEXT NOT NULL,
        ref_date TEXT NOT NULL,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """)

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
    cur.execute("CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_user ON password_reset_tokens(user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_expires_at ON password_reset_tokens(expires_at)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_used_at ON password_reset_tokens(used_at)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_index_rates_name_date ON index_rates(index_name, ref_date)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_sync_runs_scope_type_key_date ON sync_runs(scope_kind, scope_id, sync_type, sync_key, ref_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_index_rates_ref_date ON index_rates(ref_date)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sync_runs_ref_date ON sync_runs(ref_date)")
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

    _add_column_sqlite(cur, "accounts", "workspace_id INTEGER")
    _add_column_sqlite(cur, "categories", "workspace_id INTEGER")
    _add_column_sqlite(cur, "transactions", "workspace_id INTEGER")
    _add_column_sqlite(cur, "assets", "workspace_id INTEGER")
    _add_column_sqlite(cur, "trades", "workspace_id INTEGER")
    _add_column_sqlite(cur, "income_events", "workspace_id INTEGER")
    _add_column_sqlite(cur, "prices", "workspace_id INTEGER")
    _add_column_sqlite(cur, "asset_prices", "workspace_id INTEGER")
    _add_column_sqlite(cur, "credit_cards", "workspace_id INTEGER")
    _add_column_sqlite(cur, "credit_card_invoices", "workspace_id INTEGER")
    _add_column_sqlite(cur, "credit_card_charges", "workspace_id INTEGER")
    _add_column_sqlite(cur, "index_rates", "workspace_id INTEGER")
    _add_column_sqlite(cur, "benchmark_settings", "workspace_id INTEGER")

    cur.execute("CREATE INDEX IF NOT EXISTS idx_workspaces_owner ON workspaces(owner_user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_workspaces_status ON workspaces(status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_workspace_users_workspace ON workspace_users(workspace_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_workspace_users_user ON workspace_users(user_id)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_workspace_users_workspace_user ON workspace_users(workspace_id, user_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_permissions_workspace_user ON permissions(workspace_user_id)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_permissions_workspace_user_module ON permissions(workspace_user_id, module)")

    cur.execute("CREATE INDEX IF NOT EXISTS idx_accounts_workspace ON accounts(workspace_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_categories_workspace ON categories(workspace_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_transactions_workspace ON transactions(workspace_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_assets_workspace ON assets(workspace_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_trades_workspace ON trades(workspace_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_income_events_workspace ON income_events(workspace_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_prices_workspace ON prices(workspace_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_asset_prices_workspace ON asset_prices(workspace_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_credit_cards_workspace ON credit_cards(workspace_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_credit_card_invoices_workspace ON credit_card_invoices(workspace_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_credit_card_charges_workspace ON credit_card_charges(workspace_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_index_rates_workspace ON index_rates(workspace_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_benchmark_settings_workspace ON benchmark_settings(workspace_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_lists_workspace ON lists(workspace_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_lists_workspace_status ON lists(workspace_id, status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_lists_workspace_type ON lists(workspace_id, type)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_list_items_workspace ON list_items(workspace_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_list_items_workspace_list ON list_items(workspace_id, list_id)")

    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_accounts_workspace_name ON accounts(workspace_id, name)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_categories_workspace_name ON categories(workspace_id, name)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_assets_workspace_symbol ON assets(workspace_id, symbol)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_benchmark_settings_workspace_name ON benchmark_settings(workspace_id, index_name)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_prices_workspace_asset_date ON prices(workspace_id, asset_id, date)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_asset_prices_workspace_asset_date ON asset_prices(workspace_id, asset_id, px_date)")
    cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS ux_index_rates_workspace_name_date ON index_rates(workspace_id, index_name, ref_date)")

    _backfill_fixed_income_assets_phase1(cur)
    _backfill_multiworkspace_phase1(cur)


def _fixed_income_asset_class_condition(column_ref: str = "asset_class") -> str:
    return (
        f"LOWER(REPLACE(COALESCE({column_ref}, ''), '_', ' ')) IN ('renda fixa', 'tesouro direto', 'coe', 'fundos') "
        f"OR UPPER(COALESCE({column_ref}, '')) IN ('RENDA_FIXA', 'TESOURO_DIRETO', 'COE', 'FUNDOS')"
    )


def _backfill_fixed_income_assets_phase1(cur):
    fixed_income_where = _fixed_income_asset_class_condition("asset_class")
    fx_factor = (
        "CASE "
        "WHEN UPPER(COALESCE(assets.currency, '')) = 'USD' "
        "THEN CASE WHEN COALESCE(t.exchange_rate, 0) > 0 THEN t.exchange_rate ELSE 1 END "
        "ELSE 1 END"
    )
    buy_cost_expr = (
        f"(COALESCE(t.quantity, 0) * COALESCE(t.price, 0) * {fx_factor}) + "
        f"(COALESCE(t.fees, 0) * {fx_factor})"
    )

    cur.execute(f"""
    UPDATE assets
    SET rentability_type = 'MANUAL'
    WHERE ({fixed_income_where})
      AND (rentability_type IS NULL OR TRIM(rentability_type) = '')
    """)

    cur.execute(f"""
    UPDATE assets
    SET principal_amount = (
        SELECT ROUND(CAST(SUM({buy_cost_expr}) AS NUMERIC), 6)
        FROM trades t
        WHERE t.asset_id = assets.id
          AND COALESCE(t.user_id, 0) = COALESCE(assets.user_id, 0)
          AND UPPER(COALESCE(t.side, '')) = 'BUY'
    )
    WHERE ({fixed_income_where})
      AND principal_amount IS NULL
      AND EXISTS (
          SELECT 1
          FROM trades t
          WHERE t.asset_id = assets.id
            AND COALESCE(t.user_id, 0) = COALESCE(assets.user_id, 0)
            AND UPPER(COALESCE(t.side, '')) = 'BUY'
      )
      AND NOT EXISTS (
          SELECT 1
          FROM trades t
          WHERE t.asset_id = assets.id
            AND COALESCE(t.user_id, 0) = COALESCE(assets.user_id, 0)
            AND UPPER(COALESCE(t.side, '')) = 'SELL'
      )
    """)

    cur.execute(f"""
    UPDATE assets
    SET current_value = principal_amount
    WHERE ({fixed_income_where})
      AND current_value IS NULL
      AND principal_amount IS NOT NULL
    """)


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
            show_on_dashboard INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            user_id INTEGER
        );
        """)
        cur.execute("""
        INSERT INTO accounts_new(id, name, type, currency, show_on_dashboard, created_at, user_id)
        SELECT id, name, type, COALESCE(currency, 'BRL'), COALESCE(show_on_dashboard, 0), created_at, user_id
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
            rentability_type TEXT,
            index_name TEXT,
            index_pct REAL,
            spread_rate REAL,
            fixed_rate REAL,
            principal_amount REAL,
            current_value REAL,
            fair_price REAL,
            safety_margin_pct REAL,
            user_objective TEXT,
            last_update TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            user_id INTEGER,
            FOREIGN KEY(broker_account_id) REFERENCES accounts(id)
        );
        """)
        cur.execute("""
        INSERT INTO assets_new(
            id, symbol, name, asset_class, sector, currency,
            broker_account_id, source_account_id, issuer, rate_type, rate_value, maturity_date,
            rentability_type, index_name, index_pct, spread_rate, fixed_rate, principal_amount, current_value, fair_price, safety_margin_pct, user_objective, last_update,
            created_at, user_id
        )
        SELECT
            id, symbol, name, asset_class, sector, currency,
            broker_account_id, source_account_id, issuer, rate_type, rate_value, maturity_date,
            rentability_type, index_name, index_pct, spread_rate, fixed_rate, principal_amount, current_value, fair_price, safety_margin_pct, user_objective, last_update,
            created_at, user_id
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
