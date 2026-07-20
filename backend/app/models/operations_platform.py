from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class OperationsPlatform(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "operations_platforms"

    name: Mapped[str] = mapped_column(String(200), index=True)
    type: Mapped[str] = mapped_column(String(50), index=True)
    login_url: Mapped[str | None] = mapped_column(Text)
    login_account_encrypted: Mapped[str | None] = mapped_column(Text)
    login_secret_encrypted: Mapped[str | None] = mapped_column(Text)
    bound_email: Mapped[str | None] = mapped_column(String(200))
    bound_phone: Mapped[str | None] = mapped_column(String(100))
    is_core: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    has_expiry: Mapped[bool] = mapped_column(Boolean, default=False)
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    include_cost: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(50), default="active", index=True)
    remark: Mapped[str | None] = mapped_column(Text)
