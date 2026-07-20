import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class CostItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "cost_items"

    cost_no: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    cost_type: Mapped[str] = mapped_column(String(50), index=True)
    source_type: Mapped[str] = mapped_column(String(50), default="manual", index=True)
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id"),
        index=True,
    )
    product_name: Mapped[str | None] = mapped_column(String(200))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    currency: Mapped[str] = mapped_column(String(20), default="USD")
    cost_date: Mapped[date] = mapped_column(Date, index=True)
    include_all_cost: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    include_real_cost: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    one_time: Mapped[bool] = mapped_column(Boolean, default=True)
    recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    recurring_period: Mapped[str | None] = mapped_column(String(20))
    period_started_at: Mapped[date | None] = mapped_column(Date)
    period_finished_at: Mapped[date | None] = mapped_column(Date)
    remark: Mapped[str | None] = mapped_column(Text)

    supplier = relationship("Supplier", back_populates="cost_items")
