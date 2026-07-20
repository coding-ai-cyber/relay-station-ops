import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ProxyPoolBase(BaseModel):
    supplier_id: uuid.UUID | None = None
    purchase_id: uuid.UUID | None = None
    proxy_type: str = Field(min_length=1, max_length=50)
    region: str | None = Field(default=None, max_length=100)
    quantity_or_traffic: str | None = Field(default=None, max_length=100)
    unit_price: Decimal | None = None
    total_price: Decimal | None = None
    expired_at: datetime | None = None
    success_rate: Decimal | None = None
    latency_ms: int | None = None
    suitable_for_login: bool = False
    suitable_for_api: bool = False
    status: str = Field(default="active", max_length=50)
    continue_purchase: bool = True
    include_real_cost: bool = False
    remark: str | None = None


class ProxyPoolCreate(ProxyPoolBase):
    pass


class ProxyPoolUpdate(BaseModel):
    supplier_id: uuid.UUID | None = None
    purchase_id: uuid.UUID | None = None
    proxy_type: str | None = Field(default=None, min_length=1, max_length=50)
    region: str | None = Field(default=None, max_length=100)
    quantity_or_traffic: str | None = Field(default=None, max_length=100)
    unit_price: Decimal | None = None
    total_price: Decimal | None = None
    expired_at: datetime | None = None
    success_rate: Decimal | None = None
    latency_ms: int | None = None
    suitable_for_login: bool | None = None
    suitable_for_api: bool | None = None
    status: str | None = Field(default=None, max_length=50)
    continue_purchase: bool | None = None
    include_real_cost: bool | None = None
    remark: str | None = None


class ProxyPoolRead(ProxyPoolBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
