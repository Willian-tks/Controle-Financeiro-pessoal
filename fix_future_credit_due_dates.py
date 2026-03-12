import argparse
import calendar
from datetime import datetime
import re

from db import get_conn


def _add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    base = (int(year) * 12 + (int(month) - 1)) + int(delta)
    return base // 12, (base % 12) + 1


def _extract_future_credit_group(note: str | None) -> str:
    txt = str(note or "").strip()
    match = re.search(r"\[(FUTCC-[a-zA-Z0-9]+)\]", txt)
    return str(match.group(1)) if match else ""


def _extract_installment_number(description: str | None) -> int | None:
    txt = str(description or "").strip()
    match = re.search(r"\((\d+)\/\d+\)\s*$", txt)
    if not match:
        return None
    try:
        num = int(match.group(1))
    except Exception:
        return None
    return num if num > 0 else None


def _month_anchor_due(created_at: str, due_day: int) -> tuple[int, int]:
    created = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
    year = int(created.year)
    month = int(created.month)
    if int(created.day) > int(due_day):
        return _add_months(year, month, 1)
    return year, month


def _target_dates(anchor_year: int, anchor_month: int, installment_number: int, due_day: int) -> tuple[str, str, str]:
    yy, mm = _add_months(anchor_year, anchor_month, max(0, int(installment_number) - 1))
    last_day = calendar.monthrange(yy, mm)[1]
    due_dom = max(1, min(int(due_day), last_day))
    invoice_period = f"{yy:04d}-{mm:02d}"
    due_date = f"{invoice_period}-{due_dom:02d}"
    purchase_date = f"{invoice_period}-01"
    return purchase_date, invoice_period, due_date


def _paid_flag(value) -> bool:
    raw = str(value if value is not None else "").strip().lower()
    return raw in {"1", "true", "t", "yes"}


def _owner_clause() -> str:
    return "COALESCE(user_id, -1) = ? AND COALESCE(workspace_id, -1) = ?"


def _rebuild_invoice(conn, owner_user: int, owner_workspace: int, card_id: int, invoice_period: str, due_day: int) -> None:
    charges = conn.execute(
        f"""
        SELECT id, amount, paid
        FROM credit_card_charges
        WHERE card_id = ?
          AND invoice_period = ?
          AND {_owner_clause()}
        """,
        (int(card_id), str(invoice_period), int(owner_user), int(owner_workspace)),
    ).fetchall()

    existing = conn.execute(
        f"""
        SELECT id
        FROM credit_card_invoices
        WHERE card_id = ?
          AND invoice_period = ?
          AND {_owner_clause()}
        ORDER BY id
        """,
        (int(card_id), str(invoice_period), int(owner_user), int(owner_workspace)),
    ).fetchall()

    if not charges:
      for row in existing:
        conn.execute("DELETE FROM credit_card_invoices WHERE id = ?", (int(row["id"]),))
      return

    year, month = str(invoice_period).split("-")
    last_day = calendar.monthrange(int(year), int(month))[1]
    due_date = f"{year}-{month}-{max(1, min(int(due_day), last_day)):02d}"
    total_amount = float(sum(float(r["amount"] or 0.0) for r in charges))
    paid_amount = float(sum(float(r["amount"] or 0.0) for r in charges if _paid_flag(r["paid"])))
    status = "PAID" if total_amount <= paid_amount + 1e-9 else "OPEN"

    if existing:
      first_id = int(existing[0]["id"])
      conn.execute(
          """
          UPDATE credit_card_invoices
          SET due_date = ?, total_amount = ?, paid_amount = ?, status = ?
          WHERE id = ?
          """,
          (due_date, total_amount, paid_amount, status, first_id),
      )
      for row in existing[1:]:
        conn.execute("DELETE FROM credit_card_invoices WHERE id = ?", (int(row["id"]),))
      return

    conn.execute(
        """
        INSERT INTO credit_card_invoices(card_id, invoice_period, due_date, total_amount, paid_amount, status, user_id, workspace_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(card_id),
            str(invoice_period),
            due_date,
            total_amount,
            paid_amount,
            status,
            None if int(owner_user) < 0 else int(owner_user),
            None if int(owner_workspace) < 0 else int(owner_workspace),
        ),
    )


def fix_future_credit_due_dates(apply_changes: bool = False) -> dict:
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT
            ch.id,
            ch.card_id,
            ch.purchase_date,
            ch.invoice_period,
            ch.due_date,
            ch.description,
            ch.note,
            ch.created_at,
            ch.user_id,
            ch.workspace_id,
            cc.due_day,
            cc.close_day
        FROM credit_card_charges ch
        JOIN credit_cards cc ON cc.id = ch.card_id
        WHERE COALESCE(ch.paid, FALSE) = FALSE
          AND COALESCE(ch.note, '') LIKE ?
        ORDER BY ch.id
        """,
        ("%[FUTCC-%",),
    ).fetchall()

    changed = []
    invoice_keys = set()
    grouped: dict[str, list] = {}
    for row in rows:
        group_id = _extract_future_credit_group(row["note"]) or f"single-{int(row['id'])}"
        grouped.setdefault(group_id, []).append(row)

    for group_rows in grouped.values():
        ordered = sorted(
            group_rows,
            key=lambda row: (
                _extract_installment_number(row["description"]) or 10**9,
                str(row["due_date"] or ""),
                int(row["id"]),
            ),
        )
        first = ordered[0]
        anchor_year, anchor_month = _month_anchor_due(first["created_at"], int(first["due_day"]))
        for position, row in enumerate(ordered, start=1):
            installment_number = _extract_installment_number(row["description"]) or position
            expected_purchase_date, expected_period, expected_due_date = _target_dates(
                anchor_year,
                anchor_month,
                installment_number,
                int(row["due_day"]),
            )
            if (
                str(row["purchase_date"]) == expected_purchase_date
                and str(row["invoice_period"]) == expected_period
                and str(row["due_date"]) == expected_due_date
            ):
                continue
            owner_user = int(row["user_id"]) if row["user_id"] is not None else -1
            owner_workspace = int(row["workspace_id"]) if row["workspace_id"] is not None else -1
            changed.append(
                {
                    "id": int(row["id"]),
                    "card_id": int(row["card_id"]),
                    "owner_user": owner_user,
                    "owner_workspace": owner_workspace,
                    "old_period": str(row["invoice_period"]),
                    "new_period": expected_period,
                    "new_due_date": expected_due_date,
                    "new_purchase_date": expected_purchase_date,
                    "due_day": int(row["due_day"]),
                }
            )
            invoice_keys.add((int(row["card_id"]), owner_user, owner_workspace, str(row["invoice_period"]), int(row["due_day"])))
            invoice_keys.add((int(row["card_id"]), owner_user, owner_workspace, expected_period, int(row["due_day"])))

    if apply_changes and changed:
        for item in changed:
            conn.execute(
                """
                UPDATE credit_card_charges
                SET purchase_date = ?, invoice_period = ?, due_date = ?
                WHERE id = ?
                """,
                (item["new_purchase_date"], item["new_period"], item["new_due_date"], item["id"]),
            )
        for card_id, owner_user, owner_workspace, invoice_period, due_day in sorted(invoice_keys):
            _rebuild_invoice(conn, owner_user, owner_workspace, card_id, invoice_period, due_day)
        conn.commit()

    conn.close()
    return {
        "matched_rows": len(rows),
        "updated_rows": len(changed),
        "applied": bool(apply_changes),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Corrige vencimentos de compromissos futuros no cartao para o mesmo mes da compra sintetica.")
    parser.add_argument("--apply", action="store_true", help="Aplica as correcoes no banco.")
    args = parser.parse_args()

    result = fix_future_credit_due_dates(apply_changes=args.apply)
    print(result)


if __name__ == "__main__":
    main()
