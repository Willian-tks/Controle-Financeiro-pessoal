from pydantic import BaseModel, Field, field_validator


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


LIST_ALLOWED_STATUSES = {"ativa", "arquivada"}
LIST_ITEM_ALLOWED_UNITS = {"un", "l", "kg"}


def _strip_required_text(value: str, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field_name} é obrigatório")
    return text


class ListSummaryResponse(BaseModel):
    total_items: int = 0
    acquired_items: int = 0
    pending_items: int = 0
    completion_pct: float = 0.0
    estimated_total: float = 0.0


class ListCreateRequest(BaseModel):
    name: str
    type: str
    description: str | None = None
    status: str = "ativa"

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _strip_required_text(value, "Nome da lista")

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        return _strip_required_text(value, "Tipo da lista")

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        status = _strip_required_text(value, "Status da lista").lower()
        if status not in LIST_ALLOWED_STATUSES:
            raise ValueError("Status da lista inválido")
        return status


class ListUpdateRequest(ListCreateRequest):
    pass


class ListItemCreateRequest(BaseModel):
    name: str
    quantity: float
    unit: str = "un"
    suggested_value: float = 0.0
    notes: str | None = None
    sort_order: int | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _strip_required_text(value, "Nome do item")

    @field_validator("quantity")
    @classmethod
    def validate_quantity(cls, value: float) -> float:
        if float(value) <= 0:
            raise ValueError("Quantidade deve ser maior que zero")
        return float(value)

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, value: str) -> str:
        unit = _strip_required_text(value, "Unidade").lower()
        if unit not in LIST_ITEM_ALLOWED_UNITS:
            raise ValueError("Unidade do item inválida")
        return unit

    @field_validator("suggested_value")
    @classmethod
    def validate_suggested_value(cls, value: float) -> float:
        if float(value) < 0:
            raise ValueError("Valor sugerido deve ser maior ou igual a zero")
        return float(value)

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None


class ListItemUpdateRequest(ListItemCreateRequest):
    pass


class ListToggleAcquiredRequest(BaseModel):
    acquired: bool


class ListItemResponse(BaseModel):
    id: int
    workspace_id: int
    list_id: int
    name: str
    quantity: float
    unit: str = "un"
    suggested_value: float
    total_value: float
    acquired: bool
    completion_date: str | None = None
    notes: str | None = None
    sort_order: int = 0
    created_at: str | None = None
    updated_at: str | None = None


class ListResponse(BaseModel):
    id: int
    workspace_id: int
    name: str
    type: str
    description: str | None = None
    status: str
    created_at: str | None = None
    updated_at: str | None = None
    summary: ListSummaryResponse = Field(default_factory=ListSummaryResponse)


class ListDetailResponse(ListResponse):
    items: list[ListItemResponse] = Field(default_factory=list)
