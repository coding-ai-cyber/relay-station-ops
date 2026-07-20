import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Sub2APIGroupRead(BaseModel):
    id: int
    name: str
    platform: str
    status: str | None = None
    is_exclusive: bool | None = None


class Sub2APIProxyRead(BaseModel):
    id: int
    name: str
    protocol: str | None = None
    host: str | None = None
    port: int | None = None
    username: str | None = None
    status: str | None = None
    latency_ms: int | None = None
    latency_status: str | None = None
    account_count: int | None = None


class Sub2APIImportCreate(BaseModel):
    instance_id: uuid.UUID
    select_all: bool = False
    account_ids: list[uuid.UUID] = Field(default_factory=list, max_length=500)
    purchase_id: uuid.UUID | None = None
    group_ids: list[int] = Field(min_length=1, max_length=100)
    proxy_id: int | None = Field(default=None, ge=1)
    duplicate_policy: Literal["skip", "update"] = "skip"
    remark: str | None = None

    @model_validator(mode="after")
    def validate_account_scope(self) -> "Sub2APIImportCreate":
        scopes = [
            bool(self.select_all),
            bool(self.account_ids),
            self.purchase_id is not None,
        ]
        if sum(scopes) != 1:
            raise ValueError("Select exactly one import scope")
        return self


class Sub2APIImportBatchRead(BaseModel):
    id: uuid.UUID
    batch_no: str
    instance_id: uuid.UUID
    instance_name: str | None = None
    created_by: uuid.UUID | None = None
    retry_of_batch_id: uuid.UUID | None = None
    group_ids: list[int]
    duplicate_policy: str
    status: str
    total_count: int
    success_count: int
    failed_count: int
    skipped_count: int
    started_at: datetime | None = None
    finished_at: datetime | None = None
    remark: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class Sub2APIImportItemRead(BaseModel):
    id: uuid.UUID
    batch_id: uuid.UUID
    account_id: uuid.UUID
    account_no: str | None = None
    account_type: str | None = None
    action: str
    status: str
    remote_account_id: str | None = None
    error_message: str | None = None
    attempted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
