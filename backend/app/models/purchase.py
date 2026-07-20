import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


ABNORMAL_ACCOUNT_STATUSES = {
    "unavailable",
    "risk_control",
    "banned",
    "api_401",
    "api_403",
    "api_429",
    "check_failed",
}


class Purchase(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "purchases"

    purchase_no: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    purchase_type: Mapped[str] = mapped_column(String(50), index=True)
    supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("suppliers.id"),
        index=True,
    )
    product_name: Mapped[str] = mapped_column(String(200))
    product_type: Mapped[str | None] = mapped_column(String(100))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    total_price: Mapped[Decimal] = mapped_column(Numeric(14, 4), default=0)
    currency: Mapped[str] = mapped_column(String(20), default="USD")
    payment_method: Mapped[str | None] = mapped_column(String(100))
    purchased_at: Mapped[date] = mapped_column(Date, index=True)
    purchaser_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
    )
    order_url: Mapped[str | None] = mapped_column(Text)
    voucher_file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("files.id"),
    )
    include_all_cost: Mapped[bool] = mapped_column(Boolean, default=True)
    include_real_cost: Mapped[bool] = mapped_column(Boolean, default=False)
    cost_status: Mapped[str] = mapped_column(String(50), default="testing", index=True)
    remark: Mapped[str | None] = mapped_column(Text)

    supplier = relationship("Supplier", back_populates="purchases")
    purchaser = relationship("User", back_populates="purchased_orders")
    voucher_file = relationship("File", back_populates="purchase_vouchers")
    accounts = relationship("Account", back_populates="purchase")
    servers = relationship("Server", back_populates="purchase")
    proxy_pools = relationship("ProxyPool", back_populates="purchase")
    evaluation_batches = relationship("EvaluationBatch", back_populates="purchase")

    @property
    def generated_asset_count(self) -> int:
        if self.purchase_type == "account":
            return len(self.accounts)
        if self.purchase_type == "server":
            return len(self.servers)
        if self.purchase_type == "proxy":
            return len(self.proxy_pools)
        return 0

    @property
    def asset_generated(self) -> bool:
        return self.generated_asset_count > 0

    @property
    def bound_account_count(self) -> int:
        if self.purchase_type != "account":
            return 0
        return sum(bool(account.raw_credentials_encrypted) for account in self.accounts)

    @property
    def imported_account_count(self) -> int:
        if self.purchase_type != "account":
            return 0
        return sum(bool(account.sub2api_instance_id) for account in self.accounts)

    @property
    def abnormal_account_count(self) -> int:
        if self.purchase_type != "account":
            return 0
        return sum(
            account.first_abnormal_at is not None
            or account.status in ABNORMAL_ACCOUNT_STATUSES
            for account in self.accounts
        )
