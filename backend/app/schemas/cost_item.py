import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class CostItemCreate(BaseModel):
    cost_no: str | None = Field(default=None, min_length=1, max_length=100)
    cost_type: str = Field(min_length=1, max_length=50)
    source_type: str = Field(default="manual", max_length=50)
    source_id: uuid.UUID | None = None
    supplier_id: uuid.UUID | None = None
    product_name: str | None = Field(default=None, max_length=200)
    amount: Decimal = Decimal("0")
    currency: str = Field(default="USD", max_length=20)
    cost_date: date
    include_all_cost: bool = True
    include_real_cost: bool = False
    one_time: bool = True
    recurring: bool = False
    recurring_period: str | None = Field(default=None, max_length=20)
    period_started_at: date | None = None
    period_finished_at: date | None = None
    remark: str | None = None

    @field_validator("cost_no", mode="before")
    @classmethod
    def blank_cost_no_as_missing(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class CostItemUpdate(BaseModel):
    cost_no: str | None = Field(default=None, min_length=1, max_length=100)
    cost_type: str | None = Field(default=None, min_length=1, max_length=50)
    supplier_id: uuid.UUID | None = None
    product_name: str | None = Field(default=None, max_length=200)
    amount: Decimal | None = None
    currency: str | None = Field(default=None, max_length=20)
    cost_date: date | None = None
    include_all_cost: bool | None = None
    include_real_cost: bool | None = None
    one_time: bool | None = None
    recurring: bool | None = None
    recurring_period: str | None = Field(default=None, max_length=20)
    period_started_at: date | None = None
    period_finished_at: date | None = None
    remark: str | None = None


class CostItemRead(CostItemCreate):
    id: uuid.UUID
    cost_no: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
