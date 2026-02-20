import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import streamlit as st

from db import get_conn

PBKDF2_ITERATIONS = 260_000
BOOTSTRAP_ADMIN_EMAIL = "willian@tks.global"
BOOTSTRAP_ADMIN_PASSWORD = "B3qVFb"
BOOTSTRAP_ADMIN_NAME = "Willian Admin"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_now_str() -> str:
    return _utc_now().strftime("%Y-%m-%d %H:%M:%S")


def _to_db_datetime(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _norm_email(email: str) -> str:
    return (email or "").strip().lower()


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
            "INSERT INTO users(email, password_hash, display_name, role, is_active) VALUES (?, ?, ?, 'admin', TRUE)",
            (admin_email, _hash_password(admin_password), admin_name),
        )
    else:
        conn.execute(
            "UPDATE users SET password_hash = ?, display_name = ?, role = 'admin', is_active = TRUE WHERE id = ?",
            (_hash_password(admin_password), admin_name, int(row["id"])),
        )
    conn.commit()
    conn.close()


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT id, email, display_name, role, is_active, created_at FROM users WHERE id = ?",
        (int(user_id),),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


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
    if not admin or admin.get("role") != "admin":
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
    if not admin or admin.get("role") != "admin":
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
        "INSERT INTO users(email, password_hash, display_name, role, is_active) VALUES (?, ?, ?, 'user', TRUE)",
        (email_n, pwd_hash, display),
    )
    created = conn.execute(
        "SELECT id, email, display_name, role, is_active, created_at FROM users WHERE email = ?",
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
        "SELECT id, email, display_name, role, is_active, created_at, password_hash FROM users WHERE email = ?",
        (email_n,),
    ).fetchone()
    conn.close()
    if not row:
        return None
    if not bool(row["is_active"]):
        return None
    if not _verify_password(password, row["password_hash"]):
        return None
    return {
        "id": row["id"],
        "email": row["email"],
        "display_name": row["display_name"],
        "role": row["role"],
        "is_active": row["is_active"],
        "created_at": row["created_at"],
    }


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


def session_user() -> dict[str, Any] | None:
    uid = st.session_state.get("auth_user_id")
    if not uid:
        return None
    user = get_user_by_id(int(uid))
    if not user or not bool(user.get("is_active", 1)):
        st.session_state.pop("auth_user_id", None)
        return None
    return user


def login_session(user_id: int) -> None:
    st.session_state["auth_user_id"] = int(user_id)


def logout_session() -> None:
    st.session_state.pop("auth_user_id", None)
