import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class RevenueCreate(BaseModel):
    revenue_no: str | None = Field(default=None, max_length=100)
    source: str = Field(min_length=1, max_length=50)
    customer: str | None = Field(default=None, max_length=200)
    amount: Decimal = Decimal("0")
    currency: str = Field(default="USD", max_length=20)
    payment_method: str | None = Field(default=None, max_length=100)
    revenue_date: date
    related_order_no: str | None = Field(default=None, max_length=100)
    received: bool = True
    remark: str | None = None

    @field_validator("revenue_no", mode="before")
    @classmethod
    def blank_revenue_no_to_none(cls, value: str | None) -> str | None:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class RevenueUpdate(BaseModel):
    revenue_no: str | None = Field(default=None, min_length=1, max_length=100)
    source: str | None = Field(default=None, min_length=1, max_length=50)
    customer: str | None = Field(default=None, max_length=200)
    amount: Decimal | None = None
    currency: str | None = Field(default=None, max_length=20)
    payment_method: str | None = Field(default=None, max_length=100)
    revenue_date: date | None = None
    related_order_no: str | None = Field(default=None, max_length=100)
    received: bool | None = None
    remark: str | None = None


class RevenueRead(RevenueCreate):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class Sub2APIRevenueSyncResult(BaseModel):
    instance_id: uuid.UUID | None = None
    instance_name: str | None = None
    created_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    status: str
    message: str | None = None
