import argparse
import re
from collections import defaultdict
from datetime import datetime

from db import get_conn
from repo import ensure_category


DESC_RE = re.compile(r"^PGTO FATURA (.+) \((\d{4}-\d{2})\)$")


def _extract_created_date(created_at: str | None) -> str | None:
    if not created_at:
        return None
    raw = str(created_at).strip()
    if not raw:
        return None
    # SQLite datetime('now') -> "YYYY-MM-DD HH:MM:SS"
    # Postgres NOW() string repr -> "YYYY-MM-DD HH:MM:SS.ssssss+TZ"
    try:
        if "T" in raw:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(raw.replace(" ", "T"))
        return dt.date().isoformat()
    except Exception:
        return raw[:10] if len(raw) >= 10 else None


def _find_invoice(conn, user_id: int, card_name: str, period: str):
    return conn.execute(
        """
        SELECT i.id, i.card_id, i.invoice_period, i.due_date, i.total_amount, i.paid_amount
        FROM credit_card_invoices i
        JOIN credit_cards cc ON cc.id = i.card_id AND cc.user_id = i.user_id
        WHERE i.user_id = ? AND cc.name = ? AND i.invoice_period = ?
        ORDER BY i.id DESC
        LIMIT 1
        """,
        (int(user_id), str(card_name), str(period)),
    ).fetchone()


def _group_charges(conn, user_id: int, card_id: int, period: str):
    return conn.execute(
        """
        SELECT
            ch.category_id,
            COALESCE(c.name, 'Fatura Cartão') AS category_name,
            SUM(ch.amount) AS total_amount
        FROM credit_card_charges ch
        LEFT JOIN categories c ON c.id = ch.category_id AND c.user_id = ch.user_id
        WHERE ch.user_id = ? AND ch.card_id = ? AND ch.invoice_period = ?
        GROUP BY ch.category_id, COALESCE(c.name, 'Fatura Cartão')
        ORDER BY total_amount DESC
        """,
        (int(user_id), int(card_id), str(period)),
    ).fetchall()


def run(apply: bool = False) -> dict:
    conn = get_conn()
    stats = defaultdict(int)
    try:
        cat_fatura_by_user: dict[int, int] = {}
        rows = conn.execute(
            """
            SELECT
                t.id,
                t.user_id,
                t.date,
                t.created_at,
                t.description,
                t.amount_brl,
                t.account_id,
                t.method,
                t.notes,
                t.category_id,
                c.name AS category_name
            FROM transactions t
            LEFT JOIN categories c ON c.id = t.category_id AND c.user_id = t.user_id
            WHERE COALESCE(t.method, '') = 'Credito'
              AND t.description LIKE 'PGTO FATURA %'
            ORDER BY t.id ASC
            """
        ).fetchall()

        for row in rows:
            tx_id = int(row["id"])
            uid = int(row["user_id"] or 0)
            desc = str(row["description"] or "").strip()
            match = DESC_RE.match(desc)
            if not match:
                stats["skipped_desc_format"] += 1
                continue

            card_name = match.group(1).strip()
            period = match.group(2).strip()
            cat_name = str(row["category_name"] or "").strip()
            if cat_name and cat_name != "Fatura Cartão":
                stats["already_categorized"] += 1
                continue

            inv = _find_invoice(conn, uid, card_name, period)
            if not inv:
                stats["skipped_invoice_not_found"] += 1
                continue

            grouped = _group_charges(conn, uid, int(inv["card_id"]), period)
            if not grouped:
                stats["skipped_no_charges"] += 1
                continue

            if uid not in cat_fatura_by_user:
                cat_fatura_by_user[uid] = int(ensure_category("Fatura Cartão", "Despesa", user_id=uid))
            fallback_cat_id = cat_fatura_by_user[uid]

            tx_amount = abs(float(row["amount_brl"] or 0.0))
            if tx_amount <= 0:
                stats["skipped_zero_amount"] += 1
                continue

            grouped_total = float(sum(float(g["total_amount"] or 0.0) for g in grouped))
            if grouped_total <= 0:
                stats["skipped_group_total_zero"] += 1
                continue

            scale = tx_amount / grouped_total
            chunks: list[tuple[int, str, float]] = []
            posted = 0.0
            for idx, g in enumerate(grouped):
                cat_id = int(g["category_id"]) if g["category_id"] is not None else fallback_cat_id
                category_name = str(g["category_name"] or "Fatura Cartão")
                raw_value = float(g["total_amount"] or 0.0) * scale
                if idx == len(grouped) - 1:
                    value = max(0.0, tx_amount - posted)
                else:
                    value = max(0.0, raw_value)
                    posted += value
                chunks.append((cat_id, category_name, value))

            new_date = str(row["date"] or "")
            inv_due_date = str(inv["due_date"] or "")
            created_date = _extract_created_date(row["created_at"])
            # Corrige somente quando parece o bug antigo (data igual ao vencimento).
            if created_date and new_date == inv_due_date and created_date != inv_due_date:
                new_date = created_date
                stats["date_fixed"] += 1

            stats["tx_to_fix"] += 1
            stats["new_rows"] += len(chunks)

            if not apply:
                continue

            for cat_id, category_name, amount_value in chunks:
                out_desc = desc if len(chunks) == 1 else f"{desc} - {category_name}"
                conn.execute(
                    """
                    INSERT INTO transactions(date, description, amount_brl, account_id, category_id, method, notes, user_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        new_date,
                        out_desc,
                        -abs(amount_value),
                        int(row["account_id"]),
                        int(cat_id),
                        str(row["method"] or "Credito"),
                        row["notes"],
                        uid,
                    ),
                )

            conn.execute("DELETE FROM transactions WHERE id = ? AND user_id = ?", (tx_id, uid))
            stats["applied"] += 1

        if apply:
            conn.commit()
        else:
            conn.rollback()
        return dict(stats)
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Corrige histórico de PGTO FATURA, distribuindo por categoria e ajustando data quando aplicável."
    )
    parser.add_argument("--apply", action="store_true", help="Aplica as mudanças no banco.")
    args = parser.parse_args()

    result = run(apply=args.apply)
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"[{mode}] Resultado:")
    for k in sorted(result.keys()):
        print(f"- {k}: {result[k]}")


if __name__ == "__main__":
    main()
