import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ProxyPool(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "proxy_pools"

    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id"),
        index=True,
    )
    purchase_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchases.id"),
        index=True,
    )
    proxy_type: Mapped[str] = mapped_column(String(50), index=True)
    region: Mapped[str | None] = mapped_column(String(100))
    quantity_or_traffic: Mapped[str | None] = mapped_column(String(100))
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    total_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    success_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    suitable_for_login: Mapped[bool] = mapped_column(Boolean, default=False)
    suitable_for_api: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(50), default="active", index=True)
    continue_purchase: Mapped[bool] = mapped_column(Boolean, default=True)
    include_real_cost: Mapped[bool] = mapped_column(Boolean, default=False)
    remark: Mapped[str | None] = mapped_column(Text)

    supplier = relationship("Supplier", back_populates="proxy_pools")
    purchase = relationship("Purchase", back_populates="proxy_pools")

