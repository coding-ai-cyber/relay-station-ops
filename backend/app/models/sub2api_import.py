import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Sub2APIImportBatch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sub2api_import_batches"

    batch_no: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    instance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sub2api_instances.id"),
        index=True,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        index=True,
    )
    retry_of_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sub2api_import_batches.id"),
        index=True,
        unique=True,
    )
    group_ids: Mapped[list[int]] = mapped_column(JSONB)
    duplicate_policy: Mapped[str] = mapped_column(String(20), default="skip")
    status: Mapped[str] = mapped_column(String(20), default="running", index=True)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    success_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    remark: Mapped[str | None] = mapped_column(Text)

    items = relationship(
        "Sub2APIImportItem",
        back_populates="batch",
        cascade="all, delete-orphan",
    )


class Sub2APIImportItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "sub2api_import_items"

    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sub2api_import_batches.id"),
        index=True,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id"),
        index=True,
    )
    action: Mapped[str] = mapped_column(String(20), default="create")
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    remote_account_id: Mapped[str | None] = mapped_column(String(200), index=True)
    error_message: Mapped[str | None] = mapped_column(Text)
    attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    batch = relationship("Sub2APIImportBatch", back_populates="items")
    account = relationship("Account")
