import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Server(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "servers"

    name: Mapped[str] = mapped_column(String(200), index=True)
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
    login_host: Mapped[str | None] = mapped_column(String(200))
    ssh_username: Mapped[str | None] = mapped_column(String(100))
    ssh_secret_encrypted: Mapped[str | None] = mapped_column(Text)
    console_url: Mapped[str | None] = mapped_column(Text)
    cpu: Mapped[str | None] = mapped_column(String(100))
    memory: Mapped[str | None] = mapped_column(String(100))
    disk: Mapped[str | None] = mapped_column(String(100))
    bandwidth: Mapped[str | None] = mapped_column(String(100))
    region: Mapped[str | None] = mapped_column(String(100))
    monthly_cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    usage: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(50), default="running", index=True)
    include_real_cost: Mapped[bool] = mapped_column(Boolean, default=False)
    remark: Mapped[str | None] = mapped_column(Text)

    supplier = relationship("Supplier", back_populates="servers")
    purchase = relationship("Purchase", back_populates="servers")

