import base64
import base64
import hashlib
import hmac
import os
import re
import secrets
from collections import deque
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any

from db import get_conn

PBKDF2_ITERATIONS = 260_000
BOOTSTRAP_ADMIN_EMAIL = "willian@tks.global"
BOOTSTRAP_ADMIN_PASSWORD = "B3qVFb"
BOOTSTRAP_ADMIN_NAME = "Willian Admin"
PASSWORD_RESET_TTL_MINUTES = max(15, min(30, int(os.getenv("PASSWORD_RESET_TTL_MINUTES", "30") or "30")))
PASSWORD_RESET_EMAIL_LIMIT_PER_HOUR = max(1, int(os.getenv("PASSWORD_RESET_EMAIL_LIMIT_PER_HOUR", "3") or "3"))
PASSWORD_RESET_IP_LIMIT_PER_HOUR = max(1, int(os.getenv("PASSWORD_RESET_IP_LIMIT_PER_HOUR", "10") or "10"))
PASSWORD_RESET_NEUTRAL_MESSAGE = "Se o e-mail existir, você receberá instruções para redefinir sua senha."

_PASSWORD_RESET_RATE_LOCK = Lock()
_PASSWORD_RESET_EMAIL_ATTEMPTS: dict[str, deque[float]] = {}
_PASSWORD_RESET_IP_ATTEMPTS: dict[str, deque[float]] = {}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_str() -> str:
    return _utc_now().strftime("%Y-%m-%d %H:%M:%S")


def _to_db_datetime(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _norm_email(email: str) -> str:
    return (email or "").strip().lower()


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(str(raw_token or "").encode("utf-8")).hexdigest()


def _password_strength_error(password: str) -> str | None:
    raw = str(password or "")
    if len(raw) < 8:
        return "A nova senha deve ter pelo menos 8 caracteres."
    if not re.search(r"[A-Za-z]", raw):
        return "A nova senha deve conter pelo menos uma letra."
    if not re.search(r"\d", raw):
        return "A nova senha deve conter pelo menos um numero."
    return None


def _check_password_change_allowed(new_password: str, current_hash: str) -> None:
    err = _password_strength_error(new_password)
    if err:
        raise ValueError(err)
    if _verify_password(new_password, str(current_hash or "")):
        raise ValueError("A nova senha nao pode ser igual a atual.")


def password_reset_public_message() -> str:
    return PASSWORD_RESET_NEUTRAL_MESSAGE


def _consume_recent_attempts(bucket: dict[str, deque[float]], key: str, limit: int) -> bool:
    if not key:
        return True
    now_ts = _utc_now().timestamp()
    cutoff = now_ts - 3600
    with _PASSWORD_RESET_RATE_LOCK:
        q = bucket.setdefault(key, deque())
        while q and q[0] < cutoff:
            q.popleft()
        if len(q) >= limit:
            return False
        q.append(now_ts)
        return True


def _global_role_from_legacy(role: str | None) -> str:
    raw = str(role or "").strip().lower()
    return "SUPER_ADMIN" if raw == "admin" else "USER"


def _legacy_role_from_global(global_role: str | None) -> str:
    raw = str(global_role or "").strip().upper()
    return "admin" if raw == "SUPER_ADMIN" else "user"


def _effective_global_role(user: dict[str, Any] | None) -> str:
    if not user:
        return "USER"
    raw = str((user.get("global_role") or "")).strip().upper()
    if raw in {"SUPER_ADMIN", "USER"}:
        return raw
    return _global_role_from_legacy(str(user.get("role") or ""))


def _workspace_default_name(email: str | None, user_id: int) -> str:
    base = (str(email or "").strip().split("@", 1)[0] or "").strip()
    if not base:
        base = f"Usuario {int(user_id)}"
    return f"Workspace {base}"


def _hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return (
        f"pbkdf2_sha256${PBKDF2_ITERATIONS}$"
        f"{base64.b64encode(salt).decode('ascii')}$"
        f"{base64.b64encode(dk).decode('ascii')}"
    )


def _verify_password(password: str, encoded: str) -> bool:
    try:
        algo, iters, b64_salt, b64_hash = encoded.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        salt = base64.b64decode(b64_salt.encode("ascii"))
        expected = base64.b64decode(b64_hash.encode("ascii"))
        got = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iters))
        return hmac.compare_digest(got, expected)
    except Exception:
        return False


def count_users() -> int:
    conn = get_conn()
    row = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()
    conn.close()
    return int(row["n"] if row else 0)


def ensure_bootstrap_admin() -> None:
    admin_email = _norm_email(os.getenv("ADMIN_BOOTSTRAP_EMAIL", BOOTSTRAP_ADMIN_EMAIL))
    admin_password = os.getenv("ADMIN_BOOTSTRAP_PASSWORD", BOOTSTRAP_ADMIN_PASSWORD)
    admin_name = (os.getenv("ADMIN_BOOTSTRAP_NAME", BOOTSTRAP_ADMIN_NAME) or "").strip() or BOOTSTRAP_ADMIN_NAME

    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM users WHERE email = ?",
        (admin_email,),
    ).fetchone()
    if not row:
        conn.execute(
            """
            INSERT INTO users(email, password_hash, display_name, role, global_role, is_active)
            VALUES (?, ?, ?, 'admin', 'SUPER_ADMIN', TRUE)
            """,
            (admin_email, _hash_password(admin_password), admin_name),
        )
    else:
        conn.execute(
            """
            UPDATE users
            SET password_hash = ?, display_name = ?, role = 'admin', global_role = 'SUPER_ADMIN', is_active = TRUE,
                token_version = COALESCE(token_version, 0) + 1,
                password_changed_at = ?
            WHERE id = ?
            """,
            (_hash_password(admin_password), admin_name, _utc_now_str(), int(row["id"])),
        )
    conn.commit()
    conn.close()


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    conn = get_conn()
    row = conn.execute(
        """
        SELECT id, email, display_name, avatar_data, role, global_role, is_active, created_at
               , token_version, password_changed_at
        FROM users
        WHERE id = ?
        """,
        (int(user_id),),
    ).fetchone()
    conn.close()
    if not row:
        return None
    user = dict(row)
    user["global_role"] = _effective_global_role(user)
    user["role"] = _legacy_role_from_global(user["global_role"])
    return user


def get_user_by_email(email: str) -> dict[str, Any] | None:
    email_n = _norm_email(email)
    if not email_n:
        return None
    conn = get_conn()
    row = conn.execute(
        """
        SELECT id, email, display_name, avatar_data, role, global_role, is_active, created_at
               , token_version, password_changed_at
        FROM users
        WHERE email = ?
        """,
        (email_n,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    user = dict(row)
    user["global_role"] = _effective_global_role(user)
    user["role"] = _legacy_role_from_global(user["global_role"])
    return user


def create_user(
    *,
    email: str,
    password: str | None = None,
    display_name: str | None = None,
    global_role: str = "USER",
) -> dict[str, Any]:
    email_n = _norm_email(email)
    if "@" not in email_n or "." not in email_n:
        raise ValueError("Informe um e-mail válido.")
    raw_password = str(password or "")
    if raw_password and len(raw_password) < 6:
        raise ValueError("A senha deve ter pelo menos 6 caracteres.")
    if not raw_password:
        raw_password = secrets.token_urlsafe(24)

    role_n = str(global_role or "").strip().upper() or "USER"
    if role_n not in {"USER", "SUPER_ADMIN"}:
        raise ValueError("Global role inválido.")

    existing = get_user_by_email(email_n)
    if existing:
        raise ValueError("Este e-mail já está cadastrado.")

    display = (display_name or "").strip() or None
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO users(email, password_hash, display_name, role, global_role, is_active)
        VALUES (?, ?, ?, ?, ?, TRUE)
        """,
        (email_n, _hash_password(raw_password), display, _legacy_role_from_global(role_n), role_n),
    )
    conn.commit()
    conn.close()

    created = get_user_by_email(email_n)
    if not created:
        raise ValueError("Falha ao criar usuário.")
    return created


def get_workspace_by_id(workspace_id: int) -> dict[str, Any] | None:
    conn = get_conn()
    row = conn.execute(
        """
        SELECT id AS workspace_id, name AS workspace_name, owner_user_id, status, created_at
        FROM workspaces
        WHERE id = ?
        """,
        (int(workspace_id),),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_workspace_membership(user_id: int, workspace_id: int) -> dict[str, Any] | None:
    conn = get_conn()
    row = conn.execute(
        """
        SELECT
            wu.id AS workspace_user_id,
            wu.workspace_id,
            wu.user_id,
            wu.role AS workspace_role,
            w.name AS workspace_name,
            w.status AS workspace_status,
            w.owner_user_id
        FROM workspace_users wu
        JOIN workspaces w ON w.id = wu.workspace_id
        WHERE wu.user_id = ? AND wu.workspace_id = ?
        LIMIT 1
        """,
        (int(user_id), int(workspace_id)),
    ).fetchone()
    conn.close()
    if not row:
        return None
    member = dict(row)
    member["workspace_role"] = str(member.get("workspace_role") or "").strip().upper() or "GUEST"
    member["workspace_status"] = str(member.get("workspace_status") or "").strip().lower() or "active"
    return member


def list_user_workspaces(user_id: int, active_only: bool = False) -> list[dict[str, Any]]:
    conn = get_conn()
    where_status = " AND LOWER(COALESCE(w.status, 'active')) = 'active'" if active_only else ""
    rows = conn.execute(
        f"""
        SELECT
            w.id AS workspace_id,
            w.name AS workspace_name,
            w.owner_user_id,
            w.status AS workspace_status,
            wu.role AS workspace_role
        FROM workspace_users wu
        JOIN workspaces w ON w.id = wu.workspace_id
        WHERE wu.user_id = ? {where_status}
        ORDER BY
            CASE WHEN UPPER(COALESCE(wu.role, '')) = 'OWNER' THEN 0 ELSE 1 END,
            w.id
        """,
        (int(user_id),),
    ).fetchall()
    conn.close()
    out: list[dict[str, Any]] = []
    for r in rows:
        d = dict(r)
        d["workspace_role"] = str(d.get("workspace_role") or "").strip().upper() or "GUEST"
        d["workspace_status"] = str(d.get("workspace_status") or "").strip().lower() or "active"
        out.append(d)
    return out


def list_all_workspaces() -> list[dict[str, Any]]:
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT
            w.id AS workspace_id,
            w.name AS workspace_name,
            w.owner_user_id,
            w.status AS workspace_status,
            u.email AS owner_email,
            u.display_name AS owner_display_name,
            (
                SELECT COUNT(*)
                FROM workspace_users wu
                WHERE wu.workspace_id = w.id
            ) AS members_count
        FROM workspaces w
        LEFT JOIN users u ON u.id = w.owner_user_id
        ORDER BY
            CASE WHEN LOWER(COALESCE(w.status, 'active')) = 'active' THEN 0 ELSE 1 END,
            w.id
        """
    ).fetchall()
    conn.close()
    out: list[dict[str, Any]] = []
    for r in rows:
        d = dict(r)
        d["workspace_status"] = str(d.get("workspace_status") or "").strip().lower() or "active"
        out.append(d)
    return out


def create_workspace_with_owner(
    owner_user_id: int,
    workspace_name: str,
    created_by: int | None = None,
) -> dict[str, Any] | None:
    owner_id = int(owner_user_id)
    name = str(workspace_name or "").strip()
    if not name:
        raise ValueError("Nome do workspace é obrigatório.")

    conn = get_conn()
    owner = conn.execute(
        """
        SELECT id, email, is_active
        FROM users
        WHERE id = ?
        LIMIT 1
        """,
        (owner_id,),
    ).fetchone()
    if not owner:
        conn.close()
        raise ValueError("Owner informado não existe.")
    if not bool(owner["is_active"]):
        conn.close()
        raise ValueError("Owner informado está inativo.")

    ws_row = conn.execute(
        """
        INSERT INTO workspaces(name, owner_user_id, status)
        VALUES (?, ?, 'active')
        RETURNING id AS workspace_id
        """,
        (name, owner_id),
    ).fetchone()
    ws_id = int(ws_row["workspace_id"]) if ws_row else 0
    if ws_id <= 0:
        conn.rollback()
        conn.close()
        return None

    creator = int(created_by) if created_by is not None else owner_id
    conn.execute(
        """
        INSERT OR IGNORE INTO workspace_users(workspace_id, user_id, role, created_by)
        VALUES (?, ?, 'OWNER', ?)
        """,
        (ws_id, owner_id, creator),
    )
    conn.execute(
        """
        UPDATE workspace_users
        SET role = 'OWNER'
        WHERE workspace_id = ? AND user_id = ?
        """,
        (ws_id, owner_id),
    )
    conn.commit()
    conn.close()

    return get_workspace_by_id(ws_id)


def update_workspace_status(workspace_id: int, status: str) -> dict[str, Any] | None:
    ws_id = int(workspace_id)
    status_n = str(status or "").strip().lower()
    if status_n not in {"active", "blocked"}:
        raise ValueError("Status do workspace inválido.")

    conn = get_conn()
    cur = conn.execute(
        "UPDATE workspaces SET status = ? WHERE id = ?",
        (status_n, ws_id),
    )
    conn.commit()
    conn.close()
    if int(cur.rowcount or 0) <= 0:
        return None
    return get_workspace_by_id(ws_id)


def update_workspace_name(workspace_id: int, workspace_name: str) -> dict[str, Any] | None:
    ws_id = int(workspace_id)
    name = str(workspace_name or "").strip()
    if not name:
        raise ValueError("Nome do workspace é obrigatório.")
    if len(name) < 3:
        raise ValueError("Nome do workspace deve ter pelo menos 3 caracteres.")

    conn = get_conn()
    cur = conn.execute(
        "UPDATE workspaces SET name = ? WHERE id = ?",
        (name, ws_id),
    )
    conn.commit()
    conn.close()
    if int(cur.rowcount or 0) <= 0:
        return None
    return get_workspace_by_id(ws_id)


def set_user_global_role(user_id: int, global_role: str) -> dict[str, Any] | None:
    uid = int(user_id)
    role_n = str(global_role or "").strip().upper()
    if role_n not in {"SUPER_ADMIN", "USER"}:
        raise ValueError("Global role inválido.")
    legacy = _legacy_role_from_global(role_n)

    conn = get_conn()
    cur = conn.execute(
        """
        UPDATE users
        SET global_role = ?, role = ?
        WHERE id = ?
        """,
        (role_n, legacy, uid),
    )
    conn.commit()
    conn.close()
    if int(cur.rowcount or 0) <= 0:
        return None
    return get_user_by_id(uid)


def ensure_default_workspace_for_user(user_id: int) -> dict[str, Any] | None:
    uid = int(user_id)
    conn = get_conn()

    row = conn.execute(
        """
        SELECT
            wu.id AS workspace_user_id,
            wu.workspace_id,
            wu.user_id,
            wu.role AS workspace_role,
            w.name AS workspace_name,
            w.status AS workspace_status,
            w.owner_user_id
        FROM workspace_users wu
        JOIN workspaces w ON w.id = wu.workspace_id
        WHERE wu.user_id = ?
        ORDER BY
            CASE WHEN LOWER(COALESCE(w.status, 'active')) = 'active' THEN 0 ELSE 1 END,
            CASE WHEN UPPER(COALESCE(wu.role, '')) = 'OWNER' THEN 0 ELSE 1 END,
            w.id
        LIMIT 1
        """,
        (uid,),
    ).fetchone()
    if row:
        conn.close()
        member = dict(row)
        member["workspace_role"] = str(member.get("workspace_role") or "").strip().upper() or "GUEST"
        member["workspace_status"] = str(member.get("workspace_status") or "").strip().lower() or "active"
        return member
    conn.close()
    return None


def list_workspace_members(workspace_id: int) -> list[dict[str, Any]]:
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT
            wu.id AS workspace_user_id,
            wu.workspace_id,
            wu.user_id,
            wu.role AS workspace_role,
            wu.created_by,
            wu.created_at,
            u.email,
            u.display_name,
            u.is_active
        FROM workspace_users wu
        JOIN users u ON u.id = wu.user_id
        WHERE wu.workspace_id = ?
        ORDER BY
            CASE WHEN UPPER(COALESCE(wu.role, '')) = 'OWNER' THEN 0 ELSE 1 END,
            LOWER(COALESCE(u.email, '')),
            wu.user_id
        """,
        (int(workspace_id),),
    ).fetchall()
    conn.close()
    out: list[dict[str, Any]] = []
    for r in rows:
        d = dict(r)
        d["workspace_role"] = str(d.get("workspace_role") or "").strip().upper() or "GUEST"
        out.append(d)
    return out


def upsert_workspace_member(
    workspace_id: int,
    user_id: int,
    role: str = "GUEST",
    created_by: int | None = None,
) -> dict[str, Any] | None:
    ws_id = int(workspace_id)
    uid = int(user_id)
    role_n = str(role or "").strip().upper() or "GUEST"
    if role_n not in {"OWNER", "GUEST"}:
        raise ValueError("Role de workspace inválida.")

    conn = get_conn()
    conn.execute(
        """
        INSERT OR IGNORE INTO workspace_users(workspace_id, user_id, role, created_by)
        VALUES (?, ?, ?, ?)
        """,
        (ws_id, uid, role_n, int(created_by) if created_by is not None else None),
    )
    conn.execute(
        """
        UPDATE workspace_users
        SET role = ?
        WHERE workspace_id = ? AND user_id = ?
        """,
        (role_n, ws_id, uid),
    )
    conn.commit()
    row = conn.execute(
        """
        SELECT
            wu.id AS workspace_user_id,
            wu.workspace_id,
            wu.user_id,
            wu.role AS workspace_role,
            wu.created_by,
            wu.created_at
        FROM workspace_users wu
        WHERE wu.workspace_id = ? AND wu.user_id = ?
        LIMIT 1
        """,
        (ws_id, uid),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_workspace_member(workspace_id: int, user_id: int) -> int:
    conn = get_conn()
    cur = conn.execute(
        "DELETE FROM workspace_users WHERE workspace_id = ? AND user_id = ?",
        (int(workspace_id), int(user_id)),
    )
    conn.commit()
    conn.close()
    return int(cur.rowcount or 0)


def _load_invite(token: str) -> dict[str, Any] | None:
    conn = get_conn()
    row = conn.execute(
        """
        SELECT id, token, invited_email, created_by, used_by, expires_at, used_at, created_at
        FROM invites
        WHERE token = ?
        """,
        (token.strip(),),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def validate_invite(token: str, email: str | None = None) -> tuple[bool, str, dict[str, Any] | None]:
    invite = _load_invite(token)
    if not invite:
        return False, "Convite inválido.", None
    if invite.get("used_by") is not None or invite.get("used_at"):
        return False, "Convite já foi utilizado.", None
    exp = str(invite["expires_at"]).replace("T", " ").split(".")[0]
    if exp <= _utc_now_str():
        return False, "Convite expirado.", None

    invited_email = (invite.get("invited_email") or "").strip().lower()
    if invited_email and email and invited_email != _norm_email(email):
        return False, "Este convite foi emitido para outro e-mail.", None
    return True, "Convite válido.", invite


def create_invite(admin_user_id: int, invited_email: str | None = None, expires_days: int = 7) -> tuple[bool, str, dict[str, Any] | None]:
    admin = get_user_by_id(int(admin_user_id))
    if not admin or _effective_global_role(admin) != "SUPER_ADMIN":
        return False, "Somente admin pode gerar convite.", None

    token = secrets.token_urlsafe(24)
    email_n = _norm_email(invited_email) if invited_email else None
    if email_n == "":
        email_n = None
    days = max(1, min(int(expires_days or 7), 60))
    expires_at = _to_db_datetime(_utc_now() + timedelta(days=days))

    conn = get_conn()
    conn.execute(
        """
        INSERT INTO invites(token, invited_email, created_by, expires_at)
        VALUES (?, ?, ?, ?)
        """,
        (token, email_n, int(admin_user_id), expires_at),
    )
    conn.commit()
    row = conn.execute(
        """
        SELECT id, token, invited_email, created_by, used_by, expires_at, used_at, created_at
        FROM invites
        WHERE token = ?
        """,
        (token,),
    ).fetchone()
    conn.close()
    return True, "Convite criado com sucesso.", dict(row) if row else None


def list_recent_invites(admin_user_id: int, limit: int = 20) -> list[dict[str, Any]]:
    admin = get_user_by_id(int(admin_user_id))
    if not admin or _effective_global_role(admin) != "SUPER_ADMIN":
        return []
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT id, token, invited_email, created_by, used_by, expires_at, used_at, created_at
        FROM invites
        ORDER BY id DESC
        LIMIT ?
        """,
        (int(limit),),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def register_user_with_invite(
    invite_token: str,
    email: str,
    password: str,
    display_name: str | None = None,
) -> tuple[bool, str, dict[str, Any] | None]:
    email_n = _norm_email(email)
    display = (display_name or "").strip() or None

    if "@" not in email_n or "." not in email_n:
        return False, "Informe um e-mail válido.", None
    if len(password or "") < 6:
        return False, "A senha deve ter pelo menos 6 caracteres.", None

    ok, msg, invite = validate_invite(invite_token, email_n)
    if not ok:
        return False, msg, None

    conn = get_conn()
    exists = conn.execute("SELECT id FROM users WHERE email = ?", (email_n,)).fetchone()
    if exists:
        conn.close()
        return False, "Este e-mail já está cadastrado.", None

    pwd_hash = _hash_password(password)
    conn.execute(
        """
        INSERT INTO users(email, password_hash, display_name, role, global_role, is_active)
        VALUES (?, ?, ?, 'user', 'USER', TRUE)
        """,
        (email_n, pwd_hash, display),
    )
    created = conn.execute(
        """
        SELECT id, email, display_name, role, global_role, is_active, created_at
        FROM users
        WHERE email = ?
        """,
        (email_n,),
    ).fetchone()
    conn.execute(
        "UPDATE invites SET used_by = ?, used_at = ? WHERE id = ?",
        (int(created["id"]), _utc_now_str(), int(invite["id"])),
    )
    conn.commit()
    conn.close()
    return True, "Usuário criado com sucesso.", dict(created) if created else None


def authenticate_user(email: str, password: str) -> dict[str, Any] | None:
    email_n = _norm_email(email)
    conn = get_conn()
    row = conn.execute(
        """
        SELECT id, email, display_name, avatar_data, role, global_role, is_active, created_at, password_hash
               , token_version, password_changed_at
        FROM users
        WHERE email = ?
        """,
        (email_n,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    if not bool(row["is_active"]):
        return None
    if not _verify_password(password, row["password_hash"]):
        return None
    user = {
        "id": row["id"],
        "email": row["email"],
        "display_name": row["display_name"],
        "avatar_data": row["avatar_data"],
        "role": row["role"],
        "global_role": row["global_role"],
        "is_active": row["is_active"],
        "created_at": row["created_at"],
        "token_version": row["token_version"],
        "password_changed_at": row["password_changed_at"],
    }
    user["global_role"] = _effective_global_role(user)
    user["role"] = _legacy_role_from_global(user["global_role"])
    return user


def update_user_profile(
    *,
    user_id: int,
    email: str,
    display_name: str | None = None,
    current_password: str | None = None,
    new_password: str | None = None,
    avatar_data: str | None = None,
) -> dict[str, Any]:
    uid = int(user_id)
    email_n = _norm_email(email)
    if "@" not in email_n or "." not in email_n:
        raise ValueError("Informe um e-mail válido.")

    display = (display_name or "").strip() or None
    current_pwd = str(current_password or "")
    new_pwd = str(new_password or "")
    avatar = str(avatar_data or "").strip() or None
    if avatar and not avatar.startswith("data:image/"):
        raise ValueError("Avatar inválido. Envie uma imagem compatível.")
    if avatar and len(avatar) > 2_000_000:
        raise ValueError("Avatar muito grande. Use uma imagem menor.")

    conn = get_conn()
    row = conn.execute(
        """
        SELECT id, email, password_hash
        FROM users
        WHERE id = ?
        LIMIT 1
        """,
        (uid,),
    ).fetchone()
    if not row:
        conn.close()
        raise ValueError("Usuário não encontrado.")

    existing = conn.execute(
        """
        SELECT id
        FROM users
        WHERE email = ? AND id <> ?
        LIMIT 1
        """,
        (email_n, uid),
    ).fetchone()
    if existing:
        conn.close()
        raise ValueError("Este e-mail já está cadastrado.")

    fields = ["email = ?", "display_name = ?", "avatar_data = ?"]
    params: list[Any] = [email_n, display, avatar]

    if new_pwd:
        if len(new_pwd) < 6:
            conn.close()
            raise ValueError("A nova senha deve ter pelo menos 8 caracteres.")
        if not current_pwd:
            conn.close()
            raise ValueError("Informe a senha atual para alterar a senha.")
        if not _verify_password(current_pwd, str(row["password_hash"] or "")):
            conn.close()
            raise ValueError("Senha atual inválida.")
        try:
            _check_password_change_allowed(new_pwd, str(row["password_hash"] or ""))
        except ValueError as e:
            conn.close()
            raise
        fields.append("password_hash = ?")
        params.append(_hash_password(new_pwd))
        fields.append("token_version = COALESCE(token_version, 0) + 1")
        fields.append("password_changed_at = ?")
        params.append(_utc_now_str())

    params.append(uid)
    conn.execute(
        f"""
        UPDATE users
        SET {", ".join(fields)}
        WHERE id = ?
        """,
        tuple(params),
    )
    conn.commit()
    conn.close()

    updated = get_user_by_id(uid)
    if not updated:
        raise ValueError("Falha ao atualizar perfil.")
    return updated


def create_password_reset_request(
    *,
    email: str,
    request_ip: str | None = None,
    request_user_agent: str | None = None,
) -> str | None:
    email_n = _norm_email(email)
    if not email_n:
        return None
    if not _consume_recent_attempts(_PASSWORD_RESET_EMAIL_ATTEMPTS, email_n, PASSWORD_RESET_EMAIL_LIMIT_PER_HOUR):
        return None
    ip = str(request_ip or "").strip()
    if ip and not _consume_recent_attempts(_PASSWORD_RESET_IP_ATTEMPTS, ip, PASSWORD_RESET_IP_LIMIT_PER_HOUR):
        return None

    user = get_user_by_email(email_n)
    if not user or not bool(user.get("is_active", True)):
        return None

    uid = int(user["id"])
    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)
    now_s = _utc_now_str()
    expires_at = _to_db_datetime(_utc_now() + timedelta(minutes=PASSWORD_RESET_TTL_MINUTES))

    conn = get_conn()
    conn.execute(
        """
        UPDATE password_reset_tokens
        SET used_at = ?, consumed_user_agent = ?
        WHERE user_id = ? AND used_at IS NULL
        """,
        (now_s, "superseded", uid),
    )
    conn.execute(
        """
        INSERT INTO password_reset_tokens(
            user_id, token_hash, expires_at, requested_ip, requested_user_agent
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (uid, token_hash, expires_at, ip or None, str(request_user_agent or "").strip() or None),
    )
    conn.commit()
    conn.close()
    return raw_token


def reset_password_with_token(
    *,
    token: str,
    new_password: str,
    request_ip: str | None = None,
    request_user_agent: str | None = None,
) -> dict[str, Any]:
    token_hash = _hash_token(token)
    conn = get_conn()
    row = conn.execute(
        """
        SELECT
            prt.id,
            prt.user_id,
            prt.expires_at,
            prt.used_at,
            u.email,
            u.display_name,
            u.avatar_data,
            u.role,
            u.global_role,
            u.is_active,
            u.created_at,
            u.password_hash,
            u.token_version,
            u.password_changed_at
        FROM password_reset_tokens prt
        JOIN users u ON u.id = prt.user_id
        WHERE prt.token_hash = ?
        LIMIT 1
        """,
        (token_hash,),
    ).fetchone()
    if not row:
        conn.close()
        raise ValueError("Token invalido ou expirado.")
    if row["used_at"]:
        conn.close()
        raise ValueError("Token invalido ou expirado.")
    exp = str(row["expires_at"]).replace("T", " ").split(".")[0]
    if exp < _utc_now_str():
        conn.close()
        raise ValueError("Token invalido ou expirado.")
    if not bool(row["is_active"]):
        conn.close()
        raise ValueError("Usuario inativo.")

    _check_password_change_allowed(new_password, str(row["password_hash"] or ""))
    now_s = _utc_now_str()
    uid = int(row["user_id"])
    conn.execute(
        """
        UPDATE users
        SET password_hash = ?, token_version = COALESCE(token_version, 0) + 1, password_changed_at = ?
        WHERE id = ?
        """,
        (_hash_password(new_password), now_s, uid),
    )
    conn.execute(
        """
        UPDATE password_reset_tokens
        SET used_at = ?, consumed_ip = ?, consumed_user_agent = ?
        WHERE id = ?
        """,
        (now_s, str(request_ip or "").strip() or None, str(request_user_agent or "").strip() or None, int(row["id"])),
    )
    conn.execute(
        """
        UPDATE password_reset_tokens
        SET used_at = ?, consumed_user_agent = ?
        WHERE user_id = ? AND used_at IS NULL
        """,
        (now_s, "password_changed", uid),
    )
    conn.commit()
    conn.close()

    updated = get_user_by_id(uid)
    if not updated:
        raise ValueError("Usuario nao encontrado.")
    return updated


def claim_legacy_data_for_user(user_id: int) -> None:
    uid = int(user_id)
    conn = get_conn()
    conn.execute("UPDATE accounts SET user_id = ? WHERE user_id IS NULL", (uid,))
    conn.execute("UPDATE categories SET user_id = ? WHERE user_id IS NULL", (uid,))
    conn.execute("UPDATE transactions SET user_id = ? WHERE user_id IS NULL", (uid,))
    conn.execute("UPDATE assets SET user_id = ? WHERE user_id IS NULL", (uid,))
    conn.execute("UPDATE trades SET user_id = ? WHERE user_id IS NULL", (uid,))
    conn.execute("UPDATE income_events SET user_id = ? WHERE user_id IS NULL", (uid,))
    conn.execute("UPDATE prices SET user_id = ? WHERE user_id IS NULL", (uid,))
    conn.execute("UPDATE asset_prices SET user_id = ? WHERE user_id IS NULL", (uid,))
    conn.commit()
    conn.close()
