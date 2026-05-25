import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class OrderStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    processing = "processing"
    delivered = "delivered"
    failed = "failed"
    refunded = "refunded"


class OrderType(str, enum.Enum):
    catalog = "catalog"
    custom = "custom"


# The PG enum types are created by the Alembic migration, so disable
# SQLAlchemy's own CREATE TYPE to avoid a duplicate-type error.
_order_status = SAEnum(
    OrderStatus, name="order_status", create_type=False, native_enum=True
)
_order_type = SAEnum(OrderType, name="order_type", create_type=False, native_enum=True)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id"), nullable=False, index=True
    )
    pack_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("packs.id")
    )
    order_type: Mapped[OrderType] = mapped_column(_order_type, nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        _order_status, nullable=False, server_default=OrderStatus.pending.value, index=True
    )
    amount_pkr: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    paypro_invoice_id: Mapped[str | None] = mapped_column(Text, index=True)
    paypro_invoice_url: Mapped[str | None] = mapped_column(Text)
    custom_spec: Mapped[dict | None] = mapped_column(JSONB)
    delivery_s3_csv: Mapped[str | None] = mapped_column(Text)
    delivery_s3_xlsx: Mapped[str | None] = mapped_column(Text)
    delivery_email_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
