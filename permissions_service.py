from __future__ import annotations

from typing import Any

from db import get_conn


MODULES = {"dashboard", "lancamentos", "investimentos", "relatorios", "contas", "usuarios"}
ACTIONS = {"view", "add", "edit", "delete"}
DEFAULT_GUEST_PERMISSIONS: dict[str, dict[str, bool]] = {
    "dashboard": {"view": True, "add": False, "edit": False, "delete": False},
    "lancamentos": {"view": True, "add": False, "edit": False, "delete": False},
    "investimentos": {"view": True, "add": False, "edit": False, "delete": False},
    "relatorios": {"view": True, "add": False, "edit": False, "delete": False},
    "contas": {"view": True, "add": False, "edit": False, "delete": False},
    "usuarios": {"view": False, "add": False, "edit": False, "delete": False},
}


def _norm_global_role(value: Any) -> str:
    raw = str(value or "").strip().upper()
    if raw in {"SUPER_ADMIN", "USER"}:
        return raw
    return "SUPER_ADMIN" if str(value or "").strip().lower() == "admin" else "USER"


def _norm_workspace_role(value: Any) -> str:
    raw = str(value or "").strip().upper()
    if raw in {"OWNER", "GUEST"}:
        return raw
    return "GUEST"


def _action_column(action: str) -> str:
    act = str(action or "").strip().lower()
    if act == "view":
        return "can_view"
    if act == "add":
        return "can_add"
    if act == "edit":
        return "can_edit"
    if act == "delete":
        return "can_delete"
    raise ValueError(f"Ação inválida: {action}")


def _workspace_user_id(user_id: int, workspace_id: int) -> int | None:
    conn = get_conn()
    row = conn.execute(
        """
        SELECT id
        FROM workspace_users
        WHERE user_id = ? AND workspace_id = ?
        LIMIT 1
        """,
        (int(user_id), int(workspace_id)),
    ).fetchone()
    conn.close()
    if not row:
        return None
    try:
        return int(row["id"])
    except Exception:
        return int(row[0])


def _norm_module(module: str) -> str:
    mod = str(module or "").strip().lower()
    if mod not in MODULES:
        raise ValueError(f"Módulo inválido: {module}")
    return mod


def _to_flag(value: Any) -> int:
    return 1 if bool(value) else 0


def get_workspace_user(workspace_id: int, user_id: int) -> dict[str, Any] | None:
    conn = get_conn()
    row = conn.execute(
        """
        SELECT id, workspace_id, user_id, role, created_by, created_at
        FROM workspace_users
        WHERE workspace_id = ? AND user_id = ?
        LIMIT 1
        """,
        (int(workspace_id), int(user_id)),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def list_permissions_by_workspace_user(workspace_user_id: int) -> list[dict[str, Any]]:
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT module, can_view, can_add, can_edit, can_delete
        FROM permissions
        WHERE workspace_user_id = ?
        ORDER BY module
        """,
        (int(workspace_user_id),),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def upsert_permission(
    workspace_user_id: int,
    module: str,
    *,
    can_view: bool = False,
    can_add: bool = False,
    can_edit: bool = False,
    can_delete: bool = False,
) -> None:
    mod = _norm_module(module)
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO permissions(
            workspace_user_id, module, can_view, can_add, can_edit, can_delete
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(workspace_user_id, module) DO UPDATE SET
            can_view = excluded.can_view,
            can_add = excluded.can_add,
            can_edit = excluded.can_edit,
            can_delete = excluded.can_delete
        """,
        (
            int(workspace_user_id),
            mod,
            _to_flag(can_view),
            _to_flag(can_add),
            _to_flag(can_edit),
            _to_flag(can_delete),
        ),
    )
    conn.commit()
    conn.close()


def seed_default_guest_permissions(workspace_user_id: int) -> None:
    conn = get_conn()
    for module, rules in DEFAULT_GUEST_PERMISSIONS.items():
        conn.execute(
            """
            INSERT INTO permissions(
                workspace_user_id, module, can_view, can_add, can_edit, can_delete
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(workspace_user_id, module) DO NOTHING
            """,
            (
                int(workspace_user_id),
                str(module),
                _to_flag(rules.get("view")),
                _to_flag(rules.get("add")),
                _to_flag(rules.get("edit")),
                _to_flag(rules.get("delete")),
            ),
        )
    conn.commit()
    conn.close()


def replace_permissions(workspace_user_id: int, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items or []:
        mod = _norm_module(str((item or {}).get("module") or ""))
        if mod in seen:
            continue
        seen.add(mod)
        normalized.append(
            {
                "module": mod,
                "can_view": bool((item or {}).get("can_view", False)),
                "can_add": bool((item or {}).get("can_add", False)),
                "can_edit": bool((item or {}).get("can_edit", False)),
                "can_delete": bool((item or {}).get("can_delete", False)),
            }
        )

    conn = get_conn()
    conn.execute("DELETE FROM permissions WHERE workspace_user_id = ?", (int(workspace_user_id),))
    for item in normalized:
        conn.execute(
            """
            INSERT INTO permissions(
                workspace_user_id, module, can_view, can_add, can_edit, can_delete
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                int(workspace_user_id),
                str(item["module"]),
                _to_flag(item["can_view"]),
                _to_flag(item["can_add"]),
                _to_flag(item["can_edit"]),
                _to_flag(item["can_delete"]),
            ),
        )
    conn.commit()
    conn.close()
    return normalized


def delete_permissions_for_workspace_user(workspace_user_id: int) -> int:
    conn = get_conn()
    cur = conn.execute(
        "DELETE FROM permissions WHERE workspace_user_id = ?",
        (int(workspace_user_id),),
    )
    conn.commit()
    conn.close()
    return int(cur.rowcount or 0)


def can_access(user: dict[str, Any], module: str, action: str) -> bool:
    mod = str(module or "").strip().lower()
    act = str(action or "").strip().lower()
    if mod not in MODULES or act not in ACTIONS:
        return False

    global_role = _norm_global_role(user.get("global_role"))
    if global_role == "SUPER_ADMIN":
        return True

    workspace_role = _norm_workspace_role(user.get("workspace_role"))
    if workspace_role == "OWNER":
        return True

    if workspace_role != "GUEST":
        return False

    if mod == "usuarios":
        return False

    workspace_id = user.get("workspace_id")
    user_id = user.get("id")
    if workspace_id is None or user_id is None:
        return False

    wu_id = _workspace_user_id(int(user_id), int(workspace_id))
    if not wu_id:
        return False

    col = _action_column(act)
    conn = get_conn()
    row = conn.execute(
        f"""
        SELECT {col} AS allowed
        FROM permissions
        WHERE workspace_user_id = ?
          AND LOWER(COALESCE(module, '')) = ?
        LIMIT 1
        """,
        (int(wu_id), mod),
    ).fetchone()
    conn.close()
    if not row:
        return False
    try:
        return bool(row["allowed"])
    except Exception:
        return bool(row[0])
