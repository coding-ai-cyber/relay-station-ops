import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Account(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "accounts"

    account_no: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str | None] = mapped_column(String(200))
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
    sub2api_instance_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sub2api_instances.id"),
        index=True,
    )
    account_type: Mapped[str] = mapped_column(String(50), index=True)
    plan_type: Mapped[str | None] = mapped_column(String(50))
    login_url: Mapped[str | None] = mapped_column(Text)
    login_account: Mapped[str | None] = mapped_column(Text)
    login_password_encrypted: Mapped[str | None] = mapped_column(Text)
    authorized_email: Mapped[str | None] = mapped_column(String(200))
    sub2api_account_id: Mapped[str | None] = mapped_column(String(200), index=True)
    sub2api_key_encrypted: Mapped[str | None] = mapped_column(Text)
    import_file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("files.id"),
        index=True,
    )
    import_batch_no: Mapped[str | None] = mapped_column(String(100), index=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSONB)
    raw_credentials_encrypted: Mapped[str | None] = mapped_column(Text)
    bind_email: Mapped[str | None] = mapped_column(String(200))
    recovery_email: Mapped[str | None] = mapped_column(String(200))
    country_region: Mapped[str | None] = mapped_column(String(100))
    proxy_requirement: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), default="pending_test", index=True)
    participate_operation: Mapped[bool] = mapped_column(Boolean, default=False)
    include_real_cost: Mapped[bool] = mapped_column(Boolean, default=False)
    cost_unit_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    available_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    available_days: Mapped[int | None] = mapped_column(Integer)
    first_seen_alive_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_alive_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    first_abnormal_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_sub2api_status_code: Mapped[int | None] = mapped_column(Integer)
    last_sub2api_error_code: Mapped[str | None] = mapped_column(String(100))
    last_sub2api_message: Mapped[str | None] = mapped_column(Text)
    survival_seconds: Mapped[int | None] = mapped_column(Integer)
    remark: Mapped[str | None] = mapped_column(Text)

    supplier = relationship("Supplier", back_populates="accounts")
    purchase = relationship("Purchase", back_populates="accounts")
    sub2api_instance = relationship("Sub2APIInstance")
    items = relationship("AccountItem", back_populates="account", cascade="all, delete-orphan")
    evaluations = relationship("AccountEvaluation", back_populates="account")
    import_file = relationship("File")
    check_records = relationship("AccountCheckRecord", back_populates="account")

