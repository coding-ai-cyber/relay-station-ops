import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class AccountItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "account_items"

    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id"),
        index=True,
    )
    purchase_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchases.id"),
        index=True,
    )
    item_no: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    item_index: Mapped[int] = mapped_column(Integer)
    email: Mapped[str | None] = mapped_column(String(200), index=True)
    platform: Mapped[str | None] = mapped_column(String(100), index=True)
    plan_type: Mapped[str | None] = mapped_column(String(50))
    remote_account_id: Mapped[str | None] = mapped_column(String(200), index=True)
    status: Mapped[str] = mapped_column(String(50), default="bound", index=True)
    import_batch_no: Mapped[str | None] = mapped_column(String(100), index=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSONB)
    raw_credentials_encrypted: Mapped[str | None] = mapped_column(Text)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_sub2api_status_code: Mapped[int | None] = mapped_column(Integer)
    last_sub2api_error_code: Mapped[str | None] = mapped_column(String(100))
    last_sub2api_message: Mapped[str | None] = mapped_column(Text)
    first_seen_alive_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_alive_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_abnormal_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    survival_seconds: Mapped[int | None] = mapped_column(Integer)
    remark: Mapped[str | None] = mapped_column(Text)

    account = relationship("Account", back_populates="items")
    purchase = relationship("Purchase")
