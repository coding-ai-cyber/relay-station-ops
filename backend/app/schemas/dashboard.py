from pydantic import BaseModel


class DashboardOverview(BaseModel):
    revenue: float
    all_cost: float
    real_cost: float
    profit: float
    real_profit: float
    test_loss: float
    available_accounts: int
    unavailable_accounts: int


class ExpiringAssetRow(BaseModel):
    asset_id: str
    asset_type: str
    name: str
    status: str
    expired_at: str
    days_left: int
    include_real_cost: bool


class MonthlyProfitRow(BaseModel):
    month: str
    revenue: float
    all_cost: float
    real_cost: float
    profit: float
    real_profit: float
    test_loss: float


class SupplierRankingRow(BaseModel):
    supplier_id: str | None
    supplier_name: str
    purchase_count: int
    all_cost: float
    real_cost: float
    test_loss: float
    avg_score: float | None


class SupplierMultiplierRow(BaseModel):
    supplier_id: str
    supplier_name: str
    batch_count: int
    purchase_quantity: int
    effective_account_count: int
    effective_rate: float
    avg_score: float
    real_effective_unit_cost: float
    target_margin: float
    base_multiplier: float
    risk_buffer: float
    loss_buffer: float
    score_buffer: float
    recommended_multiplier: float
    suggested_sale_price: float
    stability_level: str
    reason: str


class AccountTypeProfitRow(BaseModel):
    account_type: str
    batch_count: int
    purchase_quantity: int
    effective_account_count: int
    effective_rate: float
    all_cost: float
    effective_cost: float
    test_loss: float
    real_effective_unit_cost: float | None
    avg_score: float | None


class PurchaseBatchProfitRow(BaseModel):
    batch_id: str
    batch_no: str
    supplier_id: str | None
    supplier_name: str | None
    account_type: str
    purchase_quantity: int
    effective_account_count: int
    effective_rate: float
    purchase_total_price: float
    nominal_unit_price: float | None
    real_effective_unit_price: float | None
    test_loss: float
    overall_score: float | None
    conclusion: str | None


class AIPricingRecommendationRow(BaseModel):
    account_type: str
    batch_count: int
    purchase_quantity: int
    effective_account_count: int
    effective_rate: float
    real_effective_unit_cost: float
    target_margin: float
    recommended_multiplier: float
    suggested_sale_price: float
    projected_revenue: float
    projected_profit: float
    projected_margin: float
    risk_level: str
    reason: str
