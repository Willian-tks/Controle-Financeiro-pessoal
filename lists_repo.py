from datetime import datetime
import re
from contextvars import ContextVar

from db import get_conn
from tenant import get_current_user_id, get_current_workspace_id


_USE_WORKSPACE_SCOPE: ContextVar[bool] = ContextVar("lists_repo_use_workspace_scope", default=False)


def _uid(user_id: int | None = None) -> int:
    wid = get_current_workspace_id(required=False)
    if wid is not None:
        _USE_WORKSPACE_SCOPE.set(True)
        return int(wid)

    uid = int(user_id) if user_id is not None else int(get_current_user_id())
    conn = get_conn()
    try:
        row = _exec(
            conn,
            """
            SELECT wu.workspace_id
            FROM workspace_users wu
            JOIN workspaces w ON w.id = wu.workspace_id
            WHERE wu.user_id = ?
            ORDER BY
                CASE WHEN LOWER(COALESCE(w.status, 'active')) = 'active' THEN 0 ELSE 1 END,
                CASE WHEN UPPER(COALESCE(wu.role, '')) = 'OWNER' THEN 0 ELSE 1 END,
                wu.workspace_id
            LIMIT 1
            """,
            (uid,),
            rewrite_scope=False,
        ).fetchone()
    except Exception:
        row = None
    finally:
        conn.close()

    if not row:
        _USE_WORKSPACE_SCOPE.set(False)
        return uid
    _USE_WORKSPACE_SCOPE.set(True)
    return int(row["workspace_id"])


def _scope_sql(query: str) -> str:
    return re.sub(r"(?<![A-Za-z0-9_])user_id(?![A-Za-z0-9_])", "workspace_id", str(query))


def _exec(conn, query: str, params: tuple | list | None = None, rewrite_scope: bool | None = None):
    use_workspace = _USE_WORKSPACE_SCOPE.get() if rewrite_scope is None else bool(rewrite_scope)
    q = _scope_sql(query) if use_workspace else str(query)
    return conn.execute(q, tuple(params or ()))


def _insert_and_get_id(conn, insert_sql: str, params: tuple | list | None = None) -> int:
    if getattr(conn, "_use_postgres", False):
        row = _exec(conn, insert_sql.rstrip().rstrip(";") + "\nRETURNING id", params).fetchone()
        return int(row["id"]) if row else 0
    _exec(conn, insert_sql, params)
    row = _exec(conn, "SELECT last_insert_rowid() AS id").fetchone()
    return int(row["id"]) if row else 0


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _normalize_list_row(row) -> dict | None:
    if not row:
        return None
    item = dict(row)
    item.setdefault("description", None)
    item["status"] = str(item.get("status") or "ativa").strip().lower()
    item["summary"] = _empty_summary()
    return item


def _normalize_item_row(row) -> dict | None:
    if not row:
        return None
    item = dict(row)
    item["quantity"] = float(item.get("quantity") or 0.0)
    item["unit"] = str(item.get("unit") or "un").strip().lower() or "un"
    item["suggested_value"] = float(item.get("suggested_value") or 0.0)
    item["total_value"] = float(item.get("total_value") or 0.0)
    item["acquired"] = bool(item.get("acquired"))
    item["sort_order"] = int(item.get("sort_order") or 0)
    return item


def _empty_summary() -> dict:
    return {
        "total_items": 0,
        "acquired_items": 0,
        "pending_items": 0,
        "completion_pct": 0.0,
        "estimated_total": 0.0,
    }


def _list_summary(conn, list_id: int, scope_id: int) -> dict:
    row = _exec(
        conn,
        """
        SELECT
            COUNT(*) AS total_items,
            COALESCE(SUM(CASE WHEN COALESCE(acquired, FALSE) = TRUE THEN 1 ELSE 0 END), 0) AS acquired_items,
            COALESCE(SUM(total_value), 0) AS estimated_total
        FROM list_items
        WHERE list_id = ? AND workspace_id = ?
        """,
        (int(list_id), int(scope_id)),
    ).fetchone()
    total_items = int(row["total_items"] or 0) if row else 0
    acquired_items = int(row["acquired_items"] or 0) if row else 0
    pending_items = max(0, total_items - acquired_items)
    completion_pct = float((acquired_items / total_items) * 100.0) if total_items else 0.0
    estimated_total = float(row["estimated_total"] or 0.0) if row else 0.0
    return {
        "total_items": total_items,
        "acquired_items": acquired_items,
        "pending_items": pending_items,
        "completion_pct": round(completion_pct, 2),
        "estimated_total": estimated_total,
    }


def _list_row_with_summary(conn, list_id: int, scope_id: int) -> dict | None:
    row = _exec(
        conn,
        """
        SELECT id, workspace_id, name, type, description, status, created_at, updated_at
        FROM lists
        WHERE id = ? AND workspace_id = ?
        """,
        (int(list_id), int(scope_id)),
    ).fetchone()
    item = _normalize_list_row(row)
    if not item:
        return None
    item["summary"] = _list_summary(conn, int(list_id), int(scope_id))
    return item


def list_lists(
    search: str | None = None,
    status: str | None = None,
    list_type: str | None = None,
    user_id: int | None = None,
) -> list[dict]:
    uid = _uid(user_id)
    conn = get_conn()
    q = """
        SELECT id, workspace_id, name, type, description, status, created_at, updated_at
        FROM lists
        WHERE workspace_id = ?
    """
    params: list[object] = [uid]
    if search:
        q += " AND LOWER(name) LIKE ?"
        params.append(f"%{str(search).strip().lower()}%")
    if status:
        q += " AND LOWER(status) = ?"
        params.append(str(status).strip().lower())
    if list_type:
        q += " AND LOWER(type) = ?"
        params.append(str(list_type).strip().lower())
    q += " ORDER BY created_at DESC, id DESC"
    rows = _exec(conn, q, params).fetchall()
    out = []
    for row in rows:
        item = _normalize_list_row(row)
        item["summary"] = _list_summary(conn, int(item["id"]), uid)
        out.append(item)
    conn.close()
    return out


def get_list(list_id: int, user_id: int | None = None) -> dict | None:
    uid = _uid(user_id)
    conn = get_conn()
    item = _list_row_with_summary(conn, int(list_id), uid)
    conn.close()
    return item


def get_list_detail(list_id: int, user_id: int | None = None) -> dict | None:
    uid = _uid(user_id)
    conn = get_conn()
    item = _list_row_with_summary(conn, int(list_id), uid)
    if not item:
        conn.close()
        return None
    item["items"] = list_items(int(list_id), user_id=user_id, _conn=conn, _scope_id=uid)
    conn.close()
    return item


def create_list(
    name: str,
    list_type: str,
    description: str | None = None,
    status: str = "ativa",
    user_id: int | None = None,
) -> dict:
    uid = _uid(user_id)
    now = _now_iso()
    conn = get_conn()
    new_id = _insert_and_get_id(
        conn,
        """
        INSERT INTO lists(workspace_id, name, type, description, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            uid,
            str(name).strip(),
            str(list_type).strip(),
            str(description).strip() if description and str(description).strip() else None,
            str(status or "ativa").strip().lower(),
            now,
            now,
        ),
    )
    item = _list_row_with_summary(conn, new_id, uid) if new_id else None
    conn.commit()
    conn.close()
    return item or {}


def update_list(
    list_id: int,
    name: str,
    list_type: str,
    description: str | None = None,
    status: str = "ativa",
    user_id: int | None = None,
) -> dict | None:
    uid = _uid(user_id)
    now = _now_iso()
    conn = get_conn()
    _exec(
        conn,
        """
        UPDATE lists
        SET name = ?, type = ?, description = ?, status = ?, updated_at = ?
        WHERE id = ? AND workspace_id = ?
        """,
        (
            str(name).strip(),
            str(list_type).strip(),
            str(description).strip() if description and str(description).strip() else None,
            str(status or "ativa").strip().lower(),
            now,
            int(list_id),
            uid,
        ),
    )
    item = _list_row_with_summary(conn, int(list_id), uid)
    conn.commit()
    conn.close()
    return item


def archive_list(list_id: int, user_id: int | None = None) -> dict | None:
    uid = _uid(user_id)
    now = _now_iso()
    conn = get_conn()
    _exec(conn, "UPDATE lists SET status = 'arquivada', updated_at = ? WHERE id = ? AND workspace_id = ?", (now, int(list_id), uid))
    item = _list_row_with_summary(conn, int(list_id), uid)
    conn.commit()
    conn.close()
    return item


def delete_list(list_id: int, user_id: int | None = None) -> int:
    uid = _uid(user_id)
    conn = get_conn()
    _exec(conn, "DELETE FROM list_items WHERE list_id = ? AND workspace_id = ?", (int(list_id), uid))
    cur = _exec(conn, "DELETE FROM lists WHERE id = ? AND workspace_id = ?", (int(list_id), uid))
    conn.commit()
    deleted = int(cur.rowcount or 0)
    conn.close()
    return deleted


def list_items(
    list_id: int,
    user_id: int | None = None,
    _conn=None,
    _scope_id: int | None = None,
) -> list[dict]:
    uid = int(_scope_id) if _scope_id is not None else _uid(user_id)
    conn = _conn or get_conn()
    rows = _exec(
        conn,
        """
        SELECT id, workspace_id, list_id, name, quantity, suggested_value, total_value,
               unit, acquired, completion_date, notes, sort_order, created_at, updated_at
        FROM list_items
        WHERE list_id = ? AND workspace_id = ?
        ORDER BY sort_order ASC, id ASC
        """,
        (int(list_id), uid),
    ).fetchall()
    out = [_normalize_item_row(row) for row in rows]
    if _conn is None:
        conn.close()
    return out


def get_item(item_id: int, user_id: int | None = None, _conn=None, _scope_id: int | None = None) -> dict | None:
    uid = int(_scope_id) if _scope_id is not None else _uid(user_id)
    conn = _conn or get_conn()
    row = _exec(
        conn,
        """
        SELECT id, workspace_id, list_id, name, quantity, suggested_value, total_value,
               unit, acquired, completion_date, notes, sort_order, created_at, updated_at
        FROM list_items
        WHERE id = ? AND workspace_id = ?
        """,
        (int(item_id), uid),
    ).fetchone()
    item = _normalize_item_row(row)
    if _conn is None:
        conn.close()
    return item


def _next_sort_order(conn, list_id: int, scope_id: int) -> int:
    row = _exec(
        conn,
        "SELECT COALESCE(MAX(sort_order), 0) AS max_sort_order FROM list_items WHERE list_id = ? AND workspace_id = ?",
        (int(list_id), int(scope_id)),
    ).fetchone()
    return int(row["max_sort_order"] or 0) + 1


def create_list_item(
    list_id: int,
    name: str,
    quantity: float,
    suggested_value: float = 0.0,
    notes: str | None = None,
    sort_order: int | None = None,
    unit: str = "un",
    user_id: int | None = None,
) -> dict:
    uid = _uid(user_id)
    conn = get_conn()
    parent = _exec(conn, "SELECT id FROM lists WHERE id = ? AND workspace_id = ?", (int(list_id), uid)).fetchone()
    if not parent:
        conn.close()
        raise ValueError("Lista não encontrada.")

    qty = float(quantity or 0.0)
    suggested = float(suggested_value or 0.0)
    total_value = qty * suggested
    now = _now_iso()
    final_sort_order = int(sort_order) if sort_order is not None else _next_sort_order(conn, int(list_id), uid)
    new_id = _insert_and_get_id(
        conn,
        """
        INSERT INTO list_items(
            workspace_id, list_id, name, quantity, unit, suggested_value, total_value,
            acquired, completion_date, notes, sort_order, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, FALSE, NULL, ?, ?, ?, ?)
        """,
        (
            uid,
            int(list_id),
            str(name).strip(),
            qty,
            str(unit or "un").strip().lower(),
            suggested,
            total_value,
            str(notes).strip() if notes and str(notes).strip() else None,
            final_sort_order,
            now,
            now,
        ),
    )
    item = get_item(new_id, user_id=user_id, _conn=conn, _scope_id=uid) if new_id else None
    conn.commit()
    conn.close()
    return item or {}


def update_list_item(
    item_id: int,
    name: str,
    quantity: float,
    suggested_value: float = 0.0,
    notes: str | None = None,
    sort_order: int | None = None,
    unit: str = "un",
    user_id: int | None = None,
) -> dict | None:
    uid = _uid(user_id)
    conn = get_conn()
    current = get_item(int(item_id), user_id=user_id, _conn=conn, _scope_id=uid)
    if not current:
        conn.close()
        return None

    qty = float(quantity or 0.0)
    suggested = float(suggested_value or 0.0)
    total_value = qty * suggested
    final_sort_order = int(sort_order) if sort_order is not None else int(current["sort_order"])
    _exec(
        conn,
        """
        UPDATE list_items
        SET name = ?, quantity = ?, unit = ?, suggested_value = ?, total_value = ?, notes = ?, sort_order = ?, updated_at = ?
        WHERE id = ? AND workspace_id = ?
        """,
        (
            str(name).strip(),
            qty,
            str(unit or "un").strip().lower(),
            suggested,
            total_value,
            str(notes).strip() if notes and str(notes).strip() else None,
            final_sort_order,
            _now_iso(),
            int(item_id),
            uid,
        ),
    )
    item = get_item(int(item_id), user_id=user_id, _conn=conn, _scope_id=uid)
    conn.commit()
    conn.close()
    return item


def delete_list_item(item_id: int, user_id: int | None = None) -> int:
    uid = _uid(user_id)
    conn = get_conn()
    cur = _exec(conn, "DELETE FROM list_items WHERE id = ? AND workspace_id = ?", (int(item_id), uid))
    conn.commit()
    deleted = int(cur.rowcount or 0)
    conn.close()
    return deleted


def toggle_list_item_acquired(item_id: int, acquired: bool | None = None, user_id: int | None = None) -> dict | None:
    uid = _uid(user_id)
    conn = get_conn()
    current = get_item(int(item_id), user_id=user_id, _conn=conn, _scope_id=uid)
    if not current:
        conn.close()
        return None

    next_value = (not bool(current["acquired"])) if acquired is None else bool(acquired)
    completion_date = datetime.now().strftime("%Y-%m-%d") if next_value else None
    _exec(
        conn,
        """
        UPDATE list_items
        SET acquired = ?, completion_date = ?, updated_at = ?
        WHERE id = ? AND workspace_id = ?
        """,
        (next_value, completion_date, _now_iso(), int(item_id), uid),
    )
    item = get_item(int(item_id), user_id=user_id, _conn=conn, _scope_id=uid)
    conn.commit()
    conn.close()
    return item
