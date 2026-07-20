from decimal import Decimal

from sqlalchemy import Boolean, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Supplier(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "suppliers"

    name: Mapped[str] = mapped_column(String(200), index=True)
    type: Mapped[str] = mapped_column(String(50), index=True)
    contact_name: Mapped[str | None] = mapped_column(String(100))
    url: Mapped[str | None] = mapped_column(Text)
    purchase_url: Mapped[str | None] = mapped_column(Text)
    login_url: Mapped[str | None] = mapped_column(Text)
    login_account: Mapped[str | None] = mapped_column(Text)
    login_secret_encrypted: Mapped[str | None] = mapped_column(Text)
    telegram: Mapped[str | None] = mapped_column(String(100))
    wechat: Mapped[str | None] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(200))
    country_region: Mapped[str | None] = mapped_column(String(100))
    continue_cooperation: Mapped[bool] = mapped_column(Boolean, default=True)
    monitor_shop: Mapped[bool] = mapped_column(Boolean, default=False)
    preferred_product_tags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(50), default="normal", index=True)
    manual_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    remark: Mapped[str | None] = mapped_column(Text)

    purchases = relationship("Purchase", back_populates="supplier")
    accounts = relationship("Account", back_populates="supplier")
    servers = relationship("Server", back_populates="supplier")
    proxy_pools = relationship("ProxyPool", back_populates="supplier")
    evaluation_batches = relationship("EvaluationBatch", back_populates="supplier")
    cost_items = relationship("CostItem", back_populates="supplier")
    shop_monitors = relationship("ShopMonitor", back_populates="supplier")
