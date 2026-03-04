from contextvars import ContextVar

_current_user_id: ContextVar[int | None] = ContextVar("current_user_id", default=None)
_current_workspace_id: ContextVar[int | None] = ContextVar("current_workspace_id", default=None)
_current_workspace_role: ContextVar[str | None] = ContextVar("current_workspace_role", default=None)
_current_global_role: ContextVar[str | None] = ContextVar("current_global_role", default=None)


def set_current_user_id(user_id: int) -> None:
    _current_user_id.set(int(user_id))


def clear_current_user_id() -> None:
    _current_user_id.set(None)


def get_current_user_id(required: bool = True) -> int | None:
    uid = _current_user_id.get()
    if uid is None and required:
        raise RuntimeError("Usuário não autenticado.")
    return uid


def set_current_workspace_id(workspace_id: int) -> None:
    _current_workspace_id.set(int(workspace_id))


def clear_current_workspace_id() -> None:
    _current_workspace_id.set(None)


def get_current_workspace_id(required: bool = False) -> int | None:
    wid = _current_workspace_id.get()
    if wid is None and required:
        raise RuntimeError("Workspace não definido no contexto atual.")
    return wid


def set_current_workspace_role(workspace_role: str | None) -> None:
    role = str(workspace_role or "").strip().upper() or None
    _current_workspace_role.set(role)


def clear_current_workspace_role() -> None:
    _current_workspace_role.set(None)


def get_current_workspace_role(required: bool = False) -> str | None:
    role = _current_workspace_role.get()
    if role is None and required:
        raise RuntimeError("Role do workspace não definida no contexto atual.")
    return role


def set_current_global_role(global_role: str | None) -> None:
    role = str(global_role or "").strip().upper() or None
    _current_global_role.set(role)


def clear_current_global_role() -> None:
    _current_global_role.set(None)


def get_current_global_role(required: bool = False) -> str | None:
    role = _current_global_role.get()
    if role is None and required:
        raise RuntimeError("Role global não definida no contexto atual.")
    return role


def clear_tenant_context() -> None:
    clear_current_user_id()
    clear_current_workspace_id()
    clear_current_workspace_role()
    clear_current_global_role()
