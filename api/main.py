from __future__ import annotations

import os
import calendar
from typing import Any
from datetime import date as _date

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

import auth
import api.importers as importers
import invest_repo
import invest_reports
import invest_quotes
import repo
import reports
from db import get_conn, init_db
from tenant import clear_current_user_id

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
    IncomeCreateRequest,
    PriceUpsertRequest,
    QuoteUpdateAllRequest,
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


def _auth_payload(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload


def _current_user(payload: dict = Depends(_auth_payload)) -> dict:
    user = auth.get_user_by_id(int(payload["uid"]))
    if not user or not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="Invalid user")
    return user


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
def login(body: LoginRequest) -> LoginResponse:
    user = auth.authenticate_user(body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    token = create_token(int(user["id"]), str(user["email"]))
    return LoginResponse(token=token, user=user)


@app.get("/me")
def me(user: dict = Depends(_current_user)) -> dict:
    return user


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
        due_day = int(body.due_day or 0)
        if due_day < 1 or due_day > 31:
            raise HTTPException(status_code=400, detail="Dia de vencimento deve estar entre 1 e 31.")
        repeat_months = int(body.repeat_months or 1)
        if repeat_months < 1 or repeat_months > 120:
            raise HTTPException(status_code=400, detail="Meses para replicar deve estar entre 1 e 120.")

        today = _date.today()
        start_y, start_m = int(today.year), int(today.month)
        if int(today.day) > int(due_day):
            start_y, start_m = _add_months(start_y, start_m, 1)

        cat_id = int(category_id) if category_id is not None else None
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
                method="Futuro",
                notes=notes,
                user_id=uid,
            )
            created += 1
        return {"ok": True, "mode": "future_schedule", "created": created, "first_date": first_date, "last_date": last_date}

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
        if src_type == dst_type:
            raise HTTPException(
                status_code=400,
                detail="Para Transferência, origem e destino devem ser de tipos diferentes (Banco <-> Corretora)",
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
    else:
        due_day = 1

    try:
        repo.create_credit_card(
            name=name,
            brand=brand,
            model=model,
            card_type=card_type,
            card_account_id=int(body.card_account_id),
            source_account_id=int(body.card_account_id),
            due_day=due_day,
            user_id=uid,
        )
    except Exception as e:
        msg = str(e)
        if "UNIQUE constraint failed" in msg and "credit_cards.user_id" in msg and "credit_cards.name" in msg and "credit_cards.card_type" in msg:
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
    else:
        due_day = 1
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
            user_id=uid,
        )
    except Exception as e:
        msg = str(e)
        if "UNIQUE constraint failed" in msg and "credit_cards.user_id" in msg and "credit_cards.name" in msg and "credit_cards.card_type" in msg:
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
    user: dict = Depends(_current_user),
) -> dict:
    uid = int(user["id"])
    repo.delete_transaction(int(tx_id), user_id=uid)
    return {"ok": True}


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
    }


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

    created = invest_repo.create_asset(
        symbol=symbol,
        name=name,
        asset_class=body.asset_class,
        sector=sector,
        currency=(body.currency or "BRL").strip().upper(),
        broker_account_id=body.broker_account_id,
        source_account_id=body.source_account_id,
        issuer=(body.issuer or "").strip() or None,
        maturity_date=(body.maturity_date or "").strip() or None,
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

    invest_repo.update_asset(
        asset_id=asset_id,
        symbol=(body.symbol or "").strip().upper(),
        name=(body.name or "").strip(),
        asset_class=body.asset_class,
        sector=sector,
        currency=(body.currency or "BRL").strip().upper(),
        broker_account_id=body.broker_account_id,
        user_id=uid,
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
    conn = get_conn()
    try:
        q = """
            SELECT p.id, p.asset_id, p.date, p.price, p.source, a.symbol, a.asset_class
            FROM prices p
            JOIN assets a ON a.id = p.asset_id AND a.user_id = p.user_id
            WHERE p.user_id = ?
        """
        params: list[Any] = [uid]
        if asset_id is not None:
            q += " AND p.asset_id = ?"
            params.append(int(asset_id))
        q += " ORDER BY p.date DESC, p.id DESC LIMIT ?"
        params.append(int(limit))
        rows = conn.execute(q, params).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


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
        clear_current_user_id()
