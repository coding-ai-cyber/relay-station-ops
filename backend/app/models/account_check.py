import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class AccountCheckBatch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "account_check_batches"

    batch_no: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(200))
    source: Mapped[str] = mapped_column(String(50), default="sub2api", index=True)
    endpoint_url: Mapped[str | None] = mapped_column(Text)
    method: Mapped[str] = mapped_column(String(10), default="GET")
    checked_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        index=True,
    )
    sub2api_instance_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sub2api_instances.id"),
        index=True,
    )
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    alive_count: Mapped[int] = mapped_column(Integer, default=0)
    abnormal_count: Mapped[int] = mapped_column(Integer, default=0)
    status_401_count: Mapped[int] = mapped_column(Integer, default=0)
    status_403_count: Mapped[int] = mapped_column(Integer, default=0)
    status_429_count: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    request_config: Mapped[dict | None] = mapped_column(JSONB)
    remark: Mapped[str | None] = mapped_column(Text)

    records = relationship("AccountCheckRecord", back_populates="batch")


class AccountCheckRecord(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "account_check_records"

    batch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("account_check_batches.id"),
        index=True,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id"),
        index=True,
    )
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    http_status: Mapped[int | None] = mapped_column(Integer, index=True)
    sub2api_status: Mapped[str | None] = mapped_column(String(100), index=True)
    is_alive: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    error_code: Mapped[str | None] = mapped_column(String(100), index=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    response_ms: Mapped[int | None] = mapped_column(Integer)
    survived_seconds: Mapped[int | None] = mapped_column(Integer)
    raw_response: Mapped[dict | None] = mapped_column(JSONB)
    remark: Mapped[str | None] = mapped_column(Text)

    batch = relationship("AccountCheckBatch", back_populates="records")
    account = relationship("Account", back_populates="check_records")
