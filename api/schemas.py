from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user: dict


class TransactionCreateRequest(BaseModel):
    date: str
    description: str
    amount: float
    account_id: int
    category_id: int | None = None
    kind: str | None = None
    source_account_id: int | None = None
    card_id: int | None = None
    method: str | None = None
    notes: str | None = None


class AccountCreateRequest(BaseModel):
    name: str
    type: str


class AccountUpdateRequest(BaseModel):
    name: str
    type: str


class CategoryCreateRequest(BaseModel):
    name: str
    kind: str


class CategoryUpdateRequest(BaseModel):
    name: str
    kind: str


class AssetCreateRequest(BaseModel):
    symbol: str
    name: str
    asset_class: str
    sector: str | None = None
    currency: str = "BRL"
    broker_account_id: int | None = None
    source_account_id: int | None = None
    issuer: str | None = None
    maturity_date: str | None = None


class AssetUpdateRequest(BaseModel):
    symbol: str
    name: str
    asset_class: str
    sector: str | None = None
    currency: str = "BRL"
    broker_account_id: int | None = None


class TradeCreateRequest(BaseModel):
    asset_id: int
    date: str
    side: str
    quantity: float
    price: float
    fees: float = 0.0
    taxes: float = 0.0
    note: str | None = None


class IncomeCreateRequest(BaseModel):
    asset_id: int
    date: str
    type: str
    amount: float
    note: str | None = None


class PriceUpsertRequest(BaseModel):
    asset_id: int
    date: str
    price: float
    source: str | None = None


class QuoteUpdateAllRequest(BaseModel):
    timeout_s: float | None = None
    max_workers: int | None = None


class CreditCardCreateRequest(BaseModel):
    name: str
    brand: str | None = None
    model: str | None = None
    card_type: str | None = None
    card_account_id: int
    source_account_id: int | None = None
    due_day: int | None = None


class CreditCardUpdateRequest(BaseModel):
    name: str
    brand: str | None = None
    model: str | None = None
    card_type: str | None = None
    card_account_id: int
    source_account_id: int | None = None
    due_day: int | None = None


class CreditCardPayInvoiceRequest(BaseModel):
    payment_date: str
