# repo.py
from db import get_conn

def list_accounts():
    conn = get_conn()
    rows = conn.execute("SELECT id, name, type FROM accounts ORDER BY name").fetchall()
    conn.close()
    return rows

def create_account(name: str, acc_type: str):
    conn = get_conn()
    conn.execute("INSERT OR IGNORE INTO accounts(name, type) VALUES (?, ?)", (name.strip(), acc_type))
    conn.commit()
    conn.close()

def list_categories(kind: str | None = None):
    conn = get_conn()
    if kind:
        rows = conn.execute(
            "SELECT id, name, kind FROM categories WHERE kind=? ORDER BY name",
            (kind,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT id, name, kind FROM categories ORDER BY kind, name").fetchall()
    conn.close()
    return rows

def create_category(name: str, kind: str):
    conn = get_conn()
    conn.execute("INSERT OR IGNORE INTO categories(name, kind) VALUES (?, ?)", (name.strip(), kind))
    conn.commit()
    conn.close()

def insert_transaction(date: str, description: str, amount: float, account_id: int,
                       category_id: int | None, method: str | None, notes: str | None):
    conn = get_conn()
    conn.execute("""
        INSERT INTO transactions(date, description, amount, account_id, category_id, method, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (date, description.strip(), float(amount), int(account_id),
          int(category_id) if category_id else None,
          method.strip() if method else None,
          notes.strip() if notes else None))
    conn.commit()
    conn.close()

def delete_transaction(tx_id: int):
    conn = get_conn()
    conn.execute("DELETE FROM transactions WHERE id=?", (int(tx_id),))
    conn.commit()
    conn.close()

def fetch_transactions(date_from: str | None = None, date_to: str | None = None,
                       account_id: int | None = None, category_id: int | None = None):
    conn = get_conn()
    q = """
        SELECT
            t.id, t.date, t.description, t.amount, t.method, t.notes,
            a.name AS account,
            c.name AS category,
            c.kind AS category_kind
        FROM transactions t
        JOIN accounts a ON a.id = t.account_id
        LEFT JOIN categories c ON c.id = t.category_id
        WHERE 1=1
    """
    params = []
    if date_from:
        q += " AND t.date >= ?"
        params.append(date_from)
    if date_to:
        q += " AND t.date <= ?"
        params.append(date_to)
    if account_id:
        q += " AND t.account_id = ?"
        params.append(int(account_id))
    if category_id:
        q += " AND t.category_id = ?"
        params.append(int(category_id))

    q += " ORDER BY t.date DESC, t.id DESC"

    rows = conn.execute(q, params).fetchall()
    conn.close()
    return rows