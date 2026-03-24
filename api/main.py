from __future__ import annotations

import os
import re
import calendar
import logging
from html import escape
from typing import Any
from datetime import date as _date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from uuid import uuid4
from zoneinfo import ZoneInfo

import requests
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, Request, Response, UploadFile
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
    AssetFairValueUpdateRequest,
    AssetCreateRequest,
    AssetUpdateRequest,
    CategoryCreateRequest,
    CategoryUpdateRequest,
    CreditCardCreateRequest,
    CreditCardPayInvoiceRequest,
    CreditCardUpdateRequest,
    ForgotPasswordRequest,
    CommitmentSettleRequest,
    LoginRequest,
    LoginResponse,
    ManualAssetValueUpdateRequest,
    ProfileUpdateRequest,
    UserGlobalRoleUpdateRequest,
    WorkspaceAdminCreateRequest,
    WorkspaceMemberCreateRequest,
    WorkspacePermissionItemRequest,
    WorkspacePermissionsUpdateRequest,
    WorkspaceRenameRequest,
    WorkspaceStatusUpdateRequest,
    WorkspaceSwitchRequest,
    IncomeCreateRequest,
    IndexRatesSyncRequest,
    IndexRatesUpsertRequest,
    PriceUpsertRequest,
    QuoteUpdateAllRequest,
    RentabilityDivergenceRequest,
    RentabilityUpdateRequest,
    ResetPasswordRequest,
    TradeCreateRequest,
    TransactionCreateRequest,
)
from .security import create_token, verify_token


app = FastAPI(title="Controle Financeiro API", version="0.1.0")
VALID_VIEWS = {"caixa", "competencia", "futuro"}
logger = logging.getLogger(__name__)
QUOTE_JOB_TIMEZONE = "America/Sao_Paulo"
QUOTE_JOB_START_AT = time(hour=10, minute=0)
QUOTE_JOB_END_AT = time(hour=17, minute=10)


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


def _quote_job_schedule_context(now: datetime | None = None) -> dict[str, str]:
    tz = ZoneInfo(QUOTE_JOB_TIMEZONE)
    base_now = now.astimezone(tz) if isinstance(now, datetime) else datetime.now(tz)
    current = base_now
    for _ in range(10):
        if current.weekday() < 5:
            start_dt = datetime.combine(current.date(), QUOTE_JOB_START_AT, tzinfo=tz)
            end_dt = datetime.combine(current.date(), QUOTE_JOB_END_AT, tzinfo=tz)
            if base_now <= start_dt:
                next_run = start_dt
            elif base_now <= end_dt:
                next_run = base_now
            else:
                current = current + timedelta(days=1)
                continue
            return {
                "timezone": QUOTE_JOB_TIMEZONE,
                "start_at": QUOTE_JOB_START_AT.strftime("%H:%M"),
                "end_at": QUOTE_JOB_END_AT.strftime("%H:%M"),
                "next_run_at": next_run.isoformat(),
            }
        current = current + timedelta(days=1)
    return {
        "timezone": QUOTE_JOB_TIMEZONE,
        "start_at": QUOTE_JOB_START_AT.strftime("%H:%M"),
        "end_at": QUOTE_JOB_END_AT.strftime("%H:%M"),
        "next_run_at": base_now.isoformat(),
    }


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
        "CDI_SPREAD": "CDI_SPREAD",
        "CDI_X": "CDI_SPREAD",
        "SELIC_SPREAD": "SELIC_SPREAD",
        "SELIC_X": "SELIC_SPREAD",
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

    valid_types = {"PREFIXADO", "PCT_CDI", "PCT_SELIC", "CDI_SPREAD", "SELIC_SPREAD", "IPCA_SPREAD", "MANUAL"}
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

    if rt == "CDI_SPREAD":
        if idx != "CDI":
            raise HTTPException(status_code=400, detail="CDI_SPREAD exige index_name=CDI.")
        if sr is None:
            raise HTTPException(status_code=400, detail="CDI_SPREAD exige spread_rate.")
        if any(v is not None for v in [ip, fr]):
            raise HTTPException(status_code=400, detail="CDI_SPREAD não permite index_pct/fixed_rate.")
        return {
            "rentability_type": "CDI_SPREAD",
            "index_name": "CDI",
            "index_pct": None,
            "spread_rate": sr,
            "fixed_rate": None,
        }

    if rt == "SELIC_SPREAD":
        if idx != "SELIC":
            raise HTTPException(status_code=400, detail="SELIC_SPREAD exige index_name=SELIC.")
        if sr is None:
            raise HTTPException(status_code=400, detail="SELIC_SPREAD exige spread_rate.")
        if any(v is not None for v in [ip, fr]):
            raise HTTPException(status_code=400, detail="SELIC_SPREAD não permite index_pct/fixed_rate.")
        return {
            "rentability_type": "SELIC_SPREAD",
            "index_name": "SELIC",
            "index_pct": None,
            "spread_rate": sr,
            "fixed_rate": None,
        }

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


def _validate_asset_fair_value_fields(
    fair_price: Any,
    safety_margin_pct: Any,
) -> dict[str, float | None]:
    fair = None if fair_price is None else float(fair_price)
    margin = None if safety_margin_pct is None else float(safety_margin_pct)
    if fair is not None and fair <= 0:
        raise HTTPException(status_code=400, detail="Preço justo deve ser maior que zero.")
    if margin is not None and (margin < 0 or margin > 100):
        raise HTTPException(status_code=400, detail="Margem de segurança deve estar entre 0 e 100%.")
    return {
        "fair_price": fair,
        "safety_margin_pct": margin,
    }


def _validate_asset_user_objective(user_objective: Any) -> str | None:
    if user_objective is None:
        return None
    objective = str(user_objective or "").strip().lower()
    if not objective:
        return None
    if objective not in invest_repo.USER_OBJECTIVES:
        raise HTTPException(status_code=400, detail="Objetivo do usuário inválido.")
    return objective


def _sanitize_download_filename(file_name: str, fallback: str = "avaliacao.pdf") -> str:
    raw = str(file_name or "").strip()
    cleaned = re.sub(r'[^A-Za-z0-9._ -]+', "_", raw).strip(" .")
    if not cleaned:
        cleaned = fallback
    if not cleaned.lower().endswith(".pdf"):
        cleaned = f"{cleaned}.pdf"
    return cleaned


_CURRENT_VALUE_Q = Decimal("0.000001")


def _to_decimal_or_none(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _resolve_manual_rentability_updates(
    *,
    rentability_type: str | None,
    rate_value: Any,
    current_value: Any = None,
    principal_amount: Any,
    existing_rate_type: Any = None,
    existing_current_value: Any = None,
    existing_principal_amount: Any = None,
) -> dict[str, Any]:
    rt = _norm_rentability_type(rentability_type)
    parsed_rate = _to_decimal_or_none(rate_value)
    if parsed_rate is not None and parsed_rate < Decimal("-100"):
        raise HTTPException(status_code=400, detail="Rentabilidade manual não pode ser menor que -100%.")

    if rt != "MANUAL":
        if (existing_rate_type or "") == "MANUAL_RETURN":
            return {"rate_type": None, "rate_value": None}
        return {}

    if parsed_rate is None:
        return {}

    base_value = _to_decimal_or_none(current_value)
    if base_value is None:
        base_value = _to_decimal_or_none(existing_current_value)
    if base_value is None:
        base_value = _to_decimal_or_none(principal_amount)
    if base_value is None:
        base_value = _to_decimal_or_none(existing_principal_amount)
    if base_value is None or base_value <= 0:
        raise HTTPException(
            status_code=400,
            detail="Rentabilidade manual exige um valor base no ativo. Informe valor atual ou registre a aplicação primeiro.",
        )

    current_value = (base_value * (Decimal("1") + (parsed_rate / Decimal("100")))).quantize(
        _CURRENT_VALUE_Q,
        rounding=ROUND_HALF_UP,
    )
    return {
        "rate_type": "MANUAL_RETURN",
        "rate_value": float(parsed_rate),
        "current_value": float(current_value),
        "last_update": _date.today().isoformat(),
    }


def _resolve_manual_current_value_update(
    *,
    current_value: Any,
    ref_date: str | None = None,
) -> dict[str, Any]:
    parsed_current = _to_decimal_or_none(current_value)
    if parsed_current is None or parsed_current <= 0:
        raise HTTPException(status_code=400, detail="Informe um valor atual válido.")
    return {
        "rate_type": None,
        "rate_value": None,
        "current_value": float(parsed_current.quantize(_CURRENT_VALUE_Q, rounding=ROUND_HALF_UP)),
        "last_update": (ref_date or "").strip() or _date.today().isoformat(),
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


def _request_user_agent(request: Request | None) -> str | None:
    try:
        raw = request.headers.get("user-agent", "") if request else ""
    except Exception:
        raw = ""
    return str(raw or "").strip() or None


def _password_reset_target_url(raw_token: str) -> str:
    base = str(os.getenv("APP_PASSWORD_RESET_URL", "") or "").strip()
    if not base:
        app_base = str(os.getenv("APP_BASE_URL", "") or "").strip().rstrip("/")
        base = f"{app_base}/reset-password" if app_base else "http://localhost:5173/reset-password"
    sep = "&" if "?" in base else "?"
    return f"{base}{sep}token={raw_token}"


def _send_password_reset_email(*, email: str, raw_token: str) -> bool:
    api_key = str(os.getenv("RESEND_API_KEY", "") or "").strip()
    from_email = str(os.getenv("RESEND_FROM_EMAIL", "") or "").strip()
    if not api_key or not from_email:
        logger.warning("Password reset requested but Resend is not configured.")
        return False

    reset_url = _password_reset_target_url(raw_token)
    safe_url = escape(reset_url, quote=True)
    payload = {
        "from": from_email,
        "to": [email],
        "subject": "Redefinicao de senha do Domus",
        "html": (
            "<p>Recebemos uma solicitacao para redefinir sua senha no Domus.</p>"
            f"<p><a href=\"{safe_url}\">Clique aqui para redefinir sua senha</a></p>"
            "<p>Este link expira em 30 minutos. Se voce nao solicitou a alteracao, ignore este e-mail.</p>"
        ),
        "text": (
            "Recebemos uma solicitacao para redefinir sua senha no Domus.\n\n"
            f"Abra este link: {reset_url}\n\n"
            "Este link expira em 30 minutos. Se voce nao solicitou a alteracao, ignore este e-mail."
        ),
    }
    resp = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=10,
    )
    resp.raise_for_status()
    return True


def _send_first_access_email(*, email: str, raw_token: str) -> bool:
    api_key = str(os.getenv("RESEND_API_KEY", "") or "").strip()
    from_email = str(os.getenv("RESEND_FROM_EMAIL", "") or "").strip()
    if not api_key or not from_email:
        logger.warning("First access requested but Resend is not configured.")
        return False

    reset_url = _password_reset_target_url(raw_token)
    safe_url = escape(reset_url, quote=True)
    payload = {
        "from": from_email,
        "to": [email],
        "subject": "Crie sua senha de acesso ao Domus",
        "html": (
            "<p>Seu acesso ao Domus foi criado.</p>"
            "<p>Para concluir o primeiro acesso, defina sua senha pelo link abaixo.</p>"
            f"<p><a href=\"{safe_url}\">Criar senha de acesso</a></p>"
            "<p>Este link expira em 30 minutos. Se voce nao esperava este convite, ignore este e-mail.</p>"
        ),
        "text": (
            "Seu acesso ao Domus foi criado.\n\n"
            "Para concluir o primeiro acesso, defina sua senha neste link:\n"
            f"{reset_url}\n\n"
            "Este link expira em 30 minutos. Se voce nao esperava este convite, ignore este e-mail."
        ),
    }
    resp = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=10,
    )
    resp.raise_for_status()
    return True


def _issue_first_access_email(*, email: str, request: Request | None = None) -> bool:
    raw_token = auth.create_password_reset_request(
        email=email,
        request_ip=_request_ip(request),
        request_user_agent=_request_user_agent(request),
    )
    if not raw_token:
        return False
    return _send_first_access_email(email=email, raw_token=raw_token)


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


_PERMISSION_MODULE_ORDER = ("dashboard", "lancamentos", "investimentos", "relatorios", "contas", "usuarios")


def _empty_permissions_payload() -> list[dict[str, Any]]:
    return [
        {
            "module": module,
            "can_view": False,
            "can_add": False,
            "can_edit": False,
            "can_delete": False,
        }
        for module in _PERMISSION_MODULE_ORDER
    ]


def _full_permissions_payload() -> list[dict[str, Any]]:
    return [
        {
            "module": module,
            "can_view": True,
            "can_add": True,
            "can_edit": True,
            "can_delete": True,
        }
        for module in _PERMISSION_MODULE_ORDER
    ]


def _effective_permissions_for_user(user: dict[str, Any], member: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    global_role = _global_role_from_user(user)
    workspace_role = str((member or {}).get("workspace_role") or user.get("workspace_role") or "").strip().upper()

    if global_role == "SUPER_ADMIN" or workspace_role in {"OWNER", "SUPER_ADMIN"}:
        return _full_permissions_payload()

    base = {row["module"]: dict(row) for row in _empty_permissions_payload()}
    if workspace_role != "GUEST":
        return list(base.values())

    uid = int(user.get("id") or 0)
    workspace_id = int((member or {}).get("workspace_id") or user.get("workspace_id") or 0)
    if uid <= 0 or workspace_id <= 0:
        return list(base.values())

    workspace_user_id = int((member or {}).get("workspace_user_id") or 0)
    if workspace_user_id <= 0:
        workspace_user = permissions_service.get_workspace_user(workspace_id, uid)
        workspace_user_id = int((workspace_user or {}).get("id") or 0)

    if workspace_user_id <= 0:
        return list(base.values())

    rows = permissions_service.list_permissions_by_workspace_user(workspace_user_id)
    for item in rows:
        module = str((item or {}).get("module") or "").strip().lower()
        if module not in base:
            continue
        base[module]["can_view"] = bool((item or {}).get("can_view"))
        base[module]["can_add"] = bool((item or {}).get("can_add"))
        base[module]["can_edit"] = bool((item or {}).get("can_edit"))
        base[module]["can_delete"] = bool((item or {}).get("can_delete"))

    return list(base.values())


def _permission_from_request(method: str, path: str) -> tuple[str, str] | None:
    p = str(path or "").strip().lower().strip("/")
    if not p:
        return None

    if p in {"workspaces", "workspaces/switch"}:
        return None

    if p.startswith("dashboard"):
        module = "dashboard"
    elif p == "kpis":
        module = "dashboard"
    elif p.startswith("transactions") or p.startswith("credit-commitments"):
        module = "lancamentos"
    elif p.startswith("invest"):
        module = "investimentos"
    elif p.startswith("accounts") or p.startswith("categories") or p.startswith("cards") or p.startswith("card-invoices"):
        module = "contas"
    elif p.startswith("import"):
        module = "relatorios"
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
    try:
        token_version = int(payload.get("tv", 0) or 0)
    except Exception:
        token_version = 0
    current_token_version = int(user.get("token_version") or 0)
    if token_version != current_token_version:
        security_monitor.record_event(
            event_type="auth_stale_session",
            status_code=401,
            path=str(request.url.path),
            detail="Stale session token",
            user_id=uid,
            ip=_request_ip(request),
        )
        raise HTTPException(status_code=401, detail="Sessao expirada. Faca login novamente.")

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
    out["permissions"] = _effective_permissions_for_user(out, member=member)

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


def _latest_index_ref_date(index_name: str, user_id: int, workspace_id: int | None = None) -> str | None:
    try:
        if workspace_id is not None:
            set_current_workspace_id(int(workspace_id))
        set_current_user_id(int(user_id))
        rows = invest_index_rates.list_index_rates(index_name=index_name, limit=1, user_id=int(user_id))
        if not rows:
            return None
        return str(rows[0].get("ref_date") or "").strip() or None
    finally:
        clear_tenant_context()


def _sync_scope(user_id: int, workspace_id: int | None = None) -> tuple[str, int]:
    if workspace_id is not None:
        return "workspace", int(workspace_id)
    return "user", int(user_id)


def _has_sync_run_today(
    sync_type: str,
    sync_key: str,
    user_id: int,
    workspace_id: int | None = None,
    ref_date: str | None = None,
) -> bool:
    scope_kind, scope_id = _sync_scope(user_id=user_id, workspace_id=workspace_id)
    target_date = str(ref_date or _date.today().isoformat())
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT 1
            FROM sync_runs
            WHERE scope_kind = ? AND scope_id = ? AND sync_type = ? AND sync_key = ? AND ref_date = ?
            LIMIT 1
            """,
            (scope_kind, scope_id, str(sync_type), str(sync_key), target_date),
        ).fetchone()
    return bool(row)


def _mark_sync_run_today(
    sync_type: str,
    sync_key: str,
    user_id: int,
    workspace_id: int | None = None,
    ref_date: str | None = None,
) -> None:
    scope_kind, scope_id = _sync_scope(user_id=user_id, workspace_id=workspace_id)
    target_date = str(ref_date or _date.today().isoformat())
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO sync_runs(scope_kind, scope_id, sync_type, sync_key, ref_date)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(scope_kind, scope_id, sync_type, sync_key, ref_date) DO NOTHING
            """,
            (scope_kind, scope_id, str(sync_type), str(sync_key), target_date),
        )


def _manual_asset_updates_today(user_id: int, workspace_id: int | None = None, ref_date: str | None = None) -> set[int]:
    target_date = str(ref_date or _date.today().isoformat())
    params: list[object] = [target_date]
    where_scope = "workspace_id = ?" if workspace_id is not None else "user_id = ?"
    params.append(int(workspace_id) if workspace_id is not None else int(user_id))
    with get_conn() as conn:
        rows = conn.execute(
            f"""
            SELECT DISTINCT asset_id
            FROM asset_prices
            WHERE px_date = ?
              AND {where_scope}
              AND LOWER(COALESCE(source, '')) IN ('manual_current_value', 'manual_rentability')
            """,
            tuple(params),
        ).fetchall()
    out: set[int] = set()
    for row in rows:
        try:
            out.add(int(row["asset_id"]))
        except Exception:
            out.add(int(row[0]))
    return out


def _collect_login_fixed_income_context(user_id: int, workspace_id: int | None = None) -> dict[str, Any]:
    try:
        if workspace_id is not None:
            set_current_workspace_id(int(workspace_id))
        set_current_user_id(int(user_id))
        assets = [dict(a) for a in (invest_repo.list_assets(user_id=int(user_id)) or [])]
    finally:
        clear_tenant_context()

    impacted_assets: list[dict[str, Any]] = []
    impacted_indexes: set[str] = set()
    for asset in assets:
        if not invest_rentability._is_fixed_income(asset.get("asset_class")):
            continue
        rent_type = invest_rentability._norm_rentability_type(asset.get("rentability_type"))
        if not invest_rentability._is_auto_rentability_type(rent_type):
            continue
        impacted_assets.append(asset)
        idx_name = invest_rentability._norm_index_name(asset.get("index_name"))
        if not idx_name:
            if rent_type in {"PCT_CDI", "CDI_SPREAD"}:
                idx_name = "CDI"
            elif rent_type in {"PCT_SELIC", "SELIC_SPREAD"}:
                idx_name = "SELIC"
            elif rent_type == "IPCA_SPREAD":
                idx_name = "IPCA"
        if idx_name in invest_index_rates.SUPPORTED_INDEX_NAMES:
            impacted_indexes.add(idx_name)

    ordered_indexes = [idx for idx in invest_index_rates.SUPPORTED_INDEX_NAMES if idx in impacted_indexes]
    return {
        "impacted_asset_count": len(impacted_assets),
        "impacted_index_names": ordered_indexes,
    }


def _sync_indexes_on_login(
    user_id: int,
    workspace_id: int | None = None,
    target_indexes: list[str] | None = None,
) -> dict[str, Any]:
    today = _date.today()
    today_iso = today.isoformat()
    plans: list[tuple[str, str, str]] = []
    target_set = {str(idx or "").strip().upper() for idx in (target_indexes or []) if str(idx or "").strip()}
    status_map: dict[str, str] = {}

    for idx in ("CDI", "SELIC"):
        if _has_sync_run_today("index_rate_sync", idx, user_id=user_id, workspace_id=workspace_id, ref_date=today_iso):
            if idx in target_set:
                status_map[idx] = "up_to_date"
            continue
        latest = _latest_index_ref_date(idx, user_id=user_id, workspace_id=workspace_id)
        if latest:
            start = (_date.fromisoformat(latest) + timedelta(days=1)).isoformat()
        else:
            start = f"{today.year}-01-01"
        if start <= today_iso:
            plans.append((idx, start, today_iso))
        elif idx in target_set:
            status_map[idx] = "up_to_date"

    if today.day >= 12:
        if not _has_sync_run_today("index_rate_sync", "IPCA", user_id=user_id, workspace_id=workspace_id, ref_date=today_iso):
            latest_ipca = _latest_index_ref_date("IPCA", user_id=user_id, workspace_id=workspace_id)
            if latest_ipca:
                start = (_date.fromisoformat(latest_ipca) + timedelta(days=1)).isoformat()
            else:
                start = f"{today.year}-01-01"
            if start <= today_iso:
                plans.append(("IPCA", start, today_iso))
            elif "IPCA" in target_set:
                status_map["IPCA"] = "up_to_date"
        elif "IPCA" in target_set:
            status_map["IPCA"] = "up_to_date"
    elif "IPCA" in target_set:
        status_map["IPCA"] = "pending_release"

    if target_set:
        for idx, _, _ in plans:
            if idx in target_set and idx not in status_map:
                status_map[idx] = "pending_sync"

    for idx, start, end in plans:
        try:
            if workspace_id is not None:
                set_current_workspace_id(int(workspace_id))
            set_current_user_id(int(user_id))
            invest_index_rates.sync_from_bcb(
                index_names=[idx],
                date_from=start,
                date_to=end,
                timeout_s=10.0,
                user_id=int(user_id),
            )
            _mark_sync_run_today("index_rate_sync", idx, user_id=user_id, workspace_id=workspace_id, ref_date=today_iso)
            if idx in target_set:
                status_map[idx] = "updated"
        except Exception:
            if idx in target_set:
                status_map[idx] = "failed"
            logger.exception(
                "Falha ao sincronizar índices no login",
                extra={"user_id": int(user_id), "workspace_id": workspace_id, "index_name": idx},
            )
        finally:
            clear_tenant_context()

    updated = [idx for idx in invest_index_rates.SUPPORTED_INDEX_NAMES if status_map.get(idx) == "updated"]
    up_to_date = [idx for idx in invest_index_rates.SUPPORTED_INDEX_NAMES if status_map.get(idx) == "up_to_date"]
    failed = [idx for idx in invest_index_rates.SUPPORTED_INDEX_NAMES if status_map.get(idx) == "failed"]
    pending = [
        idx
        for idx in invest_index_rates.SUPPORTED_INDEX_NAMES
        if status_map.get(idx) in {"pending_release", "pending_sync"}
    ]
    return {
        "statuses": status_map,
        "updated_indexes": updated,
        "up_to_date_indexes": up_to_date,
        "failed_indexes": failed,
        "pending_indexes": pending,
    }


def _refresh_fixed_income_on_login(user_id: int, workspace_id: int | None = None) -> dict[str, Any]:
    today_iso = _date.today().isoformat()
    manual_asset_ids = sorted(_manual_asset_updates_today(user_id=user_id, workspace_id=workspace_id, ref_date=today_iso))
    try:
        if workspace_id is not None:
            set_current_workspace_id(int(workspace_id))
        set_current_user_id(int(user_id))
        result = invest_rentability.update_fixed_income_assets(
            as_of_date=today_iso,
            user_id=int(user_id),
            only_auto=True,
            exclude_asset_ids=manual_asset_ids,
        )
        return {
            "ok": True,
            "total_assets": int(result.get("total_assets") or 0),
            "updated": int(result.get("updated") or 0),
            "errors": int(result.get("errors") or 0),
            "skipped": int(result.get("skipped") or 0),
        }
    except Exception:
        # Falhas de atualização automática não devem bloquear o login.
        logger.exception(
            "Falha ao atualizar renda fixa no login",
            extra={"user_id": int(user_id), "workspace_id": workspace_id},
        )
        return {
            "ok": False,
            "total_assets": 0,
            "updated": 0,
            "errors": 1,
            "skipped": 0,
        }
    finally:
        clear_tenant_context()


def _format_index_names(names: list[str]) -> str:
    labels = [str(name or "").strip().upper() for name in (names or []) if str(name or "").strip()]
    if not labels:
        return ""
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f"{labels[0]} e {labels[1]}"
    return f"{', '.join(labels[:-1])} e {labels[-1]}"


def _build_login_sync_status(
    impacted: dict[str, Any],
    index_sync: dict[str, Any],
    fixed_income_refresh: dict[str, Any],
) -> dict[str, Any] | None:
    impacted_asset_count = int(impacted.get("impacted_asset_count") or 0)
    impacted_indexes = list(impacted.get("impacted_index_names") or [])
    if impacted_asset_count <= 0:
        return None

    updated_set = set(index_sync.get("updated_indexes") or [])
    up_to_date_set = set(index_sync.get("up_to_date_indexes") or [])
    failed_set = set(index_sync.get("failed_indexes") or [])
    pending_set = set(index_sync.get("pending_indexes") or [])
    updated_indexes = [idx for idx in impacted_indexes if idx in updated_set]
    up_to_date_indexes = [idx for idx in impacted_indexes if idx in up_to_date_set]
    failed_indexes = [idx for idx in impacted_indexes if idx in failed_set]
    pending_indexes = [idx for idx in impacted_indexes if idx in pending_set]
    refresh_ok = bool(fixed_income_refresh.get("ok"))
    fixed_income_asset_count = int(fixed_income_refresh.get("total_assets") or 0)
    fixed_income_updated = int(fixed_income_refresh.get("updated") or 0)
    fixed_income_errors = int(fixed_income_refresh.get("errors") or 0)

    if (
        not impacted_indexes
        and fixed_income_asset_count <= 0
        and fixed_income_errors <= 0
        and refresh_ok
    ):
        return None

    if failed_indexes or not refresh_ok or fixed_income_errors > 0:
        parts: list[str] = []
        if updated_indexes:
            parts.append(f"{_format_index_names(updated_indexes)} atualizados")
        if failed_indexes:
            parts.append(f"{_format_index_names(failed_indexes)} com falha")
        if pending_indexes:
            parts.append(f"{_format_index_names(pending_indexes)} sem nova divulgacao hoje")
        if not refresh_ok or fixed_income_errors > 0:
            parts.append("a atualizacao automatica da renda fixa teve pendencias")
        message = "Sync da renda fixa no login com pendencias."
        if parts:
            message = f"Sync da renda fixa no login com pendencias: {'; '.join(parts)}."
        return {
            "should_notify": True,
            "level": "warning",
            "message": message,
            "impacted_asset_count": impacted_asset_count,
            "impacted_index_names": impacted_indexes,
            "updated_indexes": updated_indexes,
            "up_to_date_indexes": up_to_date_indexes,
            "failed_indexes": failed_indexes,
            "pending_indexes": pending_indexes,
            "fixed_income_asset_count": fixed_income_asset_count,
            "fixed_income_updated": fixed_income_updated,
            "fixed_income_errors": fixed_income_errors,
        }

    parts: list[str] = []
    if updated_indexes:
        parts.append(f"indices atualizados: {_format_index_names(updated_indexes)}")
    if up_to_date_indexes:
        parts.append(f"em dia: {_format_index_names(up_to_date_indexes)}")
    if pending_indexes:
        parts.append(f"sem nova divulgacao hoje: {_format_index_names(pending_indexes)}")
    if fixed_income_asset_count > 0:
        parts.append(f"ativos recalculados: {fixed_income_updated}/{fixed_income_asset_count}")
    message = "Renda fixa conferida no login."
    if parts:
        message = f"Renda fixa conferida no login: {'; '.join(parts)}."
    return {
        "should_notify": True,
        "level": "success",
        "message": message,
        "impacted_asset_count": impacted_asset_count,
        "impacted_index_names": impacted_indexes,
        "updated_indexes": updated_indexes,
        "up_to_date_indexes": up_to_date_indexes,
        "failed_indexes": failed_indexes,
        "pending_indexes": pending_indexes,
        "fixed_income_asset_count": fixed_income_asset_count,
        "fixed_income_updated": fixed_income_updated,
        "fixed_income_errors": fixed_income_errors,
    }


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


@app.get("/admin/runtime-checks")
def admin_runtime_checks(user: dict = Depends(_current_user)) -> dict:
    _require_admin(user)
    brapi_token = invest_quotes._get_brapi_token()
    return {
        "ok": True,
        "checks": {
            "brapi_configured": bool(str(brapi_token or "").strip()),
            "cors_origins_configured": bool(_cors_origins()),
            "database_url_configured": bool(str(os.getenv("DATABASE_URL") or "").strip()),
        },
    }


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

    impacted_sync_context = _collect_login_fixed_income_context(uid, workspace_id=workspace_id)
    index_sync_status = _sync_indexes_on_login(
        uid,
        workspace_id=workspace_id,
        target_indexes=impacted_sync_context.get("impacted_index_names"),
    )
    fixed_income_refresh_status = _refresh_fixed_income_on_login(uid, workspace_id=workspace_id)
    login_sync_status = _build_login_sync_status(
        impacted_sync_context,
        index_sync_status,
        fixed_income_refresh_status,
    )

    token = create_token(
        uid,
        str(user["email"]),
        workspace_id=workspace_id,
        global_role=global_role,
        workspace_role=workspace_role,
        token_version=int(user.get("token_version") or 0),
    )

    out_user = dict(user)
    out_user["global_role"] = global_role
    out_user["role"] = "admin" if global_role == "SUPER_ADMIN" else "user"
    out_user["workspace_id"] = workspace_id
    out_user["workspace_role"] = workspace_role
    out_user["workspace_status"] = str(member.get("workspace_status") or "").strip().lower() if member else None
    out_user["workspace_name"] = member.get("workspace_name") if member else None
    out_user["permissions"] = _effective_permissions_for_user(out_user, member=member)
    return LoginResponse(token=token, user=out_user, login_sync_status=login_sync_status)


@app.post("/auth/forgot-password")
def forgot_password(body: ForgotPasswordRequest, request: Request) -> dict:
    email = (body.email or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="E-mail é obrigatório.")

    raw_token = auth.create_password_reset_request(
        email=email,
        request_ip=_request_ip(request),
        request_user_agent=_request_user_agent(request),
    )
    if raw_token:
        try:
            sent = _send_password_reset_email(email=email, raw_token=raw_token)
            security_monitor.record_event(
                event_type="password_reset_requested",
                status_code=200,
                path=str(request.url.path),
                detail="Password reset email queued" if sent else "Password reset requested without email transport",
                ip=_request_ip(request),
            )
        except Exception as exc:
            logger.exception("Failed to send password reset email: %s", exc)
            security_monitor.record_event(
                event_type="password_reset_email_failed",
                status_code=500,
                path=str(request.url.path),
                detail="Password reset email transport failed",
                ip=_request_ip(request),
            )
    else:
        security_monitor.record_event(
            event_type="password_reset_requested",
            status_code=200,
            path=str(request.url.path),
            detail="Password reset requested with neutral response",
            ip=_request_ip(request),
        )
    return {"ok": True, "message": auth.password_reset_public_message()}


@app.post("/auth/reset-password")
def reset_password(body: ResetPasswordRequest, request: Request) -> dict:
    token = str(body.token or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="Token é obrigatório.")
    try:
        auth.reset_password_with_token(
            token=token,
            new_password=body.new_password,
            request_ip=_request_ip(request),
            request_user_agent=_request_user_agent(request),
        )
    except ValueError as e:
        security_monitor.record_event(
            event_type="password_reset_failed",
            status_code=400,
            path=str(request.url.path),
            detail=str(e),
            ip=_request_ip(request),
        )
        raise HTTPException(status_code=400, detail=str(e))
    security_monitor.record_event(
        event_type="password_reset_completed",
        status_code=200,
        path=str(request.url.path),
        detail="Password reset completed",
        ip=_request_ip(request),
    )
    return {"ok": True, "message": "Sua senha foi alterada com sucesso."}


@app.get("/me")
def me(user: dict = Depends(_current_user)) -> dict:
    return user


@app.put("/me")
def update_me(body: ProfileUpdateRequest, user: dict = Depends(_current_user)) -> dict:
    try:
        updated = auth.update_user_profile(
            user_id=int(user["id"]),
            email=body.email,
            display_name=body.display_name,
            current_password=body.current_password,
            new_password=body.new_password,
            avatar_data=body.avatar_data,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    out = dict(updated)
    out["global_role"] = _global_role_from_user(updated)
    out["role"] = "admin" if out["global_role"] == "SUPER_ADMIN" else "user"
    out["workspace_id"] = user.get("workspace_id")
    out["workspace_role"] = user.get("workspace_role")
    out["workspace_status"] = user.get("workspace_status")
    out["workspace_name"] = user.get("workspace_name")
    out["permissions"] = user.get("permissions", [])
    return out


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


@app.put("/workspaces/current")
def rename_current_workspace(
    body: WorkspaceRenameRequest,
    user: dict = Depends(_current_user),
) -> dict:
    workspace_id = _current_workspace_id_from_user(user)
    if not workspace_id:
        raise HTTPException(status_code=400, detail="Workspace atual inválido.")

    if not (_is_super_admin(user) or str(user.get("workspace_role") or "").strip().upper() == "OWNER"):
        raise HTTPException(status_code=403, detail="Somente OWNER pode renomear o workspace.")

    try:
        updated = auth.update_workspace_name(int(workspace_id), body.workspace_name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not updated:
        raise HTTPException(status_code=404, detail="Workspace não encontrado.")

    item = dict(updated)
    item["workspace_status"] = str(item.get("status") or item.get("workspace_status") or "active").strip().lower()
    return {"ok": True, "workspace": item}


@app.post("/workspaces/switch", response_model=LoginResponse)
def switch_workspace(body: WorkspaceSwitchRequest, user: dict = Depends(_current_user)) -> LoginResponse:
    uid = int(user["id"])
    target_workspace_id = int(body.workspace_id)
    global_role = _global_role_from_user(user)
    member: dict | None = None

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
        token_version=int(user.get("token_version") or 0),
    )
    out_user = dict(user)
    out_user["global_role"] = global_role
    out_user["role"] = "admin" if global_role == "SUPER_ADMIN" else "user"
    out_user["workspace_id"] = target_workspace_id
    out_user["workspace_role"] = workspace_role
    out_user["workspace_status"] = workspace_status
    out_user["workspace_name"] = workspace_name
    out_user["permissions"] = _effective_permissions_for_user(out_user, member=member)
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
    request: Request,
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
    created_user = False
    first_access_email_sent = False
    if not target:
        display_name = (body.display_name or "").strip() or None
        try:
            target = auth.create_user(
                email=email,
                display_name=display_name,
                global_role="USER",
            )
            created_user = True
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        try:
            first_access_email_sent = _issue_first_access_email(email=email, request=request)
        except Exception as exc:
            logger.exception("Failed to send first access email for workspace invite: %s", exc)
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
            "created_user": created_user,
            "first_access_email_sent": first_access_email_sent,
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
        "created_user": created_user,
        "first_access_email_sent": first_access_email_sent,
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
    request: Request,
    user: dict = Depends(_current_user),
) -> dict:
    _require_admin(user)
    owner_email = str(body.owner_email or "").strip().lower()
    workspace_name = str(body.workspace_name or "").strip()
    owner_display_name = (body.owner_display_name or "").strip() or None
    if not owner_email:
        raise HTTPException(status_code=400, detail="E-mail do owner é obrigatório.")
    if not workspace_name:
        raise HTTPException(status_code=400, detail="Nome do workspace é obrigatório.")

    owner = auth.get_user_by_email(owner_email)
    created_user = False
    first_access_email_sent = False
    if not owner:
        try:
            owner = auth.create_user(
                email=owner_email,
                display_name=owner_display_name,
                global_role="USER",
            )
            created_user = True
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        try:
            first_access_email_sent = _issue_first_access_email(email=owner_email, request=request)
        except Exception as exc:
            logger.exception("Failed to send first access email for workspace owner: %s", exc)
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
    return {
        "ok": True,
        "workspace": ws,
        "created_user": created_user,
        "first_access_email_sent": first_access_email_sent,
    }


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
            due_day = int(card_cfg["due_day"])
            cycle_day = int(card_cfg["close_day"]) if card_cfg["close_day"] is not None else max(1, int(card_cfg["due_day"]) - 5)
            if cycle_day < 1 or cycle_day > 31:
                raise HTTPException(status_code=400, detail="Dia de fechamento inválido no cartão.")

            today = _date.today()
            start_y, start_m = int(today.year), int(today.month)
            # Para compromissos em cartao, o fechamento define a primeira fatura.
            # Se o compromisso for criado depois do fechamento, a 1a parcela vai
            # para o proximo ciclo, mesmo que o vencimento do mes atual ainda nao tenha passado.
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
                due_date = _due_date_for_month(yy, mm, due_day)
                # Usa uma compra sintetica no inicio do ciclo para manter o vencimento no mes alvo.
                purchase_date = _due_date_for_month(yy, mm, 1)
                if first_date is None:
                    first_date = due_date
                last_date = due_date
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


@app.get("/dashboard/wealth-monthly")
def dashboard_wealth_monthly(
    date_from: str | None = None,
    date_to: str | None = None,
    account: str | None = None,
    view: str = Query(default="caixa"),
    user: dict = Depends(_current_user),
) -> list[dict]:
    uid = int(user["id"])
    mode = _norm_view(view)
    df = reports.df_transactions(date_to=date_to, user_id=uid, view=mode)
    if account and not df.empty:
        df = df[df["account"] == account]
    out = reports.monthly_wealth_summary(df, date_from=date_from, date_to=date_to)
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
    fair_cfg = _validate_asset_fair_value_fields(
        fair_price=body.fair_price,
        safety_margin_pct=body.safety_margin_pct,
    )
    user_objective = _validate_asset_user_objective(body.user_objective)

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
        fair_price=fair_cfg["fair_price"],
        safety_margin_pct=fair_cfg["safety_margin_pct"],
        user_objective=user_objective,
        last_update=(body.last_update or "").strip() or None,
        user_id=uid,
    )
    manual_updates = _resolve_manual_rentability_updates(
        rentability_type=rent_cfg["rentability_type"],
        rate_value=body.rate_value,
        current_value=body.current_value,
        principal_amount=body.principal_amount,
    )
    if created and manual_updates:
        created_asset = next(
            (
                item
                for item in (invest_repo.list_assets(user_id=uid) or [])
                if (item.get("symbol") or "").strip().upper() == symbol
            ),
            None,
        )
        if not created_asset:
            raise HTTPException(status_code=500, detail="Ativo criado, mas a rentabilidade manual não pôde ser aplicada.")
        invest_repo.update_asset(
            asset_id=int(created_asset["id"]),
            user_id=uid,
            rate_type=manual_updates.get("rate_type"),
            rate_value=manual_updates.get("rate_value"),
            current_value=manual_updates.get("current_value"),
            last_update=manual_updates.get("last_update"),
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
    for text_field in ["issuer", "rate_type", "maturity_date", "rentability_type", "index_name", "last_update", "user_objective"]:
        if text_field in raw_payload:
            if text_field == "user_objective":
                optional_updates[text_field] = _validate_asset_user_objective(raw_payload.get(text_field))
            else:
                optional_updates[text_field] = (raw_payload.get(text_field) or "").strip() or None
    for numeric_field in ["rate_value", "index_pct", "spread_rate", "fixed_rate", "principal_amount", "current_value", "fair_price", "safety_margin_pct"]:
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
    fair_cfg = _validate_asset_fair_value_fields(
        fair_price=optional_updates.get("fair_price", asset.get("fair_price")),
        safety_margin_pct=optional_updates.get("safety_margin_pct", asset.get("safety_margin_pct")),
    )
    optional_updates["fair_price"] = fair_cfg["fair_price"]
    optional_updates["safety_margin_pct"] = fair_cfg["safety_margin_pct"]
    if "user_objective" not in optional_updates and "user_objective" in asset:
        optional_updates["user_objective"] = _validate_asset_user_objective(asset.get("user_objective"))
    optional_updates.update(
        _resolve_manual_rentability_updates(
            rentability_type=optional_updates.get("rentability_type", asset.get("rentability_type")),
            rate_value=optional_updates.get("rate_value", asset.get("rate_value")),
            current_value=optional_updates.get("current_value"),
            principal_amount=optional_updates.get("principal_amount"),
            existing_rate_type=asset.get("rate_type"),
            existing_current_value=asset.get("current_value"),
            existing_principal_amount=asset.get("principal_amount"),
        )
    )

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


@app.put("/invest/assets/{asset_id}/fair-value")
def invest_update_asset_fair_value(
    asset_id: int,
    body: AssetFairValueUpdateRequest,
    user: dict = Depends(_current_user),
) -> dict:
    uid = int(user["id"])
    asset = invest_repo.get_asset_by_id(asset_id, user_id=uid)
    if not asset:
        raise HTTPException(status_code=404, detail="Ativo não encontrado")

    fair_cfg = _validate_asset_fair_value_fields(
        fair_price=body.fair_price,
        safety_margin_pct=body.safety_margin_pct,
    )
    user_objective = _validate_asset_user_objective(body.user_objective)

    invest_repo.update_asset_fair_value(
        asset_id=asset_id,
        fair_price=None if fair_cfg["fair_price"] is None else float(fair_cfg["fair_price"]),
        safety_margin_pct=None if fair_cfg["safety_margin_pct"] is None else float(fair_cfg["safety_margin_pct"]),
        user_objective=user_objective,
        user_id=uid,
    )
    return {"ok": True}


@app.post("/invest/assets/{asset_id}/valuation-report")
async def invest_upload_asset_valuation_report(
    asset_id: int,
    file: UploadFile = File(...),
    user: dict = Depends(_current_user),
) -> dict:
    uid = int(user["id"])
    asset = invest_repo.get_asset_by_id(asset_id, user_id=uid)
    if not asset:
        raise HTTPException(status_code=404, detail="Ativo não encontrado")
    if asset.get("fair_price") in (None, ""):
        raise HTTPException(status_code=400, detail="Configure o preço justo antes de anexar o PDF de avaliação.")

    file_name = str(file.filename or "").strip()
    content_type = str(file.content_type or "").strip().lower()
    if not file_name.lower().endswith(".pdf") and content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Envie um arquivo PDF válido.")

    file_data = await file.read()
    if not file_data:
        raise HTTPException(status_code=400, detail="O arquivo enviado está vazio.")
    if len(file_data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="O PDF deve ter no máximo 10 MB.")

    safe_file_name = _sanitize_download_filename(file_name, fallback=f"avaliacao-{asset.get('symbol') or asset_id}.pdf")
    invest_repo.upsert_asset_valuation_report(
        asset_id=asset_id,
        file_name=safe_file_name,
        content_type="application/pdf",
        file_data=file_data,
        user_id=uid,
    )
    report = invest_repo.get_asset_valuation_report(asset_id, user_id=uid) or {}
    return {
        "ok": True,
        "file_name": report.get("file_name") or safe_file_name,
        "uploaded_at": report.get("uploaded_at"),
    }


@app.get("/invest/assets/{asset_id}/valuation-report")
def invest_download_asset_valuation_report(
    asset_id: int,
    user: dict = Depends(_current_user),
) -> Response:
    uid = int(user["id"])
    asset = invest_repo.get_asset_by_id(asset_id, user_id=uid)
    if not asset:
        raise HTTPException(status_code=404, detail="Ativo não encontrado")

    report = invest_repo.get_asset_valuation_report(asset_id, user_id=uid)
    if not report:
        raise HTTPException(status_code=404, detail="Nenhum PDF de avaliação foi anexado a este ativo.")

    file_name = _sanitize_download_filename(
        str(report.get("file_name") or ""),
        fallback=f"avaliacao-{asset.get('symbol') or asset_id}.pdf",
    )
    return Response(
        content=report.get("file_data") or b"",
        media_type=str(report.get("content_type") or "application/pdf"),
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


@app.post("/invest/assets/{asset_id}/manual-update")
def invest_manual_update_asset_value(
    asset_id: int,
    body: ManualAssetValueUpdateRequest,
    user: dict = Depends(_current_user),
) -> dict:
    uid = int(user["id"])
    asset = invest_repo.get_asset_by_id(asset_id, user_id=uid)
    if not asset:
        raise HTTPException(status_code=404, detail="Ativo não encontrado")
    if not _is_fixed_income_asset(asset):
        raise HTTPException(status_code=400, detail="Atualização manual está disponível apenas para renda fixa/fundos/tesouro/COE.")
    is_manual_asset = _norm_rentability_type(asset.get("rentability_type")) == "MANUAL"

    mode = (body.mode or "").strip().lower()
    if mode == "rentability":
        if not is_manual_asset:
            raise HTTPException(status_code=400, detail="Ativos com rentabilidade automática aceitam apenas ajuste por valor atual.")
        updates = _resolve_manual_rentability_updates(
            rentability_type="MANUAL",
            rate_value=body.value,
            current_value=None,
            principal_amount=None,
            existing_rate_type=asset.get("rate_type"),
            existing_current_value=asset.get("current_value"),
            existing_principal_amount=asset.get("principal_amount"),
        )
        if body.ref_date:
            updates["last_update"] = body.ref_date.strip()
    elif mode == "current_value":
        updates = _resolve_manual_current_value_update(
            current_value=body.value,
            ref_date=body.ref_date,
        )
    else:
        raise HTTPException(status_code=400, detail="Modo inválido. Use 'rentability' ou 'current_value'.")

    invest_repo.update_asset(
        asset_id=asset_id,
        symbol=(asset.get("symbol") or "").strip().upper(),
        name=(asset.get("name") or "").strip(),
        asset_class=asset.get("asset_class"),
        sector=(asset.get("sector") or "Não definido").strip() or "Não definido",
        currency=(asset.get("currency") or "BRL").strip().upper(),
        broker_account_id=asset.get("broker_account_id"),
        user_id=uid,
        rate_type=updates.get("rate_type"),
        rate_value=updates.get("rate_value"),
        current_value=updates.get("current_value"),
        last_update=updates.get("last_update"),
    )
    invest_repo.upsert_asset_snapshot(
        asset_id=asset_id,
        px_date=updates.get("last_update") or _date.today().isoformat(),
        price=updates.get("current_value"),
        source="manual_rentability" if mode == "rentability" else "manual_current_value",
        user_id=uid,
    )
    updated = invest_repo.get_asset_by_id(asset_id, user_id=uid)
    return {"ok": True, "asset": _row_to_dict(updated) if updated else None}


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

    accounts = repo.list_accounts(user_id=uid) or []
    account_ids = {int(a["id"]) for a in accounts if a["id"] is not None}
    credit_account_id = int(body.credit_account_id) if body.credit_account_id is not None else 0
    if credit_account_id and credit_account_id not in account_ids:
        raise HTTPException(status_code=400, detail="Conta de crédito inválida.")

    target_account_id = credit_account_id or int(asset["broker_account_id"] or 0)
    note = (body.note or "").strip() or None
    invest_repo.insert_income(
        asset_id=int(body.asset_id),
        date=body.date,
        type_=body.type,
        amount=float(body.amount),
        credit_account_id=target_account_id or None,
        note=note,
        user_id=uid,
    )

    if target_account_id:
        cat_id = repo.ensure_category("Investimentos", "Receita", user_id=uid)
        desc = f"PROVENTO {asset['symbol']} ({body.type})"
        repo.create_transaction(
            date=body.date,
            description=desc,
            amount=float(body.amount),
            category_id=int(cat_id),
            account_id=int(target_account_id),
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
    ok, msg = invest_repo.delete_income_with_cash_reversal(int(income_id), user_id=uid)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True, "message": msg}


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
    workspace_id = _current_workspace_id_from_user(user)
    now_tz = ZoneInfo(QUOTE_JOB_TIMEZONE)
    assets = invest_repo.list_assets(user_id=uid) or []
    include_groups = {
        str(g or "").strip()
        for g in (body.include_groups or [])
        if str(g or "").strip()
    }
    if include_groups:
        assets = [a for a in assets if _quote_group_for_asset(dict(a)) in include_groups]
    if not assets:
        if workspace_id:
            stamp = datetime.now(now_tz).isoformat()
            invest_repo.upsert_quote_job_status(
                workspace_id=int(workspace_id),
                last_started_at=stamp,
                last_finished_at=stamp,
                last_status="skipped",
                last_reason="no_assets",
                last_saved_total=0,
                last_total=0,
                last_error_total=0,
                last_run_scope="manual",
            )
        return {"ok": True, "saved": 0, "total": 0, "report": []}
    started_at = datetime.now(now_tz).isoformat()
    report = invest_quotes.update_all_prices(
        assets=[dict(a) for a in assets],
        timeout_s=body.timeout_s,
        max_workers=body.max_workers,
    )
    saved = 0
    error_total = 0
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
        else:
            error_total += 1
    if workspace_id:
        invest_repo.upsert_quote_job_status(
            workspace_id=int(workspace_id),
            last_started_at=started_at,
            last_finished_at=datetime.now(now_tz).isoformat(),
            last_status="success" if error_total == 0 else "warning",
            last_reason=None,
            last_saved_total=saved,
            last_total=len(report),
            last_error_total=error_total,
            last_run_scope="manual",
        )
    return {"ok": True, "saved": saved, "total": len(report), "report": report}


@app.get("/invest/prices/job-status")
def invest_get_quote_job_status(user: dict = Depends(_current_user)) -> dict:
    workspace_id = _current_workspace_id_from_user(user)
    base = _quote_job_schedule_context()
    if not workspace_id:
        return base
    status = invest_repo.get_quote_job_status(int(workspace_id)) or {}
    return {
        **base,
        **status,
    }


@app.middleware("http")
async def tenant_cleanup_middleware(request, call_next):
    # Defensive cleanup in case lower layers set tenant context.
    try:
        response = await call_next(request)
        return response
    finally:
        clear_tenant_context()
