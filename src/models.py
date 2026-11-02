"""Initial PostgreSQL models; migrations follow in the next milestone."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Slot(Base):
    __tablename__ = "slots"

    id: Mapped[str] = mapped_column(String(255), primary_key=True)
    provider: Mapped[str] = mapped_column(String(255), nullable=False)
    start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    slot_id: Mapped[str] = mapped_column(
        String(255), ForeignKey("slots.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    status: Mapped[str] = mapped_column(String(12), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index(
            "uq_one_confirmed_booking_per_slot",
            "slot_id",
            unique=True,
            postgresql_where=text("status = 'confirmed'"),
        ),
        Index("ix_bookings_email_created", "email", "created_at", "id"),
    )
