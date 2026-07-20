import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class OperationsPlatformBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    type: str = Field(min_length=1, max_length=50)
    login_url: str | None = None
    bound_email: str | None = Field(default=None, max_length=200)
    bound_phone: str | None = Field(default=None, max_length=100)
    is_core: bool = False
    has_expiry: bool = False
    expired_at: datetime | None = None
    include_cost: bool = False
    status: str = Field(default="active", max_length=50)
    remark: str | None = None


class OperationsPlatformCreate(OperationsPlatformBase):
    login_account: str | None = None
    login_secret: str | None = None


class OperationsPlatformUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    type: str | None = Field(default=None, min_length=1, max_length=50)
    login_url: str | None = None
    login_account: str | None = None
    login_secret: str | None = None
    bound_email: str | None = Field(default=None, max_length=200)
    bound_phone: str | None = Field(default=None, max_length=100)
    is_core: bool | None = None
    has_expiry: bool | None = None
    expired_at: datetime | None = None
    include_cost: bool | None = None
    status: str | None = Field(default=None, max_length=50)
    remark: str | None = None


class OperationsPlatformRead(OperationsPlatformBase):
    id: uuid.UUID
    has_login_account: bool
    has_login_secret: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OperationsPlatformSecretRead(BaseModel):
    id: uuid.UUID
    login_account: str | None
    login_secret: str | None
