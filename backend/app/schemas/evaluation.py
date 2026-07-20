import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class EvaluationBatchCreate(BaseModel):
    batch_no: str = Field(min_length=1, max_length=100)
    supplier_id: uuid.UUID | None = None
    account_type: str = Field(min_length=1, max_length=50)
    purchase_id: uuid.UUID | None = None
    purchase_quantity: int = 0
    purchase_total_price: Decimal = Decimal("0")
    test_started_at: datetime | None = None
    test_finished_at: datetime | None = None
    remark: str | None = None


class EvaluationBatchUpdate(BaseModel):
    batch_no: str | None = Field(default=None, min_length=1, max_length=100)
    supplier_id: uuid.UUID | None = None
    account_type: str | None = Field(default=None, min_length=1, max_length=50)
    purchase_id: uuid.UUID | None = None
    purchase_quantity: int | None = None
    purchase_total_price: Decimal | None = None
    test_started_at: datetime | None = None
    test_finished_at: datetime | None = None
    initial_pass_count: int | None = None
    day7_available_count: int | None = None
    day30_available_count: int | None = None
    banned_count: int | None = None
    refund_count: int | None = None
    effective_account_count: int | None = None
    overall_score: Decimal | None = None
    conclusion: str | None = Field(default=None, max_length=50)
    remark: str | None = None


class EvaluationBatchRead(EvaluationBatchCreate):
    id: uuid.UUID
    initial_pass_count: int
    day7_available_count: int
    day30_available_count: int
    banned_count: int
    refund_count: int
    effective_account_count: int
    nominal_unit_price: Decimal | None
    real_effective_unit_price: Decimal | None
    overall_score: Decimal | None
    conclusion: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AccountEvaluationCreate(BaseModel):
    account_id: uuid.UUID
    can_login: bool | None = None
    has_risk_control: bool | None = None
    target_model_available: bool | None = None
    need_fixed_proxy: bool | None = None
    request_success_rate: Decimal | None = None
    avg_response_quality: Decimal | None = None
    available_days: int | None = None
    is_banned: bool = False
    is_refunded: bool = False
    manual_score: Decimal | None = None
    conclusion: str | None = Field(default=None, max_length=100)
    remark: str | None = None


class AccountEvaluationUpdate(BaseModel):
    can_login: bool | None = None
    has_risk_control: bool | None = None
    target_model_available: bool | None = None
    need_fixed_proxy: bool | None = None
    request_success_rate: Decimal | None = None
    avg_response_quality: Decimal | None = None
    available_days: int | None = None
    is_banned: bool | None = None
    is_refunded: bool | None = None
    manual_score: Decimal | None = None
    conclusion: str | None = Field(default=None, max_length=100)
    remark: str | None = None


class AccountEvaluationRead(AccountEvaluationCreate):
    id: uuid.UUID
    batch_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

