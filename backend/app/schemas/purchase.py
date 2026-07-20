import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


class PurchaseBase(BaseModel):
    purchase_no: str | None = Field(default=None, min_length=1, max_length=100)
    purchase_type: str = Field(min_length=1, max_length=50)
    supplier_id: uuid.UUID | None = None
    product_name: str = Field(min_length=1, max_length=200)
    product_type: str | None = Field(default=None, max_length=100)
    quantity: Decimal = Decimal("0")
    unit_price: Decimal = Decimal("0")
    total_price: Decimal = Decimal("0")
    currency: str = Field(default="USD", max_length=20)
    payment_method: str | None = Field(default=None, max_length=100)
    purchased_at: date
    purchaser_id: uuid.UUID | None = None
    order_url: str | None = None
    voucher_file_id: uuid.UUID | None = None
    include_all_cost: bool = True
    include_real_cost: bool = False
    cost_status: str = Field(default="testing", max_length=50)
    remark: str | None = None

    @field_validator("purchase_no", mode="before")
    @classmethod
    def blank_purchase_no_as_missing(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class PurchaseCreate(PurchaseBase):
    pass


class PurchaseUpdate(BaseModel):
    purchase_no: str | None = Field(default=None, min_length=1, max_length=100)
    purchase_type: str | None = Field(default=None, min_length=1, max_length=50)
    supplier_id: uuid.UUID | None = None
    product_name: str | None = Field(default=None, min_length=1, max_length=200)
    product_type: str | None = Field(default=None, max_length=100)
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    total_price: Decimal | None = None
    currency: str | None = Field(default=None, max_length=20)
    payment_method: str | None = Field(default=None, max_length=100)
    purchased_at: date | None = None
    purchaser_id: uuid.UUID | None = None
    order_url: str | None = None
    voucher_file_id: uuid.UUID | None = None
    include_all_cost: bool | None = None
    include_real_cost: bool | None = None
    cost_status: str | None = Field(default=None, max_length=50)
    remark: str | None = None


class PurchaseRead(PurchaseBase):
    id: uuid.UUID
    purchase_no: str
    asset_generated: bool = False
    generated_asset_count: int = 0
    bound_account_count: int = 0
    imported_account_count: int = 0
    abnormal_account_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PurchaseAssetGenerationResult(BaseModel):
    purchase_id: uuid.UUID
    purchase_no: str
    purchase_type: str
    created_accounts: int = 0
    created_servers: int = 0
    created_proxy_pools: int = 0
    skipped_reason: str | None = None


class PurchaseAssetGenerationRequest(BaseModel):
    expired_at: datetime | None = None


class PurchaseAccountJsonBindRequest(BaseModel):
    file_id: uuid.UUID | None = None
    payload: dict | list
    overwrite_existing: bool = False
    account_type: str | None = Field(default=None, max_length=50)
    plan_type: str | None = Field(default=None, max_length=50)
    remark: str | None = None


class PurchaseAccountJsonBindItem(BaseModel):
    account_id: uuid.UUID | None = None
    account_no: str | None = None
    email: str | None = None
    status: str
    message: str


class PurchaseAccountJsonBindResult(BaseModel):
    purchase_id: uuid.UUID
    import_batch_no: str
    total_json_accounts: int
    bound_count: int = 0
    skipped_count: int = 0
    failed_count: int = 0
    items: list[PurchaseAccountJsonBindItem] = Field(default_factory=list)
