from __future__ import annotations

import os
import calendar
from typing import Any
from datetime import date as _date
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware

import auth
import api.importers as importers
import invest_index_rates
import invest_rentability
import invest_repo
import invest_reports
import invest_quotes
import repo
import reports
import permissions_service
import security_monitor
from db import get_conn, init_db
from tenant import (
    clear_tenant_context,
    set_current_global_role,
    set_current_user_id,
    set_current_workspace_id,
    set_current_workspace_role,
)

from .schemas import (
    AccountCreateRequest,
    AccountUpdateRequest,
    AssetCreateRequest,
    AssetUpdateRequest,
    CategoryCreateRequest,
    CategoryUpdateRequest,
    CreditCardCreateRequest,
    CreditCardPayInvoiceRequest,
    CreditCardUpdateRequest,
    CommitmentSettleRequest,
    LoginRequest,
    LoginResponse,
    UserGlobalRoleUpdateRequest,
    WorkspaceAdminCreateRequest,
    WorkspaceMemberCreateRequest,
    WorkspacePermissionItemRequest,
    WorkspacePermissionsUpdateRequest,
    WorkspaceStatusUpdateRequest,
    WorkspaceSwitchRequest,
    IncomeCreateRequest,
    IndexRatesSyncRequest,
    IndexRatesUpsertRequest,
    PriceUpsertRequest,
    QuoteUpdateAllRequest,
    RentabilityDivergenceRequest,
    RentabilityUpdateRequest,
    TradeCreateRequest,
    TransactionCreateRequest,
)
from .security import create_token, verify_token


app = FastAPI(title="Controle Financeiro API", version="0.1.0")
VALID_VIEWS = {"caixa", "competencia", "futuro"}


def _cors_origins() -> list[str]:
    raw = (os.getenv("CORS_ORIGINS") or "").strip()
    if raw:
        return [o.strip() for o in raw.split(",") if o.strip()]
    return [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    # Tolerate local dev variations (localhost/127.0.0.1 with any port, optional trailing slash).
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?/?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    auth.ensure_bootstrap_admin()


def _row_to_dict(row: Any) -> dict:
    return dict(row) if row is not None else {}


def _norm_account_type(value: Any) -> str:
    raw = str(value or "").strip().lower()
    raw = (
        raw.replace("ã", "a")
        .replace("á", "a")
        .replace("à", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )
    if raw == "cartao":
        return "Cartao"
    if raw == "corretora":
        return "Corretora"
    if raw == "banco":
        return "Banco"
    if raw == "dinheiro":
        return "Dinheiro"
    return str(value or "").strip()


def _norm_currency(value: Any) -> str:
    raw = str(value or "").strip().upper()
    return raw if raw in {"BRL", "USD"} else ""


def _norm_trade_side(value: Any) -> str:
    raw = str(value or "").strip().upper()
    raw = (
        raw.replace("Ã", "A")
        .replace("Á", "A")
        .replace("À", "A")
        .replace("Â", "A")
        .replace("É", "E")
        .replace("Ê", "E")
        .replace("Í", "I")
        .replace("Ó", "O")
        .replace("Ô", "O")
        .replace("Õ", "O")
        .replace("Ú", "U")
        .replace("Ç", "C")
    )
    mapping = {
        "BUY": "BUY",
        "SELL": "SELL",
        "COMPRA": "BUY",
        "VENDA": "SELL",
        "APLICACAO": "BUY",
        "RESGATE": "SELL",
        "C": "BUY",
        "V": "SELL",
    }
    return mapping.get(raw, "")


def _norm_asset_class(value: Any) -> str:
    raw = str(value or "").strip().lower()
    raw = (
        raw.replace("ã", "a")
        .replace("á", "a")
        .replace("à", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )
    return "_".join(raw.split())


def _is_us_stock_asset(asset: dict) -> bool:
    cls_raw = None
    if isinstance(asset, dict):
        cls_raw = asset.get("asset_class")
    else:
        try:
            cls_raw = asset["asset_class"]
        except Exception:
            cls_raw = None
    cls = _norm_asset_class(cls_raw)
    return cls in {"stock_us", "stocks_us"}


def _is_fixed_income_asset(asset: dict) -> bool:
    cls_raw = None
    if isinstance(asset, dict):
        cls_raw = asset.get("asset_class")
    else:
        try:
            cls_raw = asset["asset_class"]
        except Exception:
            cls_raw = None
    cls = _norm_asset_class(cls_raw)
    return cls in {"renda_fixa", "tesouro_direto", "coe", "fundos"}


def _norm_rentability_type(value: Any) -> str | None:
    raw = str(value or "").strip().upper()
    raw = (
        raw.replace("Ã", "A")
        .replace("Á", "A")
        .replace("À", "A")
        .replace("Â", "A")
        .replace("É", "E")
        .replace("Ê", "E")
        .replace("Í", "I")
        .replace("Ó", "O")
        .replace("Ô", "O")
        .replace("Õ", "O")
        .replace("Ú", "U")
        .replace("Ç", "C")
        .replace(" ", "_")
    )
    mapping = {
        "PREFIXADO": "PREFIXADO",
        "PCT_CDI": "PCT_CDI",
        "PCT_DI": "PCT_CDI",
        "PCT_SELIC": "PCT_SELIC",
        "IPCA_SPREAD": "IPCA_SPREAD",
        "IPCA_X": "IPCA_SPREAD",
        "MANUAL": "MANUAL",
    }
    if not raw:
        return None
    return mapping.get(raw, raw)


def _norm_index_name(value: Any) -> str | None:
    raw = str(value or "").strip().upper()
    if not raw:
        return None
    if raw in {"DI", "CDI"}:
        return "CDI"
    if raw.startswith("SELIC"):
        return "SELIC"
    if raw == "IPCA":
        return "IPCA"
    return raw


def _validate_asset_rentability(
    *,
    asset_class: str,
    rentability_type: Any,
    index_name: Any,
    index_pct: Any,
    spread_rate: Any,
    fixed_rate: Any,
) -> dict[str, Any]:
    is_fixed_income = _norm_asset_class(asset_class) in {"renda_fixa", "tesouro_direto", "coe", "fundos"}
    rt = _norm_rentability_type(rentability_type)
    idx = _norm_index_name(index_name)
    ip = index_pct
    sr = spread_rate
    fr = fixed_rate

    if not is_fixed_income:
        if any(v is not None for v in [idx, ip, sr, fr]) or (rt not in {None, "MANUAL"}):
            raise HTTPException(
                status_code=400,
                detail="Rentabilidade automática é permitida apenas para Renda Fixa/Tesouro/Fundos/COE.",
            )
        return {
            "rentability_type": None,
            "index_name": None,
            "index_pct": None,
            "spread_rate": None,
            "fixed_rate": None,
        }

    if rt is None:
        if is_fixed_income:
            rt = "MANUAL"
        else:
            raise HTTPException(status_code=400, detail="Informe rentability_type quando enviar parâmetros de taxa.")

    valid_types = {"PREFIXADO", "PCT_CDI", "PCT_SELIC", "IPCA_SPREAD", "MANUAL"}
    if rt not in valid_types:
        raise HTTPException(status_code=400, detail=f"rentability_type inválido: {rt}")

    if rt == "MANUAL":
        if any(v is not None for v in [idx, ip, sr, fr]):
            raise HTTPException(status_code=400, detail="MANUAL não permite index_name/index_pct/spread_rate/fixed_rate.")
        return {
            "rentability_type": "MANUAL",
            "index_name": None,
            "index_pct": None,
            "spread_rate": None,
            "fixed_rate": None,
        }

    if rt == "PREFIXADO":
        if fr is None:
            raise HTTPException(status_code=400, detail="PREFIXADO exige fixed_rate.")
        if any(v is not None for v in [idx, ip]):
            raise HTTPException(status_code=400, detail="PREFIXADO não permite index_name/index_pct.")
        return {
            "rentability_type": "PREFIXADO",
            "index_name": None,
            "index_pct": None,
            "spread_rate": sr,
            "fixed_rate": fr,
        }

    if rt == "PCT_CDI":
        if idx != "CDI":
            raise HTTPException(status_code=400, detail="PCT_CDI exige index_name=CDI.")
        if ip is None:
            raise HTTPException(status_code=400, detail="PCT_CDI exige index_pct.")
        if fr is not None:
            raise HTTPException(status_code=400, detail="PCT_CDI não permite fixed_rate.")
        return {
            "rentability_type": "PCT_CDI",
            "index_name": "CDI",
            "index_pct": ip,
            "spread_rate": sr,
            "fixed_rate": None,
        }

    if rt == "PCT_SELIC":
        if idx != "SELIC":
            raise HTTPException(status_code=400, detail="PCT_SELIC exige index_name=SELIC.")
        if ip is None:
            raise HTTPException(status_code=400, detail="PCT_SELIC exige index_pct.")
        if fr is not None:
            raise HTTPException(status_code=400, detail="PCT_SELIC não permite fixed_rate.")
        return {
            "rentability_type": "PCT_SELIC",
            "index_name": "SELIC",
            "index_pct": ip,
            "spread_rate": sr,
            "fixed_rate": None,
        }

    # IPCA_SPREAD
    if idx != "IPCA":
        raise HTTPException(status_code=400, detail="IPCA_SPREAD exige index_name=IPCA.")
    if sr is None:
        raise HTTPException(status_code=400, detail="IPCA_SPREAD exige spread_rate.")
    if any(v is not None for v in [ip, fr]):
        raise HTTPException(status_code=400, detail="IPCA_SPREAD não permite index_pct/fixed_rate.")
    return {
        "rentability_type": "IPCA_SPREAD",
        "index_name": "IPCA",
        "index_pct": None,
        "spread_rate": sr,
        "fixed_rate": None,
    }


def _quote_group_for_asset(asset: dict) -> str:
    cls = _norm_asset_class((asset or {}).get("asset_class"))
    if cls in {"fii", "fiis", "stock_fii"}:
        return "FIIs"
    if cls in {"acao_br", "acoes_br", "etf_br", "bdr"}:
        return "Ações BR"
    if cls in {"stock_us", "stocks_us", "etf_us"}:
        return "Stocks"
    if cls in {"crypto", "cripto"}:
        return "Cripto"
    return "Outros"


def _norm_card_brand(value: Any) -> str:
    raw = str(value or "").strip().lower()
    raw = (
        raw.replace("ã", "a")
        .replace("á", "a")
        .replace("à", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )
    if raw in {"master", "mastercard"}:
        return "Master"
    return "Visa"


def _norm_card_type(value: Any) -> str:
    raw = str(value or "").strip().lower()
    raw = (
        raw.replace("ã", "a")
        .replace("á", "a")
        .replace("à", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )
    if raw in {"debito"}:
        return "Debito"
    return "Credito"


def _norm_view(value: str | None) -> str:
    mode = (value or "caixa").strip().lower()
    if mode not in VALID_VIEWS:
        raise HTTPException(status_code=400, detail="View inválida. Use 'caixa', 'competencia' ou 'futuro'.")
    return mode


def _add_months(year: int, month: int, plus: int) -> tuple[int, int]:
    total = (int(year) * 12) + (int(month) - 1) + int(plus)
    return total // 12, (total % 12) + 1


def _due_date_for_month(year: int, month: int, due_day: int) -> str:
    last = calendar.monthrange(int(year), int(month))[1]
    day = max(1, min(int(due_day), int(last)))
    return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"


def _norm_card_model(value: Any) -> str:
    allowed = {"Black", "Gold", "Platinum", "Orange", "Violeta", "Vermelho"}
    raw = str(value or "").strip().lower()
    raw = (
        raw.replace("ã", "a")
        .replace("á", "a")
        .replace("à", "a")
        .replace("â", "a")
        .replace("é", "e")
        .replace("ê", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ô", "o")
        .replace("õ", "o")
        .replace("ú", "u")
        .replace("ç", "c")
    )
    mapping = {
        "black": "Black",
        "gold": "Gold",
        "platinum": "Platinum",
        "orange": "Orange",
        "violeta": "Violeta",
        "vermelho": "Vermelho",
    }
    model = mapping.get(raw, "Black")
    return model if model in allowed else "Black"


def _request_ip(request: Request | None) -> str | None:
    try:
        return request.client.host if request and request.client else None
    except Exception:
        return None


def _auth_payload(
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        security_monitor.record_event(
            event_type="auth_missing_bearer",
            status_code=401,
            path=str(request.url.path),
            detail="Missing bearer token",
            ip=_request_ip(request),
        )
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    payload = verify_token(token)
    if not payload:
        security_monitor.record_event(
            event_type="auth_invalid_token",
            status_code=401,
            path=str(request.url.path),
            detail="Invalid token",
            ip=_request_ip(request),
        )
        raise HTTPException(status_code=401, detail="Invalid token")
    return dict(payload)


def _global_role_from_user(user: dict | None) -> str:
    if not user:
        return "USER"
    raw = str(user.get("global_role", "") or "").strip().upper()
    if raw in {"SUPER_ADMIN", "USER"}:
        return raw
    legacy = str(user.get("role", "") or "").strip().lower()
    return "SUPER_ADMIN" if legacy == "admin" else "USER"


def _is_super_admin(user: dict | None) -> bool:
    return _global_role_from_user(user) == "SUPER_ADMIN"


def _permission_from_request(method: str, path: str) -> tuple[str, str] | None:
    p = str(path or "").strip().lower().strip("/")
    if not p:
        return None

    if p in {"workspaces", "workspaces/switch"}:
        return None

    if p.startswith("dashboard"):
        module = "dashboard"
    elif p.startswith("transactions") or p.startswith("credit-commitments"):
        module = "lancamentos"
    elif p.startswith("invest"):
        module = "investimentos"
    elif p.startswith("accounts") or p.startswith("categories") or p.startswith("cards") or p.startswith("card-invoices"):
        module = "contas"
    elif p.startswith("workspaces/members"):
        module = "usuarios"
    else:
        return None

    m = str(method or "GET").strip().upper()
    if m == "GET":
        action = "view"
    elif m == "POST":
        action = "add"
    elif m in {"PUT", "PATCH"}:
        action = "edit"
    elif m == "DELETE":
        action = "delete"
    else:
        action = "view"

    return module, action


def _current_user(
    request: Request,
    payload: dict = Depends(_auth_payload),
    x_workspace_id: int | None = Header(default=None, alias="X-Workspace-Id"),
) -> dict:
    uid = int(payload["uid"])
    user = auth.get_user_by_id(uid)
    if not user or not user.get("is_active", True):
        security_monitor.record_event(
            event_type="auth_invalid_user",
            status_code=401,
            path=str(request.url.path),
            detail="Invalid user",
            user_id=uid,
            ip=_request_ip(request),
        )
        raise HTTPException(status_code=401, detail="Invalid user")

    global_role = _global_role_from_user(user)
    requested_workspace_id = x_workspace_id
    if requested_workspace_id is None:
        wid_claim = payload.get("wid", payload.get("workspace_id"))
        if wid_claim is not None:
            try:
                requested_workspace_id = int(wid_claim)
            except Exception:
                security_monitor.record_event(
                    event_type="auth_invalid_workspace_claim",
                    status_code=401,
                    path=str(request.url.path),
                    detail="Invalid workspace claim in token",
                    user_id=uid,
                    ip=_request_ip(request),
                )
                raise HTTPException(status_code=401, detail="Invalid workspace claim in token")

    member: dict | None = None
    workspace_id: int | None = int(requested_workspace_id) if requested_workspace_id else None

    if workspace_id is not None and workspace_id <= 0:
        raise HTTPException(status_code=400, detail="X-Workspace-Id inválido")

    if workspace_id is None:
        member = auth.ensure_default_workspace_for_user(uid)
        if member:
            workspace_id = int(member["workspace_id"])

    if global_role == "SUPER_ADMIN":
        if workspace_id is not None:
            ws = auth.get_workspace_by_id(workspace_id)
            if not ws:
                raise HTTPException(status_code=404, detail="Workspace não encontrado")
            if not member:
                member = {
                    "workspace_id": int(ws["workspace_id"]),
                    "workspace_name": ws.get("workspace_name"),
                    "workspace_status": str(ws.get("status") or "active").lower(),
                    "workspace_role": "SUPER_ADMIN",
                    "owner_user_id": ws.get("owner_user_id"),
                }
    else:
        if workspace_id is None:
            security_monitor.record_event(
                event_type="workspace_missing",
                status_code=403,
                path=str(request.url.path),
                detail="Usuário sem workspace associado",
                user_id=uid,
                ip=_request_ip(request),
            )
            raise HTTPException(status_code=403, detail="Usuário sem workspace associado")
        member = auth.get_user_workspace_membership(uid, workspace_id)
        if not member:
            security_monitor.record_event(
                event_type="cross_workspace_denied",
                status_code=403,
                path=str(request.url.path),
                detail="Usuário não pertence ao workspace informado",
                user_id=uid,
                workspace_id=workspace_id,
                ip=_request_ip(request),
            )
            raise HTTPException(status_code=403, detail="Usuário não pertence ao workspace informado")
        if str(member.get("workspace_status") or "").strip().lower() != "active":
            security_monitor.record_event(
                event_type="workspace_blocked",
                status_code=403,
                path=str(request.url.path),
                detail="Workspace bloqueado",
                user_id=uid,
                workspace_id=workspace_id,
                ip=_request_ip(request),
            )
            raise HTTPException(status_code=403, detail="Workspace bloqueado")

    set_current_user_id(uid)
    set_current_global_role(global_role)
    if workspace_id is not None:
        set_current_workspace_id(workspace_id)
    if member:
        set_current_workspace_role(str(member.get("workspace_role") or "").strip().upper())

    out = dict(user)
    out["global_role"] = global_role
    out["role"] = "admin" if global_role == "SUPER_ADMIN" else "user"
    out["workspace_id"] = int(workspace_id) if workspace_id is not None else None
    out["workspace_role"] = str(member.get("workspace_role") or "").strip().upper() if member else None
    out["workspace_status"] = str(member.get("workspace_status") or "").strip().lower() if member else None
    out["workspace_name"] = member.get("workspace_name") if member else None

    perm = _permission_from_request(request.method, request.url.path)
    if perm:
        module, action = perm
        if not permissions_service.can_access(out, module=module, action=action):
            security_monitor.record_event(
                event_type="permission_denied",
                status_code=403,
                path=str(request.url.path),
                detail=f"Sem permissão para {action} em {module}",
                user_id=uid,
                workspace_id=int(workspace_id) if workspace_id is not None else None,
                ip=_request_ip(request),
            )
            raise HTTPException(status_code=403, detail=f"Sem permissão para {action} em {module}")

    return out


def _require_admin(user: dict) -> None:
    if not _is_super_admin(user):
        raise HTTPException(status_code=403, detail="Somente admin pode executar esta operação")


def _current_workspace_id_from_user(user: dict) -> int:
    workspace_id = user.get("workspace_id")
    if workspace_id is None:
        raise HTTPException(status_code=400, detail="Workspace não definido no contexto atual.")
    wid = int(workspace_id)
    if wid <= 0:
        raise HTTPException(status_code=400, detail="Workspace inválido.")
    return wid


def _require_workspace_owner(user: dict) -> None:
    if _is_super_admin(user):
        return
    role = str(user.get("workspace_role") or "").strip().upper()
    if role != "OWNER":
        raise HTTPException(status_code=403, detail="Somente OWNER pode gerenciar usuários do workspace.")


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.post("/import/transactions-csv")
async def import_transactions_csv_endpoint(
    file: UploadFile = File(...),
    preview_only: bool = Form(default=False),
    user: dict = Depends(_current_user),
) -> dict:
    uid = int(user["id"])
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Arquivo vazio")
    try:
        return importers.import_transactions_csv(raw, user_id=uid, preview_only=bool(preview_only))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/import/assets-csv")
async def import_assets_csv_endpoint(
    file: UploadFile = File(...),
    preview_only: bool = Form(default=False),
    user: dict = Depends(_current_user),
) -> dict:
    uid = int(user["id"])
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Arquivo vazio")
    try:
        return importers.import_assets_csv(raw, user_id=uid, preview_only=bool(preview_only))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/import/trades-csv")
async def import_trades_csv_endpoint(
    file: UploadFile = File(...),
    preview_only: bool = Form(default=False),
    user: dict = Depends(_current_user),
) -> dict:
    uid = int(user["id"])
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Arquivo vazio")
    try:
        return importers.import_trades_csv(raw, user_id=uid, preview_only=bool(preview_only))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/auth/login", response_model=LoginResponse)
def login(body: LoginRequest, request: Request) -> LoginResponse:
    user = auth.authenticate_user(body.email, body.password)
    if not user:
        security_monitor.record_event(
            event_type="login_invalid_credentials",
            status_code=401,
            path=str(request.url.path),
            detail="Credenciais inválidas",
            ip=_request_ip(request),
        )
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    uid = int(user["id"])
    global_role = _global_role_from_user(user)
    member = auth.ensure_default_workspace_for_user(uid)
    workspace_id = int(member["workspace_id"]) if member else None

    if global_role != "SUPER_ADMIN" and workspace_id is None:
        security_monitor.record_event(
            event_type="login_without_workspace",
            status_code=403,
            path=str(request.url.path),
            detail="Usuário sem workspace associado",
            user_id=uid,
            ip=_request_ip(request),
        )
        raise HTTPException(status_code=403, detail="Usuário sem workspace associado")

    workspace_role = None
    if member:
        workspace_role = str(member.get("workspace_role") or "").strip().upper() or None
        if global_role != "SUPER_ADMIN":
            workspace_status = str(member.get("workspace_status") or "").strip().lower() or "active"
            if workspace_status != "active":
                security_monitor.record_event(
                    event_type="login_blocked_workspace",
                    status_code=403,
                    path=str(request.url.path),
                    detail="Workspace bloqueado",
                    user_id=uid,
                    workspace_id=workspace_id,
                    ip=_request_ip(request),
                )
                raise HTTPException(status_code=403, detail="Workspace bloqueado")

    token = create_token(
        uid,
        str(user["email"]),
        workspace_id=workspace_id,
        global_role=global_role,
        workspace_role=workspace_role,
    )

    out_user = dict(user)
    out_user["global_role"] = global_role
    out_user["role"] = "admin" if global_role == "SUPER_ADMIN" else "user"
    out_user["workspace_id"] = workspace_id
    out_user["workspace_role"] = workspace_role
    out_user["workspace_status"] = str(member.get("workspace_status") or "").strip().lower() if member else None
    out_user["workspace_name"] = member.get("workspace_name") if member else None
    return LoginResponse(token=token, user=out_user)


@app.get("/me")
def me(user: dict = Depends(_current_user)) -> dict:
    return user


@app.get("/workspaces")
def list_workspaces(user: dict = Depends(_current_user)) -> list[dict]:
    if _is_super_admin(user):
        rows = auth.list_all_workspaces()
        out: list[dict] = []
        for r in rows:
            item = dict(r)
            item["workspace_role"] = "SUPER_ADMIN"
            out.append(item)
        return out
    uid = int(user["id"])
    rows = auth.list_user_workspaces(uid)
    return [dict(r) for r in rows]


@app.post("/workspaces/switch", response_model=LoginResponse)
def switch_workspace(body: WorkspaceSwitchRequest, user: dict = Depends(_current_user)) -> LoginResponse:
    uid = int(user["id"])
    target_workspace_id = int(body.workspace_id)
    global_role = _global_role_from_user(user)

    if global_role == "SUPER_ADMIN":
        ws = auth.get_workspace_by_id(target_workspace_id)
        if not ws:
            raise HTTPException(status_code=404, detail="Workspace não encontrado")
        workspace_role = "SUPER_ADMIN"
        workspace_status = str(ws.get("status") or "active").strip().lower()
        workspace_name = ws.get("workspace_name")
    else:
        member = auth.get_user_workspace_membership(uid, target_workspace_id)
        if not member:
            raise HTTPException(status_code=403, detail="Usuário não pertence ao workspace informado")
        if str(member.get("workspace_status") or "").strip().lower() != "active":
            raise HTTPException(status_code=403, detail="Workspace bloqueado")
        workspace_role = str(member.get("workspace_role") or "").strip().upper() or "GUEST"
        workspace_status = str(member.get("workspace_status") or "").strip().lower() or "active"
        workspace_name = member.get("workspace_name")

    token = create_token(
        uid,
        str(user["email"]),
        workspace_id=target_workspace_id,
        global_role=global_role,
        workspace_role=workspace_role,
    )
    out_user = dict(user)
    out_user["global_role"] = global_role
    out_user["role"] = "admin" if global_role == "SUPER_ADMIN" else "user"
    out_user["workspace_id"] = target_workspace_id
    out_user["workspace_role"] = workspace_role
    out_user["workspace_status"] = workspace_status
    out_user["workspace_name"] = workspace_name
    return LoginResponse(token=token, user=out_user)


@app.get("/workspaces/members")
def list_workspace_members(user: dict = Depends(_current_user)) -> list[dict]:
    _require_workspace_owner(user)
    workspace_id = _current_workspace_id_from_user(user)
    members = auth.list_workspace_members(workspace_id)
    out: list[dict] = []
    for m in members:
        item = dict(m)
        role = str(item.get("workspace_role") or "").strip().upper()
        if role == "GUEST":
            item["permissions"] = permissions_service.list_permissions_by_workspace_user(int(item["workspace_user_id"]))
        else:
            item["permissions"] = []
        out.append(item)
    return out


@app.post("/workspaces/members")
def create_workspace_member(
    body: WorkspaceMemberCreateRequest,
    user: dict = Depends(_current_user),
) -> dict:
    _require_workspace_owner(user)
    workspace_id = _current_workspace_id_from_user(user)
    email = (body.email or "").strip().lower()
    role = str(body.role or "GUEST").strip().upper() or "GUEST"
    if role != "GUEST":
        raise HTTPException(status_code=400, detail="Neste fluxo, apenas role GUEST é permitido.")
    if not email:
        raise HTTPException(status_code=400, detail="E-mail é obrigatório.")

    target = auth.get_user_by_email(email)
    if not target:
        raw_password = str(body.password or "")
        display_name = (body.display_name or "").strip() or None
        if len(raw_password) < 6:
            raise HTTPException(
                status_code=400,
                detail="Usuário não encontrado. Informe senha inicial (mín. 6) para criar o convidado.",
            )
        try:
            target = auth.create_user(
                email=email,
                password=raw_password,
                display_name=display_name,
                global_role="USER",
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    if not bool(target.get("is_active", True)):
        raise HTTPException(status_code=400, detail="Usuário inativo não pode ser adicionado.")

    target_user_id = int(target["id"])
    if target_user_id == int(user["id"]):
        raise HTTPException(status_code=400, detail="Usuário já pertence ao workspace atual como OWNER.")

    existing = auth.get_user_workspace_membership(target_user_id, workspace_id)
    if existing:
        existing_role = str(existing.get("workspace_role") or "").strip().upper()
        if existing_role == "OWNER":
            raise HTTPException(status_code=400, detail="Usuário já é OWNER deste workspace.")
        ws_user_id = int(existing.get("workspace_user_id") or 0)
        if ws_user_id > 0:
            permissions_service.seed_default_guest_permissions(ws_user_id)
            perms = permissions_service.list_permissions_by_workspace_user(ws_user_id)
        else:
            perms = []
        return {
            "ok": True,
            "created": False,
            "member": {
                **dict(existing),
                "email": target.get("email"),
                "display_name": target.get("display_name"),
                "is_active": target.get("is_active"),
                "permissions": perms,
            },
        }

    created = auth.upsert_workspace_member(
        workspace_id=workspace_id,
        user_id=target_user_id,
        role="GUEST",
        created_by=int(user["id"]),
    )
    if not created:
        raise HTTPException(status_code=500, detail="Falha ao incluir membro no workspace.")

    ws_user_id = int(created.get("workspace_user_id") or 0)
    if ws_user_id <= 0:
        raise HTTPException(status_code=500, detail="Falha ao resolver vínculo do membro no workspace.")

    permissions_service.seed_default_guest_permissions(ws_user_id)
    perms = permissions_service.list_permissions_by_workspace_user(ws_user_id)
    member = auth.get_user_workspace_membership(target_user_id, workspace_id) or {}

    return {
        "ok": True,
        "created": True,
        "member": {
            **dict(member),
            "email": target.get("email"),
            "display_name": target.get("display_name"),
            "is_active": target.get("is_active"),
            "permissions": perms,
        },
    }


@app.put("/workspaces/members/{member_user_id}/permissions")
def update_workspace_member_permissions(
    member_user_id: int,
    body: WorkspacePermissionsUpdateRequest,
    user: dict = Depends(_current_user),
) -> dict:
    _require_workspace_owner(user)
    workspace_id = _current_workspace_id_from_user(user)

    member = auth.get_user_workspace_membership(int(member_user_id), workspace_id)
    if not member:
        raise HTTPException(status_code=404, detail="Membro não encontrado no workspace atual.")

    role = str(member.get("workspace_role") or "").strip().upper()
    if role != "GUEST":
        raise HTTPException(status_code=400, detail="Permissões granulares só podem ser editadas para GUEST.")

    ws_user_id = int(member.get("workspace_user_id") or 0)
    if ws_user_id <= 0:
        raise HTTPException(status_code=500, detail="Vínculo do membro inválido.")

    payload = [
        {
            "module": str(item.module),
            "can_view": bool(item.can_view),
            "can_add": bool(item.can_add),
            "can_edit": bool(item.can_edit),
            "can_delete": bool(item.can_delete),
        }
        for item in (body.permissions or [])
    ]
    try:
        updated = permissions_service.replace_permissions(ws_user_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "workspace_user_id": ws_user_id, "permissions": updated}


@app.delete("/workspaces/members/{member_user_id}")
def delete_workspace_member(
    member_user_id: int,
    user: dict = Depends(_current_user),
) -> dict:
    _require_workspace_owner(user)
    workspace_id = _current_workspace_id_from_user(user)
    target_user_id = int(member_user_id)
    if target_user_id == int(user["id"]):
        raise HTTPException(status_code=400, detail="Não é permitido remover o próprio usuário deste workspace.")

    member = auth.get_user_workspace_membership(target_user_id, workspace_id)
    if not member:
        raise HTTPException(status_code=404, detail="Membro não encontrado no workspace atual.")

    role = str(member.get("workspace_role") or "").strip().upper()
    if role == "OWNER":
        raise HTTPException(status_code=400, detail="Não é permitido remover OWNER por este endpoint.")

    ws_user_id = int(member.get("workspace_user_id") or 0)
    if ws_user_id > 0:
        permissions_service.delete_permissions_for_workspace_user(ws_user_id)
    deleted = auth.delete_workspace_member(workspace_id, target_user_id)
    if deleted <= 0:
        raise HTTPException(status_code=404, detail="Membro não encontrado no workspace atual.")
    return {"ok": True}


@app.get("/admin/workspaces")
def admin_list_workspaces(user: dict = Depends(_current_user)) -> list[dict]:
    _require_admin(user)
    rows = auth.list_all_workspaces()
    return [dict(r) for r in rows]


@app.post("/admin/workspaces")
def admin_create_workspace(
    body: WorkspaceAdminCreateRequest,
    user: dict = Depends(_current_user),
) -> dict:
    _require_admin(user)
    owner_email = str(body.owner_email or "").strip().lower()
    workspace_name = str(body.workspace_name or "").strip()
    owner_password = str(body.owner_password or "")
    owner_display_name = (body.owner_display_name or "").strip() or None
    if not owner_email:
        raise HTTPException(status_code=400, detail="E-mail do owner é obrigatório.")
    if not workspace_name:
        raise HTTPException(status_code=400, detail="Nome do workspace é obrigatório.")

    owner = auth.get_user_by_email(owner_email)
    if not owner:
        if len(owner_password) < 6:
            raise HTTPException(
                status_code=400,
                detail="Owner não encontrado. Informe senha inicial (mín. 6) para criar o usuário owner.",
            )
        try:
            owner = auth.create_user(
                email=owner_email,
                password=owner_password,
                display_name=owner_display_name,
                global_role="USER",
            )
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    if not bool(owner.get("is_active", True)):
        raise HTTPException(status_code=400, detail="Usuário owner está inativo.")
    try:
        created = auth.create_workspace_with_owner(
            owner_user_id=int(owner["id"]),
            workspace_name=workspace_name,
            created_by=int(user["id"]),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not created:
        raise HTTPException(status_code=500, detail="Falha ao criar workspace.")

    ws = dict(created)
    ws["workspace_status"] = str(ws.get("status") or "active").strip().lower()
    ws["owner_email"] = owner.get("email")
    ws["owner_display_name"] = owner.get("display_name")
    return {"ok": True, "workspace": ws}


@app.put("/admin/workspaces/{workspace_id}/status")
def admin_update_workspace_status(
    workspace_id: int,
    body: WorkspaceStatusUpdateRequest,
    user: dict = Depends(_current_user),
) -> dict:
    _require_admin(user)
    try:
        updated = auth.update_workspace_status(int(workspace_id), body.status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not updated:
        raise HTTPException(status_code=404, detail="Workspace não encontrado.")
    out = dict(updated)
    out["workspace_status"] = str(out.get("status") or "active").strip().lower()
    return {"ok": True, "workspace": out}


@app.put("/admin/users/{user_id}/global-role")
def admin_update_global_role(
    user_id: int,
    body: UserGlobalRoleUpdateRequest,
    user: dict = Depends(_current_user),
) -> dict:
    _require_admin(user)
    try:
        updated = auth.set_user_global_role(int(user_id), body.global_role)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not updated:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    return {"ok": True, "user": dict(updated)}


@app.get("/admin/security/summary")
def admin_security_summary(
    limit: int = Query(default=50, ge=1, le=300),
    user: dict = Depends(_current_user),
) -> dict:
    _require_admin(user)
    return security_monitor.snapshot(limit=limit)


@app.get("/accounts")
def list_accounts(user: dict = Depends(_current_user)) -> list[dict]:
    uid = int(user["id"])
    rows = repo.list_accounts(user_id=uid) or []
    return [_row_to_dict(r) for r in rows]


@app.post("/accounts")
def create_account(
    body: AccountCreateRequest,
    user: dict = Depends(_current_user),
) -> dict:
    uid = int(user["id"])
    name = (body.name or "").strip()
    acc_type = _norm_account_type(body.type)
    currency = _norm_currency(body.currency)
    if not name:
        raise HTTPException(status_code=400, detail="Nome da conta é obrigatório")
    if acc_type not in {"Banco", "Cartao", "Dinheiro", "Corretora"}:
        raise HTTPException(status_code=400, detail="Tipo de conta inválido")
    if currency not in {"BRL", "USD"}:
        raise HTTPException(status_code=400, detail="Moeda da conta inválida")
    repo.create_account(
        name,
        acc_type,
        currency=currency,
        show_on_dashboard=bool(body.show_on_dashboard),
        user_id=uid,
    )
    return {"ok": True}


@app.put("/accounts/{account_id}")
def update_account(
    account_id: int,
    body: AccountUpdateRequest,
    user: dict = Depends(_current_user),
) -> dict:
    uid = int(user["id"])
    name = (body.name or "").strip()
    acc_type = _norm_account_type(body.type)
    currency = _norm_currency(body.currency)
    if not name:
        raise HTTPException(status_code=400, detail="Nome da conta é obrigatório")
    if acc_type not in {"Banco", "Cartao", "Dinheiro", "Corretora"}:
        raise HTTPException(status_code=400, detail="Tipo de conta inválido")
    if currency not in {"BRL", "USD"}:
        raise HTTPException(status_code=400, detail="Moeda da conta inválida")
    repo.update_account(
        account_id=account_id,
        name=name,
        acc_type=acc_type,
        currency=currency,
        show_on_dashboard=bool(body.show_on_dashboard),
        user_id=uid,
    )
    return {"ok": True}


@app.delete("/accounts/{account_id}")
def delete_account(
    account_id: int,
    user: dict = Depends(_current_user),
) -> dict:
    uid = int(user["id"])
    used = repo.account_usage_count(account_id, user_id=uid)
    if used > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Não pode excluir: {used} lançamento(s) usam esta conta",
        )
    deleted = repo.delete_account(account_id, user_id=uid)
    if not deleted:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    return {"ok": True}


@app.get("/categories")
def list_categories(
    kind: str | None = Query(default=None),
    user: dict = Depends(_current_user),
) -> list[dict]:
    uid = int(user["id"])
    rows = repo.list_categories(kind=kind, user_id=uid) or []
    return [_row_to_dict(r) for r in rows]


@app.post("/categories")
def create_category(
    body: CategoryCreateRequest,
    user: dict = Depends(_current_user),
) -> dict:
    uid = int(user["id"])
    name = (body.name or "").strip()
    kind = (body.kind or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Nome da categoria é obrigatório")
    if kind not in {"Despesa", "Receita", "Transferencia"}:
        raise HTTPException(status_code=400, detail="Tipo de categoria inválido")
    repo.create_category(name, kind, user_id=uid)
    return {"ok": True}


@app.put("/categories/{category_id}")
def update_category(
    category_id: int,
    body: CategoryUpdateRequest,
    user: dict = Depends(_current_user),
) -> dict:
    uid = int(user["id"])
    name = (body.name or "").strip()
    kind = (body.kind or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Nome da categoria é obrigatório")
    if kind not in {"Despesa", "Receita", "Transferencia"}:
        raise HTTPException(status_code=400, detail="Tipo de categoria inválido")
    repo.update_category(category_id=category_id, name=name, kind=kind, user_id=uid)
    return {"ok": True}


@app.delete("/categories/{category_id}")
def delete_category(
    category_id: int,
    user: dict = Depends(_current_user),
) -> dict:
    uid = int(user["id"])
    used = repo.category_usage_count(category_id, user_id=uid)
    if used > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Não pode excluir: {used} lançamento(s) usam esta categoria",
        )
    deleted = repo.delete_category(category_id, user_id=uid)
    if not deleted:
        raise HTTPException(status_code=404, detail="Categoria não encontrada")
    return {"ok": True}


@app.get("/transactions")
def list_transactions(
    date_from: str | None = None,
    date_to: str | None = None,
    view: str = Query(default="caixa"),
    limit: int = Query(default=100, ge=1, le=1000),
    user: dict = Depends(_current_user),
) -> list[dict]:
    uid = int(user["id"])
    mode = _norm_view(view)
    df = reports.df_transactions(date_from=date_from, date_to=date_to, user_id=uid, view=mode)
    if df.empty:
        return []
    rows_view = df.sort_values("date", ascending=False).head(int(limit)).copy()
    rows_view["date"] = rows_view["date"].dt.strftime("%Y-%m-%d")
    return rows_view.fillna("").to_dict(orient="records")


@app.post("/transactions")
def create_transaction(
    body: TransactionCreateRequest,
    user: dict = Depends(_current_user),
) -> dict:
    uid = int(user["id"])
    desc = (body.description or "").strip()
    amount_abs = abs(float(body.amount or 0.0))
    if amount_abs <= 0:
        raise HTTPException(status_code=400, detail="Valor deve ser maior que zero")

    accounts = [dict(r) for r in (repo.list_accounts(user_id=uid) or [])]
    account_map = {int(a["id"]): a for a in accounts}
    destination_id = int(body.account_id)
    if destination_id not in account_map:
        raise HTTPException(status_code=400, detail="Conta inválida")

    categories = [dict(r) for r in (repo.list_categories(user_id=uid) or [])]
    category_kind = None
    category_name = None
    category_id = None
    if body.category_id is not None:
        category_id = int(body.category_id)
        cat_map = {int(c["id"]): c for c in categories}
        if category_id not in cat_map:
            raise HTTPException(status_code=400, detail="Categoria inválida")
        category_kind = str(cat_map[category_id]["kind"])
        category_name = str(cat_map[category_id]["name"] or "").strip() or None

    if not desc:
        desc = category_name or "Lançamento"

    req_kind = (body.kind or "").strip()
    if req_kind and req_kind not in {"Receita", "Despesa", "Transferencia"}:
        raise HTTPException(status_code=400, detail="Tipo inválido")
    if req_kind and category_kind and req_kind != category_kind:
        raise HTTPException(status_code=400, detail="Tipo incompatível com a categoria")

    kind = req_kind or category_kind
    if not kind:
        kind = "Despesa" if float(body.amount) < 0 else "Receita"

    raw_method = (body.method or "").strip()
    mlow = raw_method.lower()
    if mlow in {"debito", "débito"}:
        method = "Debito"
    elif mlow in {"credito", "crédito"}:
        method = "Credito"
    elif mlow in {"pix"}:
        method = "PIX"
    elif mlow in {"futuro", "agendado"}:
        method = "Futuro"
    else:
        method = raw_method or None
    notes = (body.notes or "").strip() or None

    if method == "Futuro" and kind != "Despesa":
        raise HTTPException(status_code=400, detail="Método Futuro só é permitido para Despesa.")
    if method == "Futuro":
        future_pay_raw = (body.future_payment_method or "").strip()
        future_pay_l = future_pay_raw.lower()
        if future_pay_l in {"credito", "crédito", "cartao", "cartão", "cartao de credito", "cartão de crédito"}:
            future_pay = "Credito"
        elif future_pay_l in {"debito", "débito"}:
            future_pay = "Debito"
        elif future_pay_l in {"boleto"}:
            future_pay = "Boleto"
        else:
            future_pay = "PIX"
        repeat_months = int(body.repeat_months or 1)
        if repeat_months < 1 or repeat_months > 120:
            raise HTTPException(status_code=400, detail="Meses para replicar deve estar entre 1 e 120.")

        if future_pay == "Credito":
            if body.card_id is None:
                raise HTTPException(status_code=400, detail="Selecione um cartão de crédito para compromisso no cartão.")
            card_cfg = repo.get_credit_card_by_id_and_type(int(body.card_id), "Credito", user_id=uid)
            if not card_cfg:
                raise HTTPException(status_code=400, detail="Cartão de crédito inválido ou não encontrado.")
            cycle_day = int(card_cfg["close_day"]) if card_cfg["close_day"] is not None else max(1, int(card_cfg["due_day"]) - 5)
            if cycle_day < 1 or cycle_day > 31:
                raise HTTPException(status_code=400, detail="Dia de fechamento inválido no cartão.")

            today = _date.today()
            start_y, start_m = int(today.year), int(today.month)
            if int(today.day) > int(cycle_day):
                start_y, start_m = _add_months(start_y, start_m, 1)

            # Replica o valor informado em cada mês do parcelamento.
            recurrence_id = f"FUTCC-{uuid4().hex}"
            parcels = int(repeat_months)
            created = 0
            first_date = None
            last_date = None
            for i in range(parcels):
                yy, mm = _add_months(start_y, start_m, i)
                purchase_date = _due_date_for_month(yy, mm, cycle_day)
                if first_date is None:
                    first_date = purchase_date
                last_date = purchase_date
                value_i = round(float(amount_abs), 2)
                desc_i = f"{desc} ({i + 1}/{parcels})" if parcels > 1 else desc
                note_i = f"[{recurrence_id}] {notes}" if notes else f"[{recurrence_id}]"
                repo.register_credit_charge(
                    card_id=int(card_cfg["id"]),
                    purchase_date=purchase_date,
                    amount=float(value_i),
                    category_id=int(category_id) if category_id is not None else None,
                    description=desc_i,
                    note=note_i,
                    user_id=uid,
                )
                created += 1
            return {
                "ok": True,
                "mode": "future_credit_schedule",
                "created": created,
                "first_date": first_date,
                "last_date": last_date,
                "recurrence_id": recurrence_id,
            }

        due_day = int(body.due_day or 0)
        if due_day < 1 or due_day > 31:
            raise HTTPException(status_code=400, detail="Dia de vencimento deve estar entre 1 e 31.")

        today = _date.today()
        start_y, start_m = int(today.year), int(today.month)
        if int(today.day) > int(due_day):
            start_y, start_m = _add_months(start_y, start_m, 1)

        cat_id = int(category_id) if category_id is not None else None
        recurrence_id = f"FUT-{uuid4().hex}"
        created = 0
        first_date = None
        last_date = None
        for i in range(int(repeat_months)):
            yy, mm = _add_months(start_y, start_m, i)
            due_date = _due_date_for_month(yy, mm, due_day)
            if first_date is None:
                first_date = due_date
            last_date = due_date
            repo.insert_transaction(
                date=due_date,
                description=desc,
                amount=-amount_abs,
                account_id=destination_id,
                category_id=cat_id,
                recurrence_id=recurrence_id,
                method="Futuro",
                notes=(f"Forma: {future_pay} | {notes}" if notes else f"Forma: {future_pay}"),
                user_id=uid,
            )
            created += 1
        return {
            "ok": True,
            "mode": "future_schedule",
            "created": created,
            "first_date": first_date,
            "last_date": last_date,
            "recurrence_id": recurrence_id,
        }

    if kind == "Transferencia":
        if body.source_account_id is None:
            raise HTTPException(status_code=400, detail="Conta origem é obrigatória para Transferência")
        source_id = int(body.source_account_id)
        if source_id not in account_map:
            raise HTTPException(status_code=400, detail="Conta origem inválida")
        if source_id == destination_id:
            raise HTTPException(status_code=400, detail="Conta origem e destino devem ser diferentes")

        source = account_map[source_id]
        destination = account_map[destination_id]
        src_type = _norm_account_type(source.get("type"))
        dst_type = _norm_account_type(destination.get("type"))
        allowed_types = {"Banco", "Corretora"}
        if src_type not in allowed_types or dst_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail="Para Transferência, use apenas contas do tipo Banco ou Corretora",
            )

        src_name = str(source.get("name") or "Origem")
        dst_name = str(destination.get("name") or "Destino")
        cat_id = int(category_id) if category_id is not None else None

        repo.insert_transaction(
            date=body.date,
            description=f"TRANSF -> {dst_name} | {desc}",
            amount=-amount_abs,
            account_id=source_id,
            category_id=cat_id,
            method=method,
            notes=notes,
            user_id=uid,
        )
        repo.insert_transaction(
            date=body.date,
            description=f"TRANSF <- {src_name} | {desc}",
            amount=amount_abs,
            account_id=destination_id,
            category_id=cat_id,
            method=method,
            notes=notes,
            user_id=uid,
        )
        return {"ok": True, "mode": "transfer", "created": 2}

    destination = account_map[destination_id]
    if kind == "Despesa":
        if method == "Credito":
            if body.card_id is None:
                raise HTTPException(status_code=400, detail="Para método Crédito, selecione um cartão do tipo Crédito")
            card_cfg = repo.get_credit_card_by_id_and_type(int(body.card_id), "Credito", user_id=uid)
            if not card_cfg:
                raise HTTPException(
                    status_code=400,
                    detail="Cartão de crédito inválido ou não encontrado.",
                )
            repo.register_credit_charge(
                card_id=int(card_cfg["id"]),
                purchase_date=body.date,
                amount=amount_abs,
                category_id=int(category_id) if category_id is not None else None,
                description=desc,
                note=notes,
                user_id=uid,
            )
            return {"ok": True, "mode": "credit_card_charge", "created": 0}
        if method == "Debito" and body.card_id is not None:
            card_cfg = repo.get_credit_card_by_id_and_type(int(body.card_id), "Debito", user_id=uid)
            if not card_cfg:
                raise HTTPException(
                    status_code=400,
                    detail="Cartão de débito inválido ou não encontrado.",
                )
            source_id = int(card_cfg["card_account_id"])
            source_acc = account_map.get(source_id)
            if not source_acc:
                raise HTTPException(status_code=400, detail="Conta banco vinculada ao cartão não encontrada")
            if _norm_account_type(source_acc.get("type")) != "Banco":
                raise HTTPException(status_code=400, detail="Cartão Débito deve estar vinculado a uma conta Banco")
            repo.insert_transaction(
                date=body.date,
                description=f"DEBITO CARTAO {card_cfg.get('name')} | {desc}",
                amount=-amount_abs,
                account_id=source_id,
                category_id=int(category_id) if category_id is not None else None,
                method=method,
                notes=notes,
                user_id=uid,
            )
            return {"ok": True, "mode": "debit_card_expense", "created": 1}
        if method in {"PIX", "Futuro"} and body.card_id is not None:
            raise HTTPException(status_code=400, detail="Método selecionado não usa cartão.")

    signed_amount = amount_abs if kind == "Receita" else -amount_abs
    repo.insert_transaction(
        date=body.date,
        description=desc,
        amount=signed_amount,
        account_id=destination_id,
        category_id=int(category_id) if category_id is not None else None,
        method=method,
        notes=notes,
        user_id=uid,
    )
    return {"ok": True, "mode": "single", "created": 1}


@app.get("/cards")
def list_cards(user: dict = Depends(_current_user)) -> list[dict]:
    uid = int(user["id"])
    rows = repo.list_credit_cards(user_id=uid) or []
    return [_row_to_dict(r) for r in rows]


@app.post("/cards")
def create_card(
    body: CreditCardCreateRequest,
    user: dict = Depends(_current_user),
) -> dict:
    uid = int(user["id"])
    name = (body.name or "").strip()
    brand = _norm_card_brand(body.brand)
    model = _norm_card_model(body.model)
    card_type = _norm_card_type(body.card_type)
    if not name:
        raise HTTPException(status_code=400, detail="Nome do cartão é obrigatório")

    account_map = {int(a["id"]): dict(a) for a in (repo.list_accounts(user_id=uid) or [])}
    linked_acc = account_map.get(int(body.card_account_id))
    if not linked_acc or _norm_account_type(linked_acc.get("type")) != "Banco":
        raise HTTPException(status_code=400, detail="Conta banco vinculada ao cartão é obrigatória e deve ser do tipo Banco")

    if card_type == "Credito":
        if body.due_day is None or int(body.due_day) < 1 or int(body.due_day) > 31:
            raise HTTPException(status_code=400, detail="Dia de vencimento deve estar entre 1 e 31 para cartão Crédito")
        due_day = int(body.due_day)
        close_day = int(body.close_day) if body.close_day is not None else max(1, due_day - 5)
        if close_day < 1 or close_day > 31:
            raise HTTPException(status_code=400, detail="Dia de fechamento deve estar entre 1 e 31 para cartão Crédito")
        if close_day >= due_day:
            raise HTTPException(status_code=400, detail="Dia de fechamento deve ser anterior ao vencimento.")
    else:
        due_day = 1
        close_day = None

    try:
        repo.create_credit_card(
            name=name,
            brand=brand,
            model=model,
            card_type=card_type,
            card_account_id=int(body.card_account_id),
            source_account_id=int(body.card_account_id),
            due_day=due_day,
            close_day=close_day,
            user_id=uid,
        )
    except Exception as e:
        msg = str(e)
        if (
            "UNIQUE constraint failed" in msg
            and ("credit_cards.user_id" in msg or "credit_cards.workspace_id" in msg)
            and "credit_cards.name" in msg
            and "credit_cards.card_type" in msg
        ):
            raise HTTPException(status_code=400, detail="Já existe um cartão com este nome, tipo e conta banco.")
        raise HTTPException(status_code=400, detail=f"Erro ao cadastrar cartão: {e}")
    return {"ok": True}


@app.put("/cards/{card_id}")
def update_card(
    card_id: int,
    body: CreditCardUpdateRequest,
    user: dict = Depends(_current_user),
) -> dict:
    uid = int(user["id"])
    name = (body.name or "").strip()
    brand = _norm_card_brand(body.brand)
    model = _norm_card_model(body.model)
    card_type = _norm_card_type(body.card_type)
    if not name:
        raise HTTPException(status_code=400, detail="Nome do cartão é obrigatório")
    account_map = {int(a["id"]): dict(a) for a in (repo.list_accounts(user_id=uid) or [])}
    linked_acc = account_map.get(int(body.card_account_id))
    if not linked_acc or _norm_account_type(linked_acc.get("type")) != "Banco":
        raise HTTPException(status_code=400, detail="Conta banco vinculada ao cartão é obrigatória e deve ser Banco")
    if card_type == "Credito":
        if body.due_day is None or int(body.due_day) < 1 or int(body.due_day) > 31:
            raise HTTPException(status_code=400, detail="Dia de vencimento deve estar entre 1 e 31 para cartão Crédito")
        due_day = int(body.due_day)
        close_day = int(body.close_day) if body.close_day is not None else max(1, due_day - 5)
        if close_day < 1 or close_day > 31:
            raise HTTPException(status_code=400, detail="Dia de fechamento deve estar entre 1 e 31 para cartão Crédito")
        if close_day >= due_day:
            raise HTTPException(status_code=400, detail="Dia de fechamento deve ser anterior ao vencimento.")
    else:
        due_day = 1
        close_day = None
    try:
        repo.update_credit_card(
            card_id=int(card_id),
            name=name,
            brand=brand,
            model=model,
            card_type=card_type,
            card_account_id=int(body.card_account_id),
            source_account_id=int(body.card_account_id),
            due_day=due_day,
            close_day=close_day,
            user_id=uid,
        )
    except Exception as e:
        msg = str(e)
        if (
            "UNIQUE constraint failed" in msg
            and ("credit_cards.user_id" in msg or "credit_cards.workspace_id" in msg)
            and "credit_cards.name" in msg
            and "credit_cards.card_type" in msg
        ):
            raise HTTPException(status_code=400, detail="Já existe um cartão com este nome, tipo e conta banco.")
        raise HTTPException(status_code=400, detail=f"Erro ao atualizar cartão: {e}")
    return {"ok": True}


@app.delete("/cards/{card_id}")
def delete_card(
    card_id: int,
    user: dict = Depends(_current_user),
) -> dict:
    uid = int(user["id"])
    deleted = repo.delete_credit_card(int(card_id), user_id=uid)
    if not deleted:
        raise HTTPException(status_code=400, detail="Não foi possível excluir cartão (possui faturas/movimentos).")
    return {"ok": True}


@app.get("/card-invoices")
def list_card_invoices(
    status: str | None = None,
    card_id: int | None = None,
    user: dict = Depends(_current_user),
) -> list[dict]:
    uid = int(user["id"])
    st = (status or "").strip().upper() or None
    if st and st not in {"OPEN", "PAID"}:
        raise HTTPException(status_code=400, detail="Status inválido")
    rows = repo.list_credit_card_invoices(user_id=uid, status=st, card_id=card_id) or []
    return [_row_to_dict(r) for r in rows]


@app.post("/card-invoices/{invoice_id}/pay")
def pay_card_invoice(
    invoice_id: int,
    body: CreditCardPayInvoiceRequest,
    user: dict = Depends(_current_user),
) -> dict:
    uid = int(user["id"])
    try:
        out = repo.pay_credit_card_invoice(
            int(invoice_id),
            payment_date=body.payment_date,
            source_account_id=body.source_account_id,
            user_id=uid,
        )
        return out
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/transactions/{tx_id}")
def delete_transaction(
    tx_id: int,
    scope: str = Query(default="single"),
    user: dict = Depends(_current_user),
) -> dict:
    uid = int(user["id"])
    mode = str(scope or "single").strip().lower()
    if mode not in {"single", "future"}:
        raise HTTPException(status_code=400, detail="Escopo inválido. Use 'single' ou 'future'.")
    deleted = repo.delete_transaction_with_scope(int(tx_id), scope=mode, user_id=uid)
    return {"ok": True, "deleted": int(deleted), "scope": mode}


@app.delete("/credit-commitments/{charge_id}")
def delete_credit_commitment(
    charge_id: int,
    scope: str = Query(default="single"),
    user: dict = Depends(_current_user),
) -> dict:
    uid = int(user["id"])
    mode = str(scope or "single").strip().lower()
    if mode not in {"single", "future"}:
        raise HTTPException(status_code=400, detail="Escopo inválido. Use 'single' ou 'future'.")
    deleted = repo.delete_credit_commitment_with_scope(int(charge_id), scope=mode, user_id=uid)
    return {"ok": True, "deleted": int(deleted), "scope": mode}


@app.post("/transactions/{tx_id}/settle-commitment")
def settle_commitment_transaction(
    tx_id: int,
    body: CommitmentSettleRequest,
    user: dict = Depends(_current_user),
) -> dict:
    uid = int(user["id"])
    try:
        _date.fromisoformat(str(body.payment_date))
    except Exception:
        raise HTTPException(status_code=400, detail="Data de pagamento inválida. Use YYYY-MM-DD.")

    amount_abs = abs(float(body.amount or 0.0))
    if amount_abs <= 0:
        raise HTTPException(status_code=400, detail="Valor deve ser maior que zero")

    account_map = {int(a["id"]): dict(a) for a in (repo.list_accounts(user_id=uid) or [])}
    acc = account_map.get(int(body.account_id))
    if not acc:
        raise HTTPException(status_code=400, detail="Conta inválida")
    if _norm_account_type(acc.get("type")) not in {"Banco", "Dinheiro"}:
        raise HTTPException(status_code=400, detail="Pagamento deve ser em conta do tipo Banco ou Dinheiro")

    try:
        repo.settle_commitment_transaction(
            tx_id=int(tx_id),
            payment_date=str(body.payment_date),
            account_id=int(body.account_id),
            amount=amount_abs,
            notes=body.notes,
            user_id=uid,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "mode": "settled_commitment", "id": int(tx_id)}


@app.get("/dashboard/kpis")
def dashboard_kpis(
    date_from: str | None = None,
    date_to: str | None = None,
    account: str | None = None,
    view: str = Query(default="caixa"),
    user: dict = Depends(_current_user),
) -> dict:
    uid = int(user["id"])
    mode = _norm_view(view)
    df = reports.df_transactions(date_from=date_from, date_to=date_to, user_id=uid, view=mode)
    if account and not df.empty:
        df = df[df["account"] == account]
    return reports.kpis(df)


@app.get("/dashboard/monthly")
def dashboard_monthly(
    date_from: str | None = None,
    date_to: str | None = None,
    account: str | None = None,
    view: str = Query(default="caixa"),
    user: dict = Depends(_current_user),
) -> list[dict]:
    uid = int(user["id"])
    mode = _norm_view(view)
    df = reports.df_transactions(date_from=date_from, date_to=date_to, user_id=uid, view=mode)
    if account and not df.empty:
        df = df[df["account"] == account]
    out = reports.monthly_summary(df)
    if out.empty:
        return []
    return out.to_dict(orient="records")


@app.get("/dashboard/expenses-by-category")
def dashboard_expenses_by_category(
    date_from: str | None = None,
    date_to: str | None = None,
    account: str | None = None,
    view: str = Query(default="caixa"),
    user: dict = Depends(_current_user),
) -> list[dict]:
    uid = int(user["id"])
    mode = _norm_view(view)
    df = reports.df_transactions(date_from=date_from, date_to=date_to, user_id=uid, view=mode)
    if account and not df.empty:
        df = df[df["account"] == account]
    out = reports.category_expenses(df)
    if out.empty:
        return []
    return out.to_dict(orient="records")


@app.get("/dashboard/account-balance")
def dashboard_account_balance(
    date_from: str | None = None,
    date_to: str | None = None,
    account: str | None = None,
    view: str = Query(default="caixa"),
    user: dict = Depends(_current_user),
) -> list[dict]:
    uid = int(user["id"])
    mode = _norm_view(view)
    df = reports.df_transactions(date_from=date_from, date_to=date_to, user_id=uid, view=mode)
    if account and not df.empty:
        df = df[df["account"] == account]
    out = reports.account_balance(df)
    if out.empty:
        return []
    return out.to_dict(orient="records")


@app.get("/dashboard/commitments-summary")
def dashboard_commitments_summary(
    date_from: str | None = None,
    date_to: str | None = None,
    account: str | None = None,
    user: dict = Depends(_current_user),
) -> dict:
    uid = int(user["id"])
    return reports.commitments_summary(
        date_from=date_from,
        date_to=date_to,
        account=account,
        user_id=uid,
    )


@app.get("/invest/meta")
def invest_meta(user: dict = Depends(_current_user)) -> dict:
    return {
        "asset_classes": list(invest_repo.ASSET_CLASSES.keys()),
        "asset_sectors": list(invest_repo.ASSET_SECTORS),
        "income_types": list(invest_repo.INCOME_TYPES.keys()),
        "index_names": list(invest_index_rates.SUPPORTED_INDEX_NAMES),
    }


@app.get("/invest/index-rates")
def invest_list_index_rates(
    index_name: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = Query(default=1000, ge=1, le=10000),
    user: dict = Depends(_current_user),
) -> list[dict]:
    uid = int(user["id"])
    try:
        rows = invest_index_rates.list_index_rates(
            index_name=index_name,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            user_id=uid,
        )
        return rows
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/invest/index-rates/upsert")
def invest_upsert_index_rates(
    body: IndexRatesUpsertRequest,
    user: dict = Depends(_current_user),
) -> dict:
    _require_admin(user)
    points = [
        {
            "ref_date": (p.ref_date or "").strip(),
            "value": float(p.value),
            "source": (p.source or "").strip() or None,
        }
        for p in (body.points or [])
    ]
    if not points:
        raise HTTPException(status_code=400, detail="Informe ao menos um ponto para carga.")

    try:
        result = invest_index_rates.bulk_upsert_index_rates(
            index_name=body.index_name,
            points=points,
            source=(body.source or "").strip() or None,
            user_id=int(user["id"]),
        )
        return {"ok": True, **result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/invest/index-rates/sync")
def invest_sync_index_rates(
    body: IndexRatesSyncRequest,
    user: dict = Depends(_current_user),
) -> dict:
    _require_admin(user)
    try:
        out = invest_index_rates.sync_from_bcb(
            index_names=body.index_names,
            date_from=body.date_from,
            date_to=body.date_to,
            timeout_s=float(body.timeout_s) if body.timeout_s is not None else 20.0,
            user_id=int(user["id"]),
        )
        return {"ok": True, **out}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/invest/rentability/update/{asset_id}")
def invest_update_asset_rentability(
    asset_id: int,
    body: RentabilityUpdateRequest | None = None,
    user: dict = Depends(_current_user),
) -> dict:
    uid = int(user["id"])
    as_of_date = (body.as_of_date if body else None)
    try:
        return invest_rentability.update_investment_value(
            asset_id=int(asset_id),
            as_of_date=as_of_date,
            user_id=uid,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/invest/rentability/update-all")
def invest_update_all_rentability(
    body: RentabilityUpdateRequest | None = None,
    user: dict = Depends(_current_user),
) -> dict:
    uid = int(user["id"])
    as_of_date = (body.as_of_date if body else None)
    try:
        return invest_rentability.update_fixed_income_assets(
            as_of_date=as_of_date,
            user_id=uid,
            only_auto=bool(body.only_auto) if body else True,
            reset_from_principal=bool(body.reset_from_principal) if body else False,
            asset_ids=(body.asset_ids or []) if body else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/invest/rentability/divergence-report")
def invest_rentability_divergence_report(
    body: RentabilityDivergenceRequest | None = None,
    user: dict = Depends(_current_user),
) -> dict:
    uid = int(user["id"])
    as_of_date = (body.as_of_date if body else None)
    try:
        return invest_rentability.preview_divergence_report(
            as_of_date=as_of_date,
            user_id=uid,
            only_auto=bool(body.only_auto) if body else True,
            threshold_pct=float(body.threshold_pct or 0.0) if body else 0.0,
            limit=int(body.limit or 200) if body else 200,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/invest/assets")
def invest_list_assets(user: dict = Depends(_current_user)) -> list[dict]:
    uid = int(user["id"])
    rows = invest_repo.list_assets(user_id=uid) or []
    return [_row_to_dict(r) for r in rows]


@app.post("/invest/assets")
def invest_create_asset(
    body: AssetCreateRequest,
    user: dict = Depends(_current_user),
) -> dict:
    uid = int(user["id"])
    symbol = (body.symbol or "").strip().upper()
    name = (body.name or "").strip()
    if not symbol or not name:
        raise HTTPException(status_code=400, detail="Símbolo e nome são obrigatórios")
    if body.asset_class not in invest_repo.ASSET_CLASSES:
        raise HTTPException(status_code=400, detail="Classe de ativo inválida")
    sector = (body.sector or "Não definido").strip() or "Não definido"
    if sector not in invest_repo.ASSET_SECTORS:
        sector = "Não definido"

    # validate referenced accounts ownership
    account_ids = {int(r["id"]) for r in (repo.list_accounts(user_id=uid) or [])}
    if body.broker_account_id is not None and int(body.broker_account_id) not in account_ids:
        raise HTTPException(status_code=400, detail="Conta corretora inválida")
    if body.source_account_id is not None and int(body.source_account_id) not in account_ids:
        raise HTTPException(status_code=400, detail="Conta origem inválida")

    rent_cfg = _validate_asset_rentability(
        asset_class=body.asset_class,
        rentability_type=body.rentability_type,
        index_name=body.index_name,
        index_pct=body.index_pct,
        spread_rate=body.spread_rate,
        fixed_rate=body.fixed_rate,
    )

    created = invest_repo.create_asset(
        symbol=symbol,
        name=name,
        asset_class=body.asset_class,
        sector=sector,
        currency=(body.currency or "BRL").strip().upper(),
        broker_account_id=body.broker_account_id,
        source_account_id=body.source_account_id,
        issuer=(body.issuer or "").strip() or None,
        rate_type=(body.rate_type or "").strip() or None,
        rate_value=body.rate_value,
        maturity_date=(body.maturity_date or "").strip() or None,
        rentability_type=rent_cfg["rentability_type"],
        index_name=rent_cfg["index_name"],
        index_pct=rent_cfg["index_pct"],
        spread_rate=rent_cfg["spread_rate"],
        fixed_rate=rent_cfg["fixed_rate"],
        principal_amount=body.principal_amount,
        current_value=body.current_value,
        last_update=(body.last_update or "").strip() or None,
        user_id=uid,
    )
    return {"ok": True, "created": bool(created)}


@app.put("/invest/assets/{asset_id}")
def invest_update_asset(
    asset_id: int,
    body: AssetUpdateRequest,
    user: dict = Depends(_current_user),
) -> dict:
    uid = int(user["id"])
    asset = invest_repo.get_asset_by_id(asset_id, user_id=uid)
    if not asset:
        raise HTTPException(status_code=404, detail="Ativo não encontrado")
    if body.asset_class not in invest_repo.ASSET_CLASSES:
        raise HTTPException(status_code=400, detail="Classe de ativo inválida")
    sector = (body.sector or "Não definido").strip() or "Não definido"
    if sector not in invest_repo.ASSET_SECTORS:
        sector = "Não definido"

    account_ids = {int(r["id"]) for r in (repo.list_accounts(user_id=uid) or [])}
    if body.broker_account_id is not None and int(body.broker_account_id) not in account_ids:
        raise HTTPException(status_code=400, detail="Conta corretora inválida")
    if body.source_account_id is not None and int(body.source_account_id) not in account_ids:
        raise HTTPException(status_code=400, detail="Conta origem inválida")

    raw_payload = (
        body.model_dump(exclude_unset=True)
        if hasattr(body, "model_dump")
        else body.dict(exclude_unset=True)
    )
    optional_updates: dict[str, Any] = {}
    for text_field in ["issuer", "rate_type", "maturity_date", "rentability_type", "index_name", "last_update"]:
        if text_field in raw_payload:
            optional_updates[text_field] = (raw_payload.get(text_field) or "").strip() or None
    for numeric_field in ["rate_value", "index_pct", "spread_rate", "fixed_rate", "principal_amount", "current_value"]:
        if numeric_field in raw_payload:
            optional_updates[numeric_field] = raw_payload.get(numeric_field)
    if "source_account_id" in raw_payload:
        optional_updates["source_account_id"] = raw_payload.get("source_account_id")

    rent_cfg = _validate_asset_rentability(
        asset_class=body.asset_class,
        rentability_type=optional_updates.get("rentability_type", asset.get("rentability_type")),
        index_name=optional_updates.get("index_name", asset.get("index_name")),
        index_pct=optional_updates.get("index_pct", asset.get("index_pct")),
        spread_rate=optional_updates.get("spread_rate", asset.get("spread_rate")),
        fixed_rate=optional_updates.get("fixed_rate", asset.get("fixed_rate")),
    )
    optional_updates["rentability_type"] = rent_cfg["rentability_type"]
    optional_updates["index_name"] = rent_cfg["index_name"]
    optional_updates["index_pct"] = rent_cfg["index_pct"]
    optional_updates["spread_rate"] = rent_cfg["spread_rate"]
    optional_updates["fixed_rate"] = rent_cfg["fixed_rate"]

    invest_repo.update_asset(
        asset_id=asset_id,
        symbol=(body.symbol or "").strip().upper(),
        name=(body.name or "").strip(),
        asset_class=body.asset_class,
        sector=sector,
        currency=(body.currency or "BRL").strip().upper(),
        broker_account_id=body.broker_account_id,
        user_id=uid,
        **optional_updates,
    )
    return {"ok": True}


@app.delete("/invest/assets/{asset_id}")
def invest_delete_asset(
    asset_id: int,
    user: dict = Depends(_current_user),
) -> dict:
    uid = int(user["id"])
    ok, msg = invest_repo.delete_asset(asset_id, user_id=uid)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


@app.get("/invest/trades")
def invest_list_trades(
    date_from: str | None = None,
    date_to: str | None = None,
    asset_id: int | None = None,
    user: dict = Depends(_current_user),
) -> list[dict]:
    uid = int(user["id"])
    rows = invest_repo.list_trades(asset_id=asset_id, date_from=date_from, date_to=date_to, user_id=uid) or []
    return [_row_to_dict(r) for r in rows]


@app.post("/invest/trades")
def invest_create_trade(
    body: TradeCreateRequest,
    user: dict = Depends(_current_user),
) -> dict:
    uid = int(user["id"])
    side = _norm_trade_side(body.side)
    if side not in {"BUY", "SELL"}:
        raise HTTPException(status_code=400, detail="Tipo da operação inválido")
    if float(body.quantity) <= 0 or float(body.price) <= 0:
        raise HTTPException(status_code=400, detail="Quantidade e preço devem ser maiores que zero")
    fees = float(body.fees or 0.0)
    taxes = float(body.taxes or 0.0)
    if fees < 0 or taxes < 0:
        raise HTTPException(status_code=400, detail="Taxas e impostos não podem ser negativos")

    asset = invest_repo.get_asset(int(body.asset_id), user_id=uid)
    if not asset:
        raise HTTPException(status_code=404, detail="Ativo não encontrado")
    broker_acc_id = asset["broker_account_id"]
    if not broker_acc_id:
        raise HTTPException(status_code=400, detail="Ativo sem conta corretora vinculada")

    qty = float(body.quantity)
    price = float(body.price)
    is_us_stock = _is_us_stock_asset(asset)
    is_fixed_income = _is_fixed_income_asset(asset)
    exchange_rate = float(body.exchange_rate or 0.0)
    if is_us_stock and exchange_rate <= 0:
        raise HTTPException(status_code=400, detail="Cotação USD/BRL é obrigatória para Stocks US")
    fx = exchange_rate if is_us_stock else 1.0

    gross = qty * price * fx
    fees_brl = fees * fx if is_us_stock else fees
    taxes_brl = taxes * fx if is_us_stock else taxes
    # Em renda fixa, impostos de IR/IOF devem incidir no resgate, não na aplicação.
    total_cost = (gross + fees_brl) if is_fixed_income else (gross + fees_brl + taxes_brl)
    if total_cost < 0:
        total_cost = 0.0
    broker_cash = reports.account_balance_by_id(int(broker_acc_id), user_id=uid)
    # Tolerância para evitar falso "saldo insuficiente" por ruído de float.
    if side == "BUY" and (broker_cash + 0.005) < total_cost:
        raise HTTPException(
            status_code=400,
            detail=f"Saldo insuficiente na corretora. Disponível: {broker_cash:.2f}; Necessário: {total_cost:.2f}",
        )

    symbol = str(asset["symbol"]).strip().upper()
    if side == "BUY":
        cash = -total_cost
        desc = f"INV BUY {symbol}"
    else:
        cash = +(gross - fees_brl - taxes_brl)
        desc = f"INV SELL {symbol}"

    cat_id = repo.ensure_category("Investimentos", "Transferencia", user_id=uid)
    repo.insert_transaction(
        date=body.date,
        description=desc,
        amount=float(cash),
        account_id=int(broker_acc_id),
        category_id=int(cat_id),
        method="INV",
        notes=(body.note or "").strip() or None,
        user_id=uid,
    )
    invest_repo.insert_trade(
        asset_id=int(body.asset_id),
        date=body.date,
        side=side,
        quantity=qty,
        price=price,
        exchange_rate=fx,
        fees=fees,
        taxes=taxes,
        note=(body.note or "").strip() or None,
        user_id=uid,
    )
    return {"ok": True}


@app.delete("/invest/trades/{trade_id}")
def invest_delete_trade(
    trade_id: int,
    user: dict = Depends(_current_user),
) -> dict:
    uid = int(user["id"])
    ok, msg = invest_repo.delete_trade_with_cash_reversal(int(trade_id), user_id=uid)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


@app.get("/invest/portfolio")
def invest_portfolio(user: dict = Depends(_current_user)) -> dict:
    uid = int(user["id"])
    pos, trades_df, incomes_df = invest_reports.portfolio_view(user_id=uid)
    return {
        "positions": [] if pos is None or pos.empty else pos.to_dict(orient="records"),
        "trades": [] if trades_df is None or trades_df.empty else trades_df.to_dict(orient="records"),
        "incomes": [] if incomes_df is None or incomes_df.empty else incomes_df.to_dict(orient="records"),
    }


@app.get("/invest/summary")
def invest_summary(user: dict = Depends(_current_user)) -> dict:
    uid = int(user["id"])
    pos, _, _ = invest_reports.portfolio_view(user_id=uid)

    if pos is None or pos.empty:
        total_invested = 0.0
        total_market = 0.0
        total_income = 0.0
        total_realized = 0.0
        total_unreal = 0.0
        total_return = 0.0
    else:
        for col in ["income", "realized_pnl", "unrealized_pnl", "market_value", "cost_basis"]:
            if col not in pos.columns:
                pos[col] = 0.0

        total_invested = float(pos["cost_basis"].fillna(0.0).sum())
        total_market = float(pos["market_value"].fillna(0.0).sum())
        total_income = float(pos["income"].fillna(0.0).sum())
        total_realized = float(pos["realized_pnl"].fillna(0.0).sum())
        total_unreal = float(pos["unrealized_pnl"].fillna(0.0).sum())
        total_return = float(total_unreal + total_realized + total_income)

    total_return_pct = (total_return / total_invested * 100.0) if total_invested > 0 else 0.0

    accounts = repo.list_accounts(user_id=uid) or []
    broker_names = [str(a["name"]) for a in accounts if str(a["type"]) == "Corretora"]
    all_tx = reports.df_transactions(user_id=uid)
    if all_tx is None or all_tx.empty or not broker_names:
        broker_balance = 0.0
    else:
        broker_balance = float(all_tx[all_tx["account"].isin(broker_names)]["amount_brl"].sum())

    return {
        "assets_count": 0 if pos is None or pos.empty else int(len(pos)),
        "total_invested": total_invested,
        "total_market": total_market,
        "total_income": total_income,
        "total_realized": total_realized,
        "total_unrealized": total_unreal,
        "total_return": total_return,
        "total_return_pct": total_return_pct,
        "broker_balance": broker_balance,
    }


@app.get("/invest/incomes")
def invest_list_incomes(
    date_from: str | None = None,
    date_to: str | None = None,
    asset_id: int | None = None,
    user: dict = Depends(_current_user),
) -> list[dict]:
    uid = int(user["id"])
    rows = invest_repo.list_income(asset_id=asset_id, date_from=date_from, date_to=date_to, user_id=uid) or []
    return [_row_to_dict(r) for r in rows]


@app.post("/invest/incomes")
def invest_create_income(
    body: IncomeCreateRequest,
    user: dict = Depends(_current_user),
) -> dict:
    uid = int(user["id"])
    if float(body.amount) <= 0:
        raise HTTPException(status_code=400, detail="Valor do provento deve ser maior que zero")
    if body.type not in invest_repo.INCOME_TYPES:
        raise HTTPException(status_code=400, detail="Tipo de provento inválido")

    asset = invest_repo.get_asset(int(body.asset_id), user_id=uid)
    if not asset:
        raise HTTPException(status_code=404, detail="Ativo não encontrado")

    note = (body.note or "").strip() or None
    invest_repo.insert_income(
        asset_id=int(body.asset_id),
        date=body.date,
        type_=body.type,
        amount=float(body.amount),
        note=note,
        user_id=uid,
    )

    broker_acc_id = asset["broker_account_id"]
    if broker_acc_id:
        cat_id = repo.ensure_category("Investimentos", "Receita", user_id=uid)
        desc = f"PROVENTO {asset['symbol']} ({body.type})"
        repo.create_transaction(
            date=body.date,
            description=desc,
            amount=float(body.amount),
            category_id=int(cat_id),
            account_id=int(broker_acc_id),
            method="INV",
            notes=note,
            user_id=uid,
        )
    return {"ok": True}


@app.delete("/invest/incomes/{income_id}")
def invest_delete_income(
    income_id: int,
    user: dict = Depends(_current_user),
) -> dict:
    uid = int(user["id"])
    invest_repo.delete_income(int(income_id), user_id=uid)
    return {"ok": True}


@app.get("/invest/prices")
def invest_list_prices(
    asset_id: int | None = None,
    limit: int = Query(default=200, ge=1, le=2000),
    user: dict = Depends(_current_user),
) -> list[dict]:
    uid = int(user["id"])
    rows = invest_repo.list_prices(asset_id=asset_id, limit=int(limit), user_id=uid) or []
    return [_row_to_dict(r) for r in rows]


@app.post("/invest/prices")
def invest_upsert_price(
    body: PriceUpsertRequest,
    user: dict = Depends(_current_user),
) -> dict:
    uid = int(user["id"])
    if float(body.price) <= 0:
        raise HTTPException(status_code=400, detail="Preço deve ser maior que zero")
    asset = invest_repo.get_asset(int(body.asset_id), user_id=uid)
    if not asset:
        raise HTTPException(status_code=404, detail="Ativo não encontrado")
    invest_repo.upsert_price(
        asset_id=int(body.asset_id),
        date=body.date,
        price=float(body.price),
        source=(body.source or "").strip() or "manual",
        user_id=uid,
    )
    return {"ok": True}


@app.post("/invest/prices/update-all")
def invest_update_all_prices(
    body: QuoteUpdateAllRequest,
    user: dict = Depends(_current_user),
) -> dict:
    uid = int(user["id"])
    assets = invest_repo.list_assets(user_id=uid) or []
    include_groups = {
        str(g or "").strip()
        for g in (body.include_groups or [])
        if str(g or "").strip()
    }
    if include_groups:
        assets = [a for a in assets if _quote_group_for_asset(dict(a)) in include_groups]
    if not assets:
        return {"ok": True, "saved": 0, "total": 0, "report": []}
    report = invest_quotes.update_all_prices(
        assets=[dict(a) for a in assets],
        timeout_s=body.timeout_s,
        max_workers=body.max_workers,
    )
    saved = 0
    for r in report:
        if r.get("ok"):
            invest_repo.upsert_price(
                asset_id=int(r["asset_id"]),
                date=str(r["px_date"]),
                price=float(r["price"]),
                source=r.get("src") or "auto",
                user_id=uid,
            )
            saved += 1
    return {"ok": True, "saved": saved, "total": len(report), "report": report}


@app.middleware("http")
async def tenant_cleanup_middleware(request, call_next):
    # Defensive cleanup in case lower layers set tenant context.
    try:
        response = await call_next(request)
        return response
    finally:
        clear_tenant_context()
