import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ShopMonitor(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "shop_monitors"
    __table_args__ = (
        UniqueConstraint("platform", "shop_token", name="uq_shop_monitors_platform_token"),
    )

    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200))
    shop_url: Mapped[str] = mapped_column(Text)
    shop_token: Mapped[str] = mapped_column(String(100), index=True)
    platform: Mapped[str] = mapped_column(String(50), default="link_shop", index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_sync_status: Mapped[str] = mapped_column(String(50), default="pending", index=True)
    last_sync_message: Mapped[str | None] = mapped_column(Text)
    raw_shop_payload: Mapped[dict | None] = mapped_column(JSONB)

    supplier = relationship("Supplier", back_populates="shop_monitors")
    products = relationship(
        "ShopProduct",
        back_populates="monitor",
        cascade="all, delete-orphan",
        order_by="ShopProduct.name",
    )


class ShopProduct(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "shop_products"
    __table_args__ = (
        UniqueConstraint("monitor_id", "external_product_id", name="uq_shop_products_monitor_external"),
    )

    monitor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shop_monitors.id", ondelete="CASCADE"),
        index=True,
    )
    external_product_id: Mapped[str] = mapped_column(String(100), index=True)
    goods_type: Mapped[str] = mapped_column(String(50), index=True)
    category_id: Mapped[str | None] = mapped_column(String(100), index=True)
    category_name: Mapped[str | None] = mapped_column(String(200))
    standard_category_key: Mapped[str | None] = mapped_column(String(200), index=True)
    standard_category_name: Mapped[str | None] = mapped_column(String(200), index=True)
    category_duplicate_status: Mapped[str] = mapped_column(String(50), default="unique", index=True)
    name: Mapped[str] = mapped_column(String(500), index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    market_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    stock_count: Mapped[int] = mapped_column(Integer, default=0, index=True)
    is_out_of_stock: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSONB)

    monitor = relationship("ShopMonitor", back_populates="products")
