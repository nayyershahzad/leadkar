import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Quote(Base):
    """A server-issued, locked quote (CLAUDE.md §15.2/§15.8).

    The assistant never originates price or counts — they are computed here and
    an order is created by referencing the quote id. `kind` and `status` are
    plain text guarded by CHECK constraints in the migration.
    """

    __tablename__ = "quotes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)  # catalog | custom
    pack_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("packs.id")
    )
    city: Mapped[str | None] = mapped_column(Text)
    vertical: Mapped[str | None] = mapped_column(Text)
    count_wanted: Mapped[int | None] = mapped_column(Integer)
    guaranteed_min: Mapped[int | None] = mapped_column(Integer)
    likely_low: Mapped[int | None] = mapped_column(Integer)
    likely_high: Mapped[int | None] = mapped_column(Integer)
    price_pkr: Mapped[int] = mapped_column(Integer, nullable=False)
    preview: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="open"
    )  # open | accepted | expired
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class LeadDensityStat(Base):
    """Delivered-count history per city+vertical, used to sharpen estimates."""

    __tablename__ = "lead_density_stats"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    city: Mapped[str] = mapped_column(Text, nullable=False)
    vertical: Mapped[str] = mapped_column(Text, nullable=False)
    samples: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    last_count: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
