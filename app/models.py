import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Numeric, Integer, Enum, Index
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # idempotency (optional)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)

    sender: Mapped[str] = mapped_column(String(128))
    receiver: Mapped[str] = mapped_column(String(128))

    amount: Mapped[float] = mapped_column(Numeric(18, 8))  # stored as decimal-like
    source_currency: Mapped[str] = mapped_column(String(8))
    destination_currency: Mapped[str] = mapped_column(String(8))

    status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus), default=PaymentStatus.PENDING)

    fx_rate: Mapped[float | None] = mapped_column(Numeric(18, 10), nullable=True)
    payout_amount: Mapped[float | None] = mapped_column(Numeric(18, 8), nullable=True)

    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)

    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


Index("idx_payments_status_created", Payment.status, Payment.created_at)
