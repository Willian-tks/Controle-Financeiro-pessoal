import os
import sqlite3
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

import db as db_module


BASE_DIR = Path(__file__).resolve().parent
SQLITE_PATH = BASE_DIR / "data" / "finance.db"
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

# Preserve the current model's dependency order so foreign keys can be loaded safely.
TABLES = [
    "users",
    "invites",
    "workspaces",
    "workspace_users",
    "permissions",
    "accounts",
    "categories",
    "transactions",
    "credit_cards",
    "credit_card_invoices",
    "credit_card_charges",
    "assets",
    "index_rates",
    "sync_runs",
    "trades",
    "income_events",
    "prices",
    "asset_prices",
]

BOOLEAN_COLUMNS_BY_TABLE = {
    "users": {"is_active"},
    "accounts": {"show_on_dashboard"},
    "credit_card_charges": {"paid"},
    "permissions": {"can_view", "can_add", "can_edit", "can_delete"},
}


def _missing_account_placeholders(src: sqlite3.Connection) -> list[dict]:
    refs: dict[int, dict] = {}
    queries = [
        (
            "credit_cards",
            "Cartao",
            """
            SELECT DISTINCT
                cc.card_account_id AS missing_account_id,
                cc.user_id,
                cc.workspace_id
            FROM credit_cards cc
            LEFT JOIN accounts a ON a.id = cc.card_account_id
            WHERE cc.card_account_id IS NOT NULL
              AND a.id IS NULL
            """,
        ),
        (
            "assets",
            "Banco",
            """
            SELECT DISTINCT
                x.source_account_id AS missing_account_id,
                x.user_id,
                x.workspace_id
            FROM assets x
            LEFT JOIN accounts a ON a.id = x.source_account_id
            WHERE x.source_account_id IS NOT NULL
              AND a.id IS NULL
            """,
        ),
    ]

    for origin, acc_type, sql in queries:
        for row in src.execute(sql).fetchall():
            missing_id = int(row["missing_account_id"])
            if missing_id in refs:
                continue
            refs[missing_id] = {
                "id": missing_id,
                "name": f"Conta Migrada {missing_id} ({origin})",
                "type": acc_type,
                "currency": "BRL",
                "show_on_dashboard": False,
                "user_id": row["user_id"],
                "workspace_id": row["workspace_id"],
            }

    return [refs[k] for k in sorted(refs)]


def _insert_missing_account_placeholders(src: sqlite3.Connection, dst) -> int:
    rows = _missing_account_placeholders(src)
    if not rows:
        return 0

    sql = """
    INSERT INTO accounts(id, name, type, currency, show_on_dashboard, user_id, workspace_id)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (id) DO NOTHING
    """
    with dst.cursor() as cur:
        for row in rows:
            cur.execute(
                sql,
                (
                    row["id"],
                    row["name"],
                    row["type"],
                    row["currency"],
                    row["show_on_dashboard"],
                    row["user_id"],
                    row["workspace_id"],
                ),
            )

    print(f"accounts placeholders: {len(rows)} conta(s) sintetica(s) criada(s)")
    return len(rows)


def _sqlite_has_table(conn: sqlite3.Connection, table: str) -> bool:
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        LIMIT 1
        """,
        (table,),
    ).fetchone()
    return row is not None


def _ensure_postgres_schema(dst) -> None:
    with dst.cursor() as cur:
        db_module._postgres_schema(cur)
        db_module._migrate_multitenant_postgres(cur)


def _normalize_bool(value):
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)

    raw = str(value).strip().lower()
    if raw in {"1", "true", "t", "yes", "y"}:
        return True
    if raw in {"0", "false", "f", "no", "n", ""}:
        return False
    return value


def _normalize_row_value(table: str, col: str, value):
    if col in BOOLEAN_COLUMNS_BY_TABLE.get(table, set()):
        return _normalize_bool(value)
    return value


def _copy_table(src: sqlite3.Connection, dst, table: str) -> int:
    if not _sqlite_has_table(src, table):
        print(f"{table}: ignorada (nao existe no SQLite de origem)")
        return 0

    rows = src.execute(f"SELECT * FROM {table}").fetchall()
    if not rows:
        print(f"{table}: 0 linha(s)")
        return 0

    cols = list(rows[0].keys())
    cols_csv = ", ".join(cols)
    placeholders = ", ".join(["%s"] * len(cols))
    sql = (
        f"INSERT INTO {table} ({cols_csv}) VALUES ({placeholders}) "
        "ON CONFLICT (id) DO NOTHING"
    )

    with dst.cursor() as cur:
        for row in rows:
            cur.execute(
                sql,
                tuple(_normalize_row_value(table, col, row[col]) for col in cols),
            )

    print(f"{table}: {len(rows)} linha(s) migrada(s)")
    return len(rows)


def _sync_sequences(dst) -> None:
    with dst.cursor() as cur:
        for table in TABLES:
            cur.execute(
                f"""
                SELECT setval(
                    pg_get_serial_sequence(%s, 'id'),
                    COALESCE((SELECT MAX(id) FROM {table}), 1),
                    true
                )
                """,
                (table,),
            )


def main() -> None:
    if not DATABASE_URL:
        raise RuntimeError("Defina DATABASE_URL antes de rodar a migracao.")
    if not SQLITE_PATH.exists():
        raise RuntimeError(f"SQLite nao encontrado: {SQLITE_PATH}")

    src = sqlite3.connect(SQLITE_PATH)
    src.row_factory = sqlite3.Row
    dst = psycopg.connect(DATABASE_URL, row_factory=dict_row)

    try:
        with dst.transaction():
            _ensure_postgres_schema(dst)

            total_rows = 0
            for table in TABLES:
                total_rows += _copy_table(src, dst, table)
                if table == "accounts":
                    total_rows += _insert_missing_account_placeholders(src, dst)

            _sync_sequences(dst)

        print(f"Migracao concluida. Total de linhas copiadas: {total_rows}")
    finally:
        src.close()
        dst.close()


if __name__ == "__main__":
    main()
