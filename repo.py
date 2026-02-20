from db import get_conn
from tenant import get_current_user_id


def _uid(user_id: int | None = None) -> int:
    return int(user_id) if user_id is not None else int(get_current_user_id())


def list_accounts(user_id: int | None = None):
    uid = _uid(user_id)
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, name, type FROM accounts WHERE user_id = ? ORDER BY name",
        (uid,),
    ).fetchall()
    conn.close()
    return rows


def create_account(name: str, acc_type: str, user_id: int | None = None):
    uid = _uid(user_id)
    nm = name.strip()
    if not nm:
        return
    conn = get_conn()
    exists = conn.execute(
        "SELECT id FROM accounts WHERE user_id = ? AND name = ?",
        (uid, nm),
    ).fetchone()
    if not exists:
        conn.execute(
            "INSERT INTO accounts(name, type, user_id) VALUES (?, ?, ?)",
            (nm, acc_type, uid),
        )
    conn.commit()
    conn.close()


def list_categories(kind: str | None = None, user_id: int | None = None):
    uid = _uid(user_id)
    conn = get_conn()
    if kind:
        rows = conn.execute(
            "SELECT id, name, kind FROM categories WHERE user_id = ? AND kind = ? ORDER BY name",
            (uid, kind),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT id, name, kind FROM categories WHERE user_id = ? ORDER BY kind, name",
            (uid,),
        ).fetchall()
    conn.close()
    return rows


def create_category(name: str, kind: str, user_id: int | None = None):
    uid = _uid(user_id)
    nm = name.strip()
    if not nm:
        return
    conn = get_conn()
    exists = conn.execute(
        "SELECT id FROM categories WHERE user_id = ? AND name = ?",
        (uid, nm),
    ).fetchone()
    if not exists:
        conn.execute(
            "INSERT INTO categories(name, kind, user_id) VALUES (?, ?, ?)",
            (nm, kind, uid),
        )
    conn.commit()
    conn.close()


def insert_transaction(
    date: str,
    description: str,
    amount: float,
    account_id: int,
    category_id: int | None,
    method: str | None,
    notes: str | None,
    user_id: int | None = None,
):
    uid = _uid(user_id)
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO transactions(date, description, amount_brl, account_id, category_id, method, notes, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            date,
            description.strip(),
            float(amount),
            int(account_id),
            int(category_id) if category_id else None,
            method.strip() if method else None,
            notes.strip() if notes else None,
            uid,
        ),
    )
    conn.commit()
    conn.close()


def delete_transaction(tx_id: int, user_id: int | None = None):
    uid = _uid(user_id)
    conn = get_conn()
    conn.execute(
        "DELETE FROM transactions WHERE id = ? AND user_id = ?",
        (int(tx_id), uid),
    )
    conn.commit()
    conn.close()


def fetch_transactions(
    date_from: str | None = None,
    date_to: str | None = None,
    account_id: int | None = None,
    category_id: int | None = None,
    user_id: int | None = None,
):
    uid = _uid(user_id)
    conn = get_conn()
    q = """
        SELECT
            t.id, t.date, t.description, t.amount_brl, t.method, t.notes,
            a.name AS account,
            c.name AS category,
            c.kind AS category_kind
        FROM transactions t
        JOIN accounts a ON a.id = t.account_id AND a.user_id = t.user_id
        LEFT JOIN categories c ON c.id = t.category_id AND c.user_id = t.user_id
        WHERE t.user_id = ?
    """
    params = [uid]
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


def get_category_by_name(name: str, user_id: int | None = None):
    uid = _uid(user_id)
    conn = get_conn()
    row = conn.execute(
        "SELECT id, name, kind FROM categories WHERE user_id = ? AND name = ?",
        (uid, name),
    ).fetchone()
    conn.close()
    return row


def ensure_category(name: str, kind: str = "Transferencia", user_id: int | None = None):
    uid = _uid(user_id)
    row = get_category_by_name(name, user_id=uid)
    if row:
        return row["id"]
    conn = get_conn()
    conn.execute(
        "INSERT INTO categories(name, kind, user_id) VALUES (?, ?, ?)",
        (name, kind, uid),
    )
    conn.commit()
    row = conn.execute(
        "SELECT id FROM categories WHERE user_id = ? AND name = ?",
        (uid, name),
    ).fetchone()
    conn.close()
    return row["id"]


def create_transaction(
    date: str,
    description: str,
    amount: float,
    category_id: int,
    account_id: int,
    method: str | None = None,
    notes: str | None = None,
    user_id: int | None = None,
):
    uid = _uid(user_id)
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO transactions(date, description, amount_brl, category_id, account_id, method, notes, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (date, description, float(amount), int(category_id), int(account_id), method, notes, uid),
    )
    conn.commit()
    conn.close()


def delete_transactions_by_description_prefix(prefix: str, user_id: int | None = None) -> int:
    uid = _uid(user_id)
    conn = get_conn()
    cur = conn.execute(
        "DELETE FROM transactions WHERE user_id = ? AND description LIKE ?",
        (uid, f"{prefix}%"),
    )
    conn.commit()
    deleted = cur.rowcount if cur.rowcount is not None else 0
    conn.close()
    return deleted


def delete_transactions_by_description_exact(desc: str, user_id: int | None = None) -> int:
    uid = _uid(user_id)
    conn = get_conn()
    cur = conn.execute(
        "DELETE FROM transactions WHERE user_id = ? AND description = ?",
        (uid, desc),
    )
    conn.commit()
    deleted = cur.rowcount if cur.rowcount is not None else 0
    conn.close()
    return deleted


def update_account(account_id: int, name: str, acc_type: str, user_id: int | None = None):
    uid = _uid(user_id)
    conn = get_conn()
    conn.execute(
        "UPDATE accounts SET name = ?, type = ? WHERE id = ? AND user_id = ?",
        (name.strip(), acc_type, int(account_id), uid),
    )
    conn.commit()
    conn.close()


def account_usage_count(account_id: int, user_id: int | None = None) -> int:
    uid = _uid(user_id)
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM transactions WHERE account_id = ? AND user_id = ?",
        (int(account_id), uid),
    ).fetchone()
    conn.close()
    return int(row["n"]) if row else 0


def delete_account(account_id: int, user_id: int | None = None) -> int:
    uid = _uid(user_id)
    used = account_usage_count(account_id, user_id=uid)
    if used > 0:
        return 0

    conn = get_conn()
    cur = conn.execute(
        "DELETE FROM accounts WHERE id = ? AND user_id = ?",
        (int(account_id), uid),
    )
    conn.commit()
    conn.close()
    return cur.rowcount


def update_category(category_id: int, name: str, kind: str, user_id: int | None = None):
    uid = _uid(user_id)
    conn = get_conn()
    conn.execute(
        "UPDATE categories SET name = ?, kind = ? WHERE id = ? AND user_id = ?",
        (name.strip(), kind, int(category_id), uid),
    )
    conn.commit()
    conn.close()


def category_usage_count(category_id: int, user_id: int | None = None) -> int:
    uid = _uid(user_id)
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM transactions WHERE category_id = ? AND user_id = ?",
        (int(category_id), uid),
    ).fetchone()
    conn.close()
    return int(row["n"]) if row else 0


def delete_category(category_id: int, user_id: int | None = None) -> int:
    uid = _uid(user_id)
    used = category_usage_count(category_id, user_id=uid)
    if used > 0:
        return 0

    conn = get_conn()
    cur = conn.execute(
        "DELETE FROM categories WHERE id = ? AND user_id = ?",
        (int(category_id), uid),
    )
    conn.commit()
    conn.close()
    return cur.rowcount


def clear_transactions(user_id: int | None = None):
    uid = _uid(user_id)
    conn = get_conn()
    cur = conn.execute("DELETE FROM transactions WHERE user_id = ?", (uid,))
    conn.commit()
    conn.close()
    return cur.rowcount


def account_balance_value(account_id: int, user_id: int | None = None) -> float:
    uid = _uid(user_id)
    conn = get_conn()
    row = conn.execute(
        "SELECT COALESCE(SUM(amount_brl), 0) AS bal FROM transactions WHERE account_id = ? AND user_id = ?",
        (int(account_id), uid),
    ).fetchone()
    conn.close()
    return float(row["bal"] if row else 0.0)
