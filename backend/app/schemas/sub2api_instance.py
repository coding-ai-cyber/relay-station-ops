import uuid
from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class Sub2APIInstanceBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    base_url: HttpUrl
    is_active: bool = True
    adapter: str = Field(default="sub2api", max_length=50)
    remark: str | None = None


class Sub2APIInstanceCreate(Sub2APIInstanceBase):
    admin_key: str = Field(min_length=1)


class Sub2APIInstanceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    base_url: HttpUrl | None = None
    admin_key: str | None = None
    is_active: bool | None = None
    adapter: str | None = Field(default=None, max_length=50)
    remark: str | None = None


class Sub2APIInstanceRead(BaseModel):
    id: uuid.UUID
    name: str
    base_url: str
    is_active: bool
    has_admin_key: bool
    last_probe_at: datetime | None = None
    last_probe_status: str | None = None
    last_probe_message: str | None = None
    detected_accounts_path: str | None = None
    detected_version: str | None = None
    adapter: str
    extra: dict | None = None
    remark: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class Sub2APIProbeResult(BaseModel):
    ok: bool
    status: str
    message: str
    accounts_path: str | None = None
    version: str | None = None
    sample_count: int = 0
