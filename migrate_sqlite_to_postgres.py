import os
import sqlite3
from pathlib import Path

import psycopg
from psycopg.rows import dict_row


BASE_DIR = Path(__file__).resolve().parent
SQLITE_PATH = BASE_DIR / "data" / "finance.db"
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

TABLES = [
    "accounts",
    "categories",
    "assets",
    "transactions",
    "trades",
    "income_events",
    "prices",
    "asset_prices",
]


def main():
    if not DATABASE_URL:
        raise RuntimeError("Defina DATABASE_URL antes de rodar a migração.")
    if not SQLITE_PATH.exists():
        raise RuntimeError(f"SQLite não encontrado: {SQLITE_PATH}")

    src = sqlite3.connect(SQLITE_PATH)
    src.row_factory = sqlite3.Row
    dst = psycopg.connect(DATABASE_URL, row_factory=dict_row)

    try:
        for table in TABLES:
            rows = src.execute(f"SELECT * FROM {table}").fetchall()
            if not rows:
                continue

            cols = list(rows[0].keys())
            cols_csv = ", ".join(cols)
            placeholders = ", ".join(["%s"] * len(cols))
            sql = (
                f"INSERT INTO {table} ({cols_csv}) VALUES ({placeholders}) "
                "ON CONFLICT (id) DO NOTHING"
            )

            with dst.cursor() as cur:
                for r in rows:
                    cur.execute(sql, tuple(r[c] for c in cols))
            dst.commit()
            print(f"{table}: {len(rows)} linha(s) migrada(s)")

        # Ajusta sequências para próximos inserts.
        with dst.cursor() as cur:
            for table in TABLES:
                cur.execute(
                    """
                    SELECT setval(
                        pg_get_serial_sequence(%s, 'id'),
                        COALESCE((SELECT MAX(id) FROM """ + table + """), 1),
                        true
                    )
                    """,
                    (table,),
                )
        dst.commit()
        print("Migração concluída.")
    finally:
        src.close()
        dst.close()


if __name__ == "__main__":
    main()
