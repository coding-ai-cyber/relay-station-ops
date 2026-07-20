import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ServerBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    supplier_id: uuid.UUID | None = None
    purchase_id: uuid.UUID | None = None
    login_host: str | None = Field(default=None, max_length=200)
    ssh_username: str | None = Field(default=None, max_length=100)
    console_url: str | None = None
    cpu: str | None = Field(default=None, max_length=100)
    memory: str | None = Field(default=None, max_length=100)
    disk: str | None = Field(default=None, max_length=100)
    bandwidth: str | None = Field(default=None, max_length=100)
    region: str | None = Field(default=None, max_length=100)
    monthly_cost: Decimal | None = None
    expired_at: datetime | None = None
    usage: str | None = Field(default=None, max_length=100)
    status: str = Field(default="running", max_length=50)
    include_real_cost: bool = False
    remark: str | None = None


class ServerCreate(ServerBase):
    ssh_secret: str | None = None


class ServerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    supplier_id: uuid.UUID | None = None
    purchase_id: uuid.UUID | None = None
    login_host: str | None = Field(default=None, max_length=200)
    ssh_username: str | None = Field(default=None, max_length=100)
    ssh_secret: str | None = None
    console_url: str | None = None
    cpu: str | None = Field(default=None, max_length=100)
    memory: str | None = Field(default=None, max_length=100)
    disk: str | None = Field(default=None, max_length=100)
    bandwidth: str | None = Field(default=None, max_length=100)
    region: str | None = Field(default=None, max_length=100)
    monthly_cost: Decimal | None = None
    expired_at: datetime | None = None
    usage: str | None = Field(default=None, max_length=100)
    status: str | None = Field(default=None, max_length=50)
    include_real_cost: bool | None = None
    remark: str | None = None


class ServerRead(ServerBase):
    id: uuid.UUID
    has_ssh_secret: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ServerRenewRequest(BaseModel):
    amount: Decimal = Decimal("0")
    currency: str = Field(default="USD", max_length=20)
    payment_method: str | None = Field(default=None, max_length=100)
    purchased_at: datetime | date
    new_expired_at: datetime
    include_real_cost: bool = True
    cost_status: str = Field(default="valid", max_length=50)
    remark: str | None = None


class ServerSecretRead(BaseModel):
    id: uuid.UUID
    login_host: str | None
    ssh_username: str | None
    ssh_secret: str | None
