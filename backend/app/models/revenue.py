from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Revenue(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "revenues"

    revenue_no: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(50), index=True)
    customer: Mapped[str | None] = mapped_column(String(200), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    currency: Mapped[str] = mapped_column(String(20), default="USD")
    payment_method: Mapped[str | None] = mapped_column(String(100))
    revenue_date: Mapped[date] = mapped_column(Date, index=True)
    related_order_no: Mapped[str | None] = mapped_column(String(100), index=True)
    received: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    remark: Mapped[str | None] = mapped_column(Text)

