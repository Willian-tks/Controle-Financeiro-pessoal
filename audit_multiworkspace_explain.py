from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from db import USE_POSTGRES, get_conn, init_db


REPORT_PATH = Path("MULTIWORKSPACE_EXPLAIN_AUDIT.md")


def _as_dict(row: Any) -> dict[str, Any]:
    if isinstance(row, dict):
        return row
    try:
        return dict(row)
    except Exception:
        pass
    if isinstance(row, tuple):
        return {str(i): v for i, v in enumerate(row)}
    return {"value": row}


def _query_plan_sql(sql: str) -> str:
    base = str(sql).strip().rstrip(";")
    if USE_POSTGRES:
        return f"EXPLAIN {base}"
    return f"EXPLAIN QUERY PLAN {base}"


def _critical_queries() -> list[dict[str, Any]]:
    return [
        {
            "name": "accounts_by_workspace",
            "sql": "SELECT id, name, type, currency FROM accounts WHERE workspace_id = ? ORDER BY id DESC LIMIT 50",
            "params": (1,),
        },
        {
            "name": "categories_by_workspace",
            "sql": "SELECT id, name, kind FROM categories WHERE workspace_id = ? ORDER BY id DESC LIMIT 100",
            "params": (1,),
        },
        {
            "name": "transactions_recent_by_workspace",
            "sql": (
                "SELECT id, date, account_id, category_id "
                "FROM transactions WHERE workspace_id = ? "
                "ORDER BY date DESC, id DESC LIMIT 200"
            ),
            "params": (1,),
        },
        {
            "name": "open_invoices_by_workspace",
            "sql": (
                "SELECT i.id, i.card_id, i.invoice_period, i.due_date "
                "FROM credit_card_invoices i "
                "JOIN credit_cards c ON c.id = i.card_id AND c.workspace_id = i.workspace_id "
                "WHERE i.workspace_id = ? AND i.status = 'OPEN' "
                "ORDER BY i.due_date ASC LIMIT 100"
            ),
            "params": (1,),
        },
        {
            "name": "assets_by_workspace",
            "sql": "SELECT id, symbol, asset_class, current_value FROM assets WHERE workspace_id = ? ORDER BY id DESC LIMIT 200",
            "params": (1,),
        },
        {
            "name": "trades_recent_by_workspace",
            "sql": "SELECT id, asset_id, date, side FROM trades WHERE workspace_id = ? ORDER BY date DESC, id DESC LIMIT 200",
            "params": (1,),
        },
        {
            "name": "prices_recent_by_workspace",
            "sql": "SELECT id, asset_id, date, price FROM prices WHERE workspace_id = ? ORDER BY date DESC, id DESC LIMIT 200",
            "params": (1,),
        },
        {
            "name": "workspace_members",
            "sql": "SELECT user_id, role FROM workspace_users WHERE workspace_id = ? ORDER BY user_id",
            "params": (1,),
        },
        {
            "name": "permissions_by_workspace_user",
            "sql": (
                "SELECT module, can_view, can_add, can_edit, can_delete "
                "FROM permissions WHERE workspace_user_id = ? ORDER BY module"
            ),
            "params": (1,),
        },
    ]


def _format_plan_rows(rows: list[Any]) -> list[str]:
    out: list[str] = []
    for row in rows:
        d = _as_dict(row)
        if USE_POSTGRES:
            text = str(next(iter(d.values())) if d else row)
        else:
            text = str(d.get("detail") or d.get("3") or d)
        out.append(f"- {text}")
    return out


def main() -> int:
    init_db()
    lines: list[str] = []
    ts = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    lines.append("# Auditoria EXPLAIN - Multiworkspace")
    lines.append("")
    lines.append(f"- Gerado em: `{ts}`")
    lines.append(f"- Banco alvo: `{'postgres' if USE_POSTGRES else 'sqlite'}`")
    lines.append("")

    with get_conn() as conn:
        for item in _critical_queries():
            name = item["name"]
            sql = item["sql"]
            params = tuple(item.get("params") or ())
            lines.append(f"## {name}")
            lines.append("")
            lines.append("```sql")
            lines.append(sql)
            lines.append("```")
            try:
                rows = conn.execute(_query_plan_sql(sql), params).fetchall() or []
                plan_lines = _format_plan_rows(rows)
                lines.append("Plano:")
                lines.extend(plan_lines if plan_lines else ["- (sem linhas retornadas)"])
            except Exception as e:
                lines.append(f"Erro ao analisar: `{e}`")
            lines.append("")

    REPORT_PATH.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    print(f"[ok] Relatório salvo em {REPORT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
