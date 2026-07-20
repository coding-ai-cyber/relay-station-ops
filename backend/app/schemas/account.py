import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, HttpUrl


class AccountBase(BaseModel):
    account_no: str = Field(min_length=1, max_length=100)
    name: str | None = Field(default=None, max_length=200)
    supplier_id: uuid.UUID | None = None
    purchase_id: uuid.UUID | None = None
    sub2api_instance_id: uuid.UUID | None = None
    account_type: str = Field(min_length=1, max_length=50)
    plan_type: str | None = Field(default=None, max_length=50)
    login_url: str | None = None
    login_account: str | None = None
    authorized_email: str | None = Field(default=None, max_length=200)
    sub2api_account_id: str | None = Field(default=None, max_length=200)
    import_file_id: uuid.UUID | None = None
    import_batch_no: str | None = Field(default=None, max_length=100)
    raw_payload: dict | None = None
    bind_email: str | None = Field(default=None, max_length=200)
    recovery_email: str | None = Field(default=None, max_length=200)
    country_region: str | None = Field(default=None, max_length=100)
    proxy_requirement: str | None = None
    status: str = Field(default="pending_test", max_length=50)
    participate_operation: bool = False
    include_real_cost: bool = False
    cost_unit_price: Decimal | None = None
    available_started_at: datetime | None = None
    expired_at: datetime | None = None
    available_days: int | None = None
    remark: str | None = None


class AccountCreate(AccountBase):
    login_password: str | None = None
    sub2api_key: str | None = None


class AccountUpdate(BaseModel):
    account_no: str | None = Field(default=None, min_length=1, max_length=100)
    name: str | None = Field(default=None, max_length=200)
    supplier_id: uuid.UUID | None = None
    purchase_id: uuid.UUID | None = None
    sub2api_instance_id: uuid.UUID | None = None
    account_type: str | None = Field(default=None, min_length=1, max_length=50)
    plan_type: str | None = Field(default=None, max_length=50)
    login_url: str | None = None
    login_account: str | None = None
    login_password: str | None = None
    authorized_email: str | None = Field(default=None, max_length=200)
    sub2api_account_id: str | None = Field(default=None, max_length=200)
    sub2api_key: str | None = None
    import_file_id: uuid.UUID | None = None
    import_batch_no: str | None = Field(default=None, max_length=100)
    raw_payload: dict | None = None
    bind_email: str | None = Field(default=None, max_length=200)
    recovery_email: str | None = Field(default=None, max_length=200)
    country_region: str | None = Field(default=None, max_length=100)
    proxy_requirement: str | None = None
    status: str | None = Field(default=None, max_length=50)
    participate_operation: bool | None = None
    include_real_cost: bool | None = None
    cost_unit_price: Decimal | None = None
    available_started_at: datetime | None = None
    expired_at: datetime | None = None
    available_days: int | None = None
    first_seen_alive_at: datetime | None = None
    last_seen_alive_at: datetime | None = None
    first_abnormal_at: datetime | None = None
    last_checked_at: datetime | None = None
    last_sub2api_status_code: int | None = None
    last_sub2api_error_code: str | None = None
    last_sub2api_message: str | None = None
    survival_seconds: int | None = None
    remark: str | None = None


class AccountStatusUpdate(BaseModel):
    status: str = Field(min_length=1, max_length=50)
    participate_operation: bool | None = None
    include_real_cost: bool | None = None
    available_started_at: datetime | None = None
    expired_at: datetime | None = None
    available_days: int | None = None
    first_seen_alive_at: datetime | None = None
    last_seen_alive_at: datetime | None = None
    first_abnormal_at: datetime | None = None
    last_checked_at: datetime | None = None
    last_sub2api_status_code: int | None = None
    last_sub2api_error_code: str | None = None
    last_sub2api_message: str | None = None
    survival_seconds: int | None = None
    remark: str | None = None


class AccountRead(AccountBase):
    id: uuid.UUID
    has_login_password: bool
    has_sub2api_key: bool
    has_raw_credentials: bool
    first_seen_alive_at: datetime | None = None
    last_seen_alive_at: datetime | None = None
    first_abnormal_at: datetime | None = None
    last_checked_at: datetime | None = None
    last_sub2api_status_code: int | None = None
    last_sub2api_error_code: str | None = None
    last_sub2api_message: str | None = None
    survival_seconds: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AccountItemRead(BaseModel):
    id: uuid.UUID
    account_id: uuid.UUID
    purchase_id: uuid.UUID | None = None
    item_no: str
    item_index: int
    email: str | None = None
    platform: str | None = None
    plan_type: str | None = None
    remote_account_id: str | None = None
    status: str
    import_batch_no: str | None = None
    raw_payload: dict | None = None
    last_checked_at: datetime | None = None
    last_sub2api_status_code: int | None = None
    last_sub2api_error_code: str | None = None
    last_sub2api_message: str | None = None
    first_seen_alive_at: datetime | None = None
    last_seen_alive_at: datetime | None = None
    first_abnormal_at: datetime | None = None
    survival_seconds: int | None = None
    remark: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AccountSecretRead(BaseModel):
    id: uuid.UUID
    login_account: str | None
    login_password: str | None
    authorized_email: str | None = None
    sub2api_account_id: str | None = None
    sub2api_key: str | None = None


class AccountBulkDeleteRequest(BaseModel):
    account_ids: list[uuid.UUID] = Field(min_length=1, max_length=200)


class AccountBulkDeleteResult(BaseModel):
    deleted_count: int


class Sub2APICheckRequest(BaseModel):
    endpoint_url: HttpUrl
    method: str = Field(default="GET", pattern="^(GET|POST)$")
    auth_header_name: str | None = Field(default=None, max_length=100)
    auth_header_value: str | None = None
    account_ids: list[uuid.UUID] | None = None
    supplier_id: uuid.UUID | None = None
    purchase_id: uuid.UUID | None = None
    account_type: str | None = None
    import_batch_no: str | None = None
    include_only_operation: bool = False
    request_body: dict | None = None
    timeout_seconds: int = Field(default=15, ge=1, le=120)
    remark: str | None = None


class Sub2APIAutoCheckRequest(BaseModel):
    instance_id: uuid.UUID
    account_type: str | None = None
    import_batch_no: str | None = None
    purchase_id: uuid.UUID | None = None
    include_only_operation: bool = False
    timeout_seconds: int = Field(default=15, ge=1, le=120)
    remark: str | None = None


class AccountCheckRecordRead(BaseModel):
    id: uuid.UUID
    batch_id: uuid.UUID | None = None
    account_id: uuid.UUID
    checked_at: datetime
    http_status: int | None = None
    sub2api_status: str | None = None
    is_alive: bool
    error_code: str | None = None
    error_message: str | None = None
    response_ms: int | None = None
    survived_seconds: int | None = None
    raw_response: dict | None = None
    remark: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AccountCheckBatchRead(BaseModel):
    id: uuid.UUID
    batch_no: str
    name: str | None = None
    source: str
    endpoint_url: str | None = None
    method: str
    checked_by: uuid.UUID | None = None
    sub2api_instance_id: uuid.UUID | None = None
    total_count: int
    alive_count: int
    abnormal_count: int
    status_401_count: int
    status_403_count: int
    status_429_count: int
    started_at: datetime | None = None
    finished_at: datetime | None = None
    request_config: dict | None = None
    remark: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
