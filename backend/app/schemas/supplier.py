import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class SupplierBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    type: str = Field(min_length=1, max_length=50)
    contact_name: str | None = Field(default=None, max_length=100)
    purchase_url: str | None = None
    login_url: str | None = None
    country_region: str | None = Field(default=None, max_length=100)
    continue_cooperation: bool = True
    monitor_shop: bool = False
    preferred_product_tags: list[str] = Field(default_factory=list, max_length=20)
    status: str = Field(default="normal", max_length=50)
    remark: str | None = None


class SupplierCreate(SupplierBase):
    login_account: str | None = None
    login_secret: str | None = None


class SupplierUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    type: str | None = Field(default=None, min_length=1, max_length=50)
    contact_name: str | None = Field(default=None, max_length=100)
    purchase_url: str | None = None
    login_url: str | None = None
    login_account: str | None = None
    login_secret: str | None = None
    country_region: str | None = Field(default=None, max_length=100)
    continue_cooperation: bool | None = None
    monitor_shop: bool | None = None
    preferred_product_tags: list[str] | None = Field(default=None, max_length=20)
    status: str | None = Field(default=None, max_length=50)
    remark: str | None = None


class SupplierRead(SupplierBase):
    id: uuid.UUID
    has_login_account: bool
    has_login_secret: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SupplierSecretRead(BaseModel):
    id: uuid.UUID
    login_account: str | None
    login_secret: str | None
