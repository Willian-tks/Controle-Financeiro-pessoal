from db import get_conn
from tenant import get_current_user_id
from datetime import date, datetime
import calendar


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


def list_credit_cards(user_id: int | None = None):
    uid = _uid(user_id)
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT
            cc.id, cc.name, cc.card_account_id, ca.name AS linked_account, ca.type AS linked_account_type,
            cc.source_account_id, sa.name AS source_account, sa.type AS source_account_type,
            cc.due_day, COALESCE(cc.brand, 'Visa') AS brand, COALESCE(cc.card_type, 'Credito') AS card_type
        FROM credit_cards cc
        JOIN accounts ca ON ca.id = cc.card_account_id AND ca.user_id = cc.user_id
        JOIN accounts sa ON sa.id = cc.source_account_id AND sa.user_id = cc.user_id
        WHERE cc.user_id = ?
        ORDER BY cc.name
        """,
        (uid,),
    ).fetchall()
    conn.close()
    return rows


def create_credit_card(
    name: str,
    brand: str,
    card_type: str,
    card_account_id: int,
    source_account_id: int | None,
    due_day: int,
    user_id: int | None = None,
):
    uid = _uid(user_id)
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO credit_cards(name, brand, card_type, card_account_id, source_account_id, due_day, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name.strip(),
            brand.strip(),
            card_type.strip(),
            int(card_account_id),
            int(source_account_id) if source_account_id is not None else int(card_account_id),
            int(due_day),
            uid,
        ),
    )
    conn.commit()
    conn.close()


def update_credit_card(
    card_id: int,
    name: str,
    brand: str,
    card_type: str,
    card_account_id: int,
    source_account_id: int | None,
    due_day: int,
    user_id: int | None = None,
):
    uid = _uid(user_id)
    conn = get_conn()
    conn.execute(
        """
        UPDATE credit_cards
        SET name = ?, brand = ?, card_type = ?, card_account_id = ?, source_account_id = ?, due_day = ?
        WHERE id = ? AND user_id = ?
        """,
        (
            name.strip(),
            brand.strip(),
            card_type.strip(),
            int(card_account_id),
            int(source_account_id) if source_account_id is not None else int(card_account_id),
            int(due_day),
            int(card_id),
            uid,
        ),
    )
    conn.commit()
    conn.close()


def delete_credit_card(card_id: int, user_id: int | None = None) -> int:
    uid = _uid(user_id)
    conn = get_conn()
    row = conn.execute(
        """
        SELECT COUNT(*) AS n
        FROM credit_card_charges
        WHERE card_id = ? AND user_id = ?
        """,
        (int(card_id), uid),
    ).fetchone()
    if row and int(row["n"]) > 0:
        conn.close()
        return 0
    cur = conn.execute("DELETE FROM credit_cards WHERE id = ? AND user_id = ?", (int(card_id), uid))
    conn.commit()
    conn.close()
    return int(cur.rowcount or 0)


def get_credit_card_by_account_and_type(card_account_id: int, card_type: str, user_id: int | None = None):
    uid = _uid(user_id)
    conn = get_conn()
    row = conn.execute(
        """
        SELECT id, name, COALESCE(brand, 'Visa') AS brand, COALESCE(card_type, 'Credito') AS card_type, card_account_id, source_account_id, due_day
        FROM credit_cards
        WHERE card_account_id = ? AND user_id = ? AND COALESCE(card_type, 'Credito') = ?
        """,
        (int(card_account_id), uid, str(card_type)),
    ).fetchone()
    conn.close()
    return row


def get_credit_card_by_id_and_type(card_id: int, card_type: str, user_id: int | None = None):
    uid = _uid(user_id)
    conn = get_conn()
    row = conn.execute(
        """
        SELECT id, name, COALESCE(brand, 'Visa') AS brand, COALESCE(card_type, 'Credito') AS card_type, card_account_id, source_account_id, due_day
        FROM credit_cards
        WHERE id = ? AND user_id = ? AND COALESCE(card_type, 'Credito') = ?
        """,
        (int(card_id), uid, str(card_type)),
    ).fetchone()
    conn.close()
    return row


def _next_month_due_date(purchase_date: str, due_day: int) -> tuple[str, str]:
    d = datetime.strptime(purchase_date, "%Y-%m-%d").date()
    y = d.year + (1 if d.month == 12 else 0)
    m = 1 if d.month == 12 else d.month + 1
    last = calendar.monthrange(y, m)[1]
    day = max(1, min(int(due_day), last))
    due = date(y, m, day)
    return due.strftime("%Y-%m"), due.strftime("%Y-%m-%d")


def register_credit_charge(
    card_id: int,
    purchase_date: str,
    amount: float,
    note: str | None = None,
    user_id: int | None = None,
):
    uid = _uid(user_id)
    conn = get_conn()
    card = conn.execute(
        "SELECT id, due_day FROM credit_cards WHERE id = ? AND user_id = ?",
        (int(card_id), uid),
    ).fetchone()
    if not card:
        conn.close()
        raise ValueError("Cartão não encontrado.")

    invoice_period, due_date = _next_month_due_date(purchase_date, int(card["due_day"]))
    value = abs(float(amount))
    conn.execute(
        """
        INSERT INTO credit_card_charges(card_id, purchase_date, amount, invoice_period, due_date, paid, note, user_id)
        VALUES (?, ?, ?, ?, ?, 0, ?, ?)
        """,
        (int(card_id), purchase_date, value, invoice_period, due_date, note, uid),
    )

    existing = conn.execute(
        """
        SELECT id, total_amount
        FROM credit_card_invoices
        WHERE user_id = ? AND card_id = ? AND invoice_period = ?
        """,
        (uid, int(card_id), invoice_period),
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE credit_card_invoices SET total_amount = ? WHERE id = ? AND user_id = ?",
            (float(existing["total_amount"] or 0.0) + value, int(existing["id"]), uid),
        )
    else:
        conn.execute(
            """
            INSERT INTO credit_card_invoices(card_id, invoice_period, due_date, total_amount, paid_amount, status, user_id)
            VALUES (?, ?, ?, ?, 0, 'OPEN', ?)
            """,
            (int(card_id), invoice_period, due_date, value, uid),
        )
    conn.commit()
    conn.close()


def list_credit_card_invoices(user_id: int | None = None, status: str | None = None, card_id: int | None = None):
    uid = _uid(user_id)
    conn = get_conn()
    q = """
        SELECT
            i.id, i.card_id, cc.name AS card_name, ca.name AS linked_account, sa.name AS source_account,
            i.invoice_period, i.due_date, i.total_amount, i.paid_amount, i.status
        FROM credit_card_invoices i
        JOIN credit_cards cc ON cc.id = i.card_id AND cc.user_id = i.user_id
        JOIN accounts ca ON ca.id = cc.card_account_id AND ca.user_id = cc.user_id
        JOIN accounts sa ON sa.id = cc.source_account_id AND sa.user_id = cc.user_id
        WHERE i.user_id = ?
    """
    params: list = [uid]
    if status:
        q += " AND i.status = ?"
        params.append(status)
    if card_id is not None:
        q += " AND i.card_id = ?"
        params.append(int(card_id))
    q += " ORDER BY i.due_date DESC, i.id DESC"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return rows


def pay_credit_card_invoice(invoice_id: int, payment_date: str, user_id: int | None = None) -> dict:
    uid = _uid(user_id)
    conn = get_conn()
    inv = conn.execute(
        """
        SELECT i.id, i.card_id, i.invoice_period, i.due_date, i.total_amount, i.paid_amount, i.status,
               cc.name AS card_name, cc.card_account_id, cc.source_account_id,
               ca.name AS linked_account_name, sa.name AS source_account_name
        FROM credit_card_invoices i
        JOIN credit_cards cc ON cc.id = i.card_id AND cc.user_id = i.user_id
        JOIN accounts ca ON ca.id = cc.card_account_id AND ca.user_id = cc.user_id
        JOIN accounts sa ON sa.id = cc.source_account_id AND sa.user_id = cc.user_id
        WHERE i.id = ? AND i.user_id = ?
        """,
        (int(invoice_id), uid),
    ).fetchone()
    if not inv:
        conn.close()
        raise ValueError("Fatura não encontrada.")

    remaining = float(inv["total_amount"] or 0.0) - float(inv["paid_amount"] or 0.0)
    if remaining <= 0 or str(inv["status"]).upper() == "PAID":
        conn.close()
        raise ValueError("Fatura já está paga.")

    cat_id = ensure_category("Fatura Cartão", "Despesa", user_id=uid)
    linked_name = str(inv["linked_account_name"])
    period = str(inv["invoice_period"])

    conn.execute(
        """
        INSERT INTO transactions(date, description, amount_brl, account_id, category_id, method, notes, user_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payment_date,
            f"PGTO FATURA {inv['card_name']} ({period})",
            -abs(remaining),
            int(inv["source_account_id"]),
            int(cat_id),
            "Credito",
            f"Pagamento de fatura do cartão {inv['card_name']} (vinculado a {linked_name})",
            uid,
        ),
    )
    conn.execute(
        "UPDATE credit_card_invoices SET paid_amount = total_amount, status = 'PAID' WHERE id = ? AND user_id = ?",
        (int(invoice_id), uid),
    )
    conn.execute(
        "UPDATE credit_card_charges SET paid = 1 WHERE user_id = ? AND card_id = ? AND invoice_period = ?",
        (uid, int(inv["card_id"]), str(inv["invoice_period"])),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "paid_amount": abs(remaining)}
