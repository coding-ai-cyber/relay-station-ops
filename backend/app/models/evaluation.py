import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class EvaluationBatch(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "evaluation_batches"

    batch_no: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id"),
        index=True,
    )
    account_type: Mapped[str] = mapped_column(String(50), index=True)
    purchase_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("purchases.id"),
        index=True,
    )
    purchase_quantity: Mapped[int] = mapped_column(Integer, default=0)
    purchase_total_price: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    test_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    test_finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    initial_pass_count: Mapped[int] = mapped_column(Integer, default=0)
    day7_available_count: Mapped[int] = mapped_column(Integer, default=0)
    day30_available_count: Mapped[int] = mapped_column(Integer, default=0)
    banned_count: Mapped[int] = mapped_column(Integer, default=0)
    refund_count: Mapped[int] = mapped_column(Integer, default=0)
    effective_account_count: Mapped[int] = mapped_column(Integer, default=0)
    nominal_unit_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    real_effective_unit_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 4))
    overall_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    conclusion: Mapped[str | None] = mapped_column(String(50), index=True)
    remark: Mapped[str | None] = mapped_column(Text)

    supplier = relationship("Supplier", back_populates="evaluation_batches")
    purchase = relationship("Purchase", back_populates="evaluation_batches")
    account_evaluations = relationship("AccountEvaluation", back_populates="batch")


class AccountEvaluation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "account_evaluations"

    batch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evaluation_batches.id"),
        index=True,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id"),
        index=True,
    )
    can_login: Mapped[bool | None] = mapped_column(Boolean)
    has_risk_control: Mapped[bool | None] = mapped_column(Boolean)
    target_model_available: Mapped[bool | None] = mapped_column(Boolean)
    need_fixed_proxy: Mapped[bool | None] = mapped_column(Boolean)
    request_success_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    avg_response_quality: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    available_days: Mapped[int | None] = mapped_column(Integer)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_refunded: Mapped[bool] = mapped_column(Boolean, default=False)
    manual_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    conclusion: Mapped[str | None] = mapped_column(String(100), index=True)
    remark: Mapped[str | None] = mapped_column(Text)

    batch = relationship("EvaluationBatch", back_populates="account_evaluations")
    account = relationship("Account", back_populates="evaluations")

