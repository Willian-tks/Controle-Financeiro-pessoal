from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


class LoginSyncStatus(BaseModel):
    should_notify: bool = False
    level: str | None = None
    message: str | None = None
    impacted_asset_count: int = 0
    impacted_index_names: list[str] = Field(default_factory=list)
    updated_indexes: list[str] = Field(default_factory=list)
    up_to_date_indexes: list[str] = Field(default_factory=list)
    failed_indexes: list[str] = Field(default_factory=list)
    pending_indexes: list[str] = Field(default_factory=list)
    fixed_income_asset_count: int = 0
    fixed_income_updated: int = 0
    fixed_income_errors: int = 0


class LoginResponse(BaseModel):
    token: str
    user: dict
    login_sync_status: LoginSyncStatus | None = None


class ProfileUpdateRequest(BaseModel):
    display_name: str | None = None
    email: str
    current_password: str | None = None
    new_password: str | None = None
    avatar_data: str | None = None


class WorkspaceSwitchRequest(BaseModel):
    workspace_id: int


class WorkspaceMemberCreateRequest(BaseModel):
    email: str
    role: str = "GUEST"
    display_name: str | None = None


class WorkspacePermissionItemRequest(BaseModel):
    module: str
    can_view: bool = False
    can_add: bool = False
    can_edit: bool = False
    can_delete: bool = False


class WorkspacePermissionsUpdateRequest(BaseModel):
    permissions: list[WorkspacePermissionItemRequest]


class WorkspaceAdminCreateRequest(BaseModel):
    workspace_name: str
    owner_email: str
    owner_display_name: str | None = None


class WorkspaceStatusUpdateRequest(BaseModel):
    status: str


class WorkspaceRenameRequest(BaseModel):
    workspace_name: str


class UserGlobalRoleUpdateRequest(BaseModel):
    global_role: str


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
    due_day: int | None = None
    repeat_months: int | None = None
    future_payment_method: str | None = None


class CommitmentSettleRequest(BaseModel):
    payment_date: str
    account_id: int
    amount: float
    notes: str | None = None


class AccountCreateRequest(BaseModel):
    name: str
    type: str
    currency: str = "BRL"
    show_on_dashboard: bool = False


class AccountUpdateRequest(BaseModel):
    name: str
    type: str
    currency: str = "BRL"
    show_on_dashboard: bool = False


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
    rate_type: str | None = None
    rate_value: float | None = None
    maturity_date: str | None = None
    rentability_type: str | None = None
    index_name: str | None = None
    index_pct: float | None = None
    spread_rate: float | None = None
    fixed_rate: float | None = None
    principal_amount: float | None = None
    current_value: float | None = None
    last_update: str | None = None
    fair_price: float | None = None
    safety_margin_pct: float | None = None
    user_objective: str | None = None


class AssetUpdateRequest(BaseModel):
    symbol: str
    name: str
    asset_class: str
    sector: str | None = None
    currency: str = "BRL"
    broker_account_id: int | None = None
    source_account_id: int | None = None
    issuer: str | None = None
    rate_type: str | None = None
    rate_value: float | None = None
    maturity_date: str | None = None
    rentability_type: str | None = None
    index_name: str | None = None
    index_pct: float | None = None
    spread_rate: float | None = None
    fixed_rate: float | None = None
    principal_amount: float | None = None
    current_value: float | None = None
    last_update: str | None = None
    fair_price: float | None = None
    safety_margin_pct: float | None = None
    user_objective: str | None = None


class AssetFairValueUpdateRequest(BaseModel):
    fair_price: float | None = None
    safety_margin_pct: float | None = None
    user_objective: str | None = None


class ManualAssetValueUpdateRequest(BaseModel):
    mode: str
    value: float
    ref_date: str | None = None


class TradeCreateRequest(BaseModel):
    asset_id: int
    date: str
    side: str
    quantity: float
    price: float
    exchange_rate: float | None = None
    fees: float = 0.0
    taxes: float = 0.0
    note: str | None = None


class IncomeCreateRequest(BaseModel):
    asset_id: int
    date: str
    type: str
    amount: float
    credit_account_id: int | None = None
    note: str | None = None


class PriceUpsertRequest(BaseModel):
    asset_id: int
    date: str
    price: float
    source: str | None = None


class QuoteUpdateAllRequest(BaseModel):
    timeout_s: float | None = None
    max_workers: int | None = None
    include_groups: list[str] | None = None


class IndexRatePointRequest(BaseModel):
    ref_date: str
    value: float
    source: str | None = None


class IndexRatesUpsertRequest(BaseModel):
    index_name: str
    points: list[IndexRatePointRequest]
    source: str | None = None


class IndexRatesSyncRequest(BaseModel):
    index_names: list[str] | None = None
    date_from: str | None = None
    date_to: str | None = None
    timeout_s: float | None = None


class BenchmarkSettingUpsertRequest(BaseModel):
    index_name: str
    is_active: bool = True
    update_at_midday: bool = True
    update_at_close: bool = True
    default_asset_class: str | None = None
    display_name: str | None = None


class BenchmarkSyncRequest(BaseModel):
    date_from: str | None = None
    date_to: str | None = None
    timeout_s: float | None = None


class RentabilityUpdateRequest(BaseModel):
    as_of_date: str | None = None
    only_auto: bool = True
    reset_from_principal: bool = False
    asset_ids: list[int] | None = None


class RentabilityDivergenceRequest(BaseModel):
    as_of_date: str | None = None
    only_auto: bool = True
    threshold_pct: float = 0.0
    limit: int = 200


class CreditCardCreateRequest(BaseModel):
    name: str
    brand: str | None = None
    model: str | None = None
    card_type: str | None = None
    card_account_id: int
    source_account_id: int | None = None
    due_day: int | None = None
    close_day: int | None = None


class CreditCardUpdateRequest(BaseModel):
    name: str
    brand: str | None = None
    model: str | None = None
    card_type: str | None = None
    card_account_id: int
    source_account_id: int | None = None
    due_day: int | None = None
    close_day: int | None = None


class CreditCardPayInvoiceRequest(BaseModel):
    payment_date: str
    source_account_id: int | None = None
