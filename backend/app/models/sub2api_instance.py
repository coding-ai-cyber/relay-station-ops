from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Sub2APIInstance(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sub2api_instances"

    name: Mapped[str] = mapped_column(String(200), index=True)
    base_url: Mapped[str] = mapped_column(Text)
    admin_key_encrypted: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    last_probe_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_probe_status: Mapped[str | None] = mapped_column(String(50), index=True)
    last_probe_message: Mapped[str | None] = mapped_column(Text)
    detected_accounts_path: Mapped[str | None] = mapped_column(String(200))
    detected_version: Mapped[str | None] = mapped_column(String(100))
    adapter: Mapped[str] = mapped_column(String(50), default="sub2api")
    extra: Mapped[dict | None] = mapped_column(JSONB)
    remark: Mapped[str | None] = mapped_column(Text)
