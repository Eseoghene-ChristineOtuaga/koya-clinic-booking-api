"""Patient-facing booking routes.

These intentionally expose only public slot discovery, booking creation,
and reference+email-scoped booking management. Assessment endpoints and
administrative reset remain API-key protected under their original paths.
"""
from fastapi import APIRouter, Depends, HTTPException, Header, Query
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database import get_session
from src.models import Booking
from src.slots_api import list_slots
from src.bookings_api import BookingInput, booking_json, create_booking

router = APIRouter(prefix="/web", tags=["website"], include_in_schema=False)


@router.get("/slots")
def public_slots(provider: str | None = Query(default=None), session: Session = Depends(get_session)):
    return list_slots(provider=provider, session=session)


@router.post("/bookings")
def public_create_booking(
    payload: BookingInput,
    idempotency_key: str | None = Header(default=None),
    session: Session = Depends(get_session),
):
    # Reuse the exact transactional booking, concurrency, idempotency and
    # rolling rate-limit behavior from the protected assessment endpoint.
    return create_booking(payload=payload, idempotency_key=idempotency_key, session=session)


@router.get("/bookings/{booking_id}")
def public_get_booking(
    booking_id: str,
    email: EmailStr = Query(...),
    session: Session = Depends(get_session),
):
    booking = session.scalar(select(Booking).where(
        Booking.id == booking_id,
        Booking.email == str(email).strip().lower(),
    ))
    if booking is None:
        raise HTTPException(status_code=404, detail="booking not found")
    return booking_json(booking)


class CancelRequest(BaseModel):
    email: EmailStr


@router.post("/bookings/{booking_id}/cancel")
def public_cancel_booking(
    booking_id: str,
    payload: CancelRequest,
    session: Session = Depends(get_session),
):
    with session.begin():
        booking = session.scalar(
            select(Booking).where(
                Booking.id == booking_id,
                Booking.email == str(payload.email).strip().lower(),
            ).with_for_update()
        )
        if booking is None:
            raise HTTPException(status_code=404, detail="booking not found")
        if booking.status == "cancelled":
            raise HTTPException(status_code=409, detail="booking already cancelled")
        booking.status = "cancelled"
        session.flush()
        result = booking_json(booking)
    return result
