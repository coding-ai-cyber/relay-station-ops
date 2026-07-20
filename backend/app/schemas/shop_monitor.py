import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class ShopProductRead(BaseModel):
    id: uuid.UUID
    external_product_id: str
    goods_type: str
    category_id: str | None = None
    category_name: str | None = None
    standard_category_key: str | None = None
    standard_category_name: str | None = None
    category_duplicate_status: str = "unique"
    name: str
    price: Decimal
    market_price: Decimal | None = None
    stock_count: int
    is_out_of_stock: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ShopMonitorCreate(BaseModel):
    supplier_id: uuid.UUID | None = None
    name: str | None = Field(default=None, max_length=200)
    shop_url: str = Field(min_length=1)
    enabled: bool = True


class ShopMonitorRead(BaseModel):
    id: uuid.UUID
    supplier_id: uuid.UUID | None = None
    name: str
    shop_url: str
    shop_token: str
    platform: str
    enabled: bool
    last_synced_at: datetime | None = None
    last_sync_status: str
    last_sync_message: str | None = None
    products: list[ShopProductRead] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ShopMonitorSyncResult(BaseModel):
    monitor_id: uuid.UUID
    product_count: int
    out_of_stock_count: int
    status: str
    message: str | None = None


class ShopMonitorImportResult(BaseModel):
    created_count: int = 0
    skipped_count: int = 0
