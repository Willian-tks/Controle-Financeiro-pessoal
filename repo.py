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
def get_category_by_name(name: str):
    conn = get_conn()
    row = conn.execute("SELECT id, name, kind FROM categories WHERE name = ?", (name,)).fetchone()
    conn.close()
    return row

def ensure_category(name: str, kind: str = "Transferencia"):
    row = get_category_by_name(name)
    if row:
        return row["id"]
    conn = get_conn()
    conn.execute("INSERT INTO categories(name, kind) VALUES (?, ?)", (name, kind))
    conn.commit()
    row = conn.execute("SELECT id FROM categories WHERE name = ?", (name,)).fetchone()
    conn.close()
    return row["id"]

def create_transaction(date: str, description: str, amount: float, category_id: int, account_id: int,
                       method: str | None = None, notes: str | None = None):
    conn = get_conn()
    conn.execute("""
        INSERT INTO transactions(date, description, amount, category_id, account_id, method, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (date, description, float(amount), int(category_id), int(account_id), method, notes))
    conn.commit()
    conn.close()
def delete_transactions_by_description_prefix(prefix: str):
    conn = get_conn()
    conn.execute("DELETE FROM transactions WHERE description LIKE ?", (f"{prefix}%",))
    conn.commit()
    conn.close()

def delete_transactions_by_description_prefix(prefix: str) -> int:
    """
    Apaga transações cuja descrição começa com `prefix`.
    Retorna a quantidade apagada.
    """
    conn = get_conn()
    cur = conn.execute(
        "DELETE FROM transactions WHERE description LIKE ?",
        (f"{prefix}%",)
    )
    conn.commit()
    deleted = cur.rowcount if cur.rowcount is not None else 0
    conn.close()
    return deleted

def delete_transactions_by_description_exact(desc: str) -> int:
    conn = get_conn()
    cur = conn.execute("DELETE FROM transactions WHERE description = ?", (desc,))
    conn.commit()
    deleted = cur.rowcount if cur.rowcount is not None else 0
    conn.close()
    return deleted

# -------------------------
# ACCOUNTS
# -------------------------
def update_account(account_id: int, name: str, acc_type: str):
    conn = get_conn()
    conn.execute(
        "UPDATE accounts SET name = ?, type = ? WHERE id = ?",
        (name.strip(), acc_type, int(account_id))
    )
    conn.commit()
    conn.close()

def account_usage_count(account_id: int) -> int:
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM transactions WHERE account_id = ?",
        (int(account_id),)
    ).fetchone()
    conn.close()
    return int(row["n"]) if row else 0

def delete_account(account_id: int) -> int:
    """
    Exclui conta somente se NÃO tiver transações vinculadas.
    Retorna 1 se excluiu, 0 se não excluiu.
    """
    used = account_usage_count(account_id)
    if used > 0:
        return 0

    conn = get_conn()
    cur = conn.execute("DELETE FROM accounts WHERE id = ?", (int(account_id),))
    conn.commit()
    conn.close()
    return cur.rowcount


# -------------------------
# CATEGORIES
# -------------------------
def update_category(category_id: int, name: str, kind: str):
    conn = get_conn()
    conn.execute(
        "UPDATE categories SET name = ?, kind = ? WHERE id = ?",
        (name.strip(), kind, int(category_id))
    )
    conn.commit()
    conn.close()

def category_usage_count(category_id: int) -> int:
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM transactions WHERE category_id = ?",
        (int(category_id),)
    ).fetchone()
    conn.close()
    return int(row["n"]) if row else 0

def delete_category(category_id: int) -> int:
    """
    Exclui categoria somente se NÃO tiver transações vinculadas.
    Retorna 1 se excluiu, 0 se não excluiu.
    """
    used = category_usage_count(category_id)
    if used > 0:
        return 0

    conn = get_conn()
    cur = conn.execute("DELETE FROM categories WHERE id = ?", (int(category_id),))
    conn.commit()
    conn.close()
    return cur.rowcount

#Esta linha foi criada para fazer deletes de lançamentos de teste durante a construção!!!!

def clear_transactions():
    conn = get_conn()
    cur = conn.execute("DELETE FROM transactions")
    conn.commit()
    conn.close()
    return cur.rowcount

def account_balance_value(account_id: int) -> float:
    conn = get_conn()
    row = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) AS bal FROM transactions WHERE account_id=?",
        (int(account_id),)
    ).fetchone()
    conn.close()
    return float(row["bal"] if row else 0.0)