"""Clinic booking endpoints. Advanced retry/idempotency protection follows separately."""
import base64
import json
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.database import get_session
from src.models import Booking, Slot
from src.slots_api import require_api_key

router = APIRouter(dependencies=[Depends(require_api_key)])


class BookingInput(BaseModel):
    slot_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    email: EmailStr

    @field_validator("slot_id", "name", mode="before")
    @classmethod
    def normalize_nonblank(cls, value):
        if isinstance(value, str):
            value = value.strip()
        if not isinstance(value, str) or not value:
            raise ValueError("must not be blank")
        return value

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        if isinstance(value, str):
            return value.strip().lower()
        return value


def booking_json(booking: Booking) -> dict:
    return {
        "id": booking.id,
        "slot_id": booking.slot_id,
        "name": booking.name,
        "email": booking.email,
        "status": booking.status,
        "created_at": booking.created_at.isoformat().replace("+00:00", "Z"),
    }


@router.post("/bookings", status_code=201)
def create_booking(payload: BookingInput, session: Session = Depends(get_session)):
    slot = session.get(Slot, payload.slot_id)
    if slot is None:
        raise HTTPException(status_code=404, detail="slot not found")
    if slot.start <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="slot has already started")

    booking = Booking(
        id=str(uuid4()),
        slot_id=payload.slot_id,
        name=payload.name,
        email=str(payload.email).lower(),
        status="confirmed",
        created_at=datetime.now(timezone.utc),
    )
    session.add(booking)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        # The partial unique index ensures only one confirmed booking per slot,
        # even when two requests arrive simultaneously.
        if session.scalar(select(Booking.id).where(
            Booking.slot_id == payload.slot_id,
            Booking.status == "confirmed",
        )) is not None:
            raise HTTPException(status_code=409, detail="slot already booked")
        raise
    session.refresh(booking)
    return booking_json(booking)


@router.get("/bookings")
def list_bookings(
    email: str = Query(min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
    cursor: str | None = Query(default=None),
    session: Session = Depends(get_session),
):
    email = email.strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="email is required")
    statement = select(Booking).where(Booking.email == email)
    if cursor:
        try:
            data = json.loads(base64.urlsafe_b64decode(
                cursor + "=" * (-len(cursor) % 4)
            ))
            created_at = datetime.fromisoformat(data["t"])
            booking_id = data["id"]
            if not isinstance(booking_id, str) or created_at.tzinfo is None:
                raise ValueError()
        except (ValueError, TypeError, KeyError, UnicodeDecodeError):
            raise HTTPException(status_code=400, detail="invalid cursor")
        statement = statement.where(or_(
            Booking.created_at > created_at,
            and_(Booking.created_at == created_at, Booking.id > booking_id),
        ))
    results = session.scalars(
        statement.order_by(Booking.created_at, Booking.id).limit(limit + 1)
    ).all()
    page = results[:limit]
    next_cursor = None
    if len(results) > limit and page:
        marker = json.dumps({
            "t": page[-1].created_at.isoformat(), "id": page[-1].id
        }, separators=(",", ":")).encode()
        next_cursor = base64.urlsafe_b64encode(marker).decode().rstrip("=")
    return {"bookings": [booking_json(b) for b in page], "next_cursor": next_cursor}


@router.get("/bookings/{booking_id}")
def get_booking(booking_id: str, session: Session = Depends(get_session)):
    booking = session.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(status_code=404, detail="booking not found")
    return booking_json(booking)


@router.delete("/bookings/{booking_id}")
def cancel_booking(booking_id: str, session: Session = Depends(get_session)):
    booking = session.scalar(
        select(Booking).where(Booking.id == booking_id).with_for_update()
    )
    if booking is None:
        raise HTTPException(status_code=404, detail="booking not found")
    if booking.status == "cancelled":
        raise HTTPException(status_code=409, detail="booking already cancelled")
    booking.status = "cancelled"
    session.commit()
    session.refresh(booking)
    return booking_json(booking)
