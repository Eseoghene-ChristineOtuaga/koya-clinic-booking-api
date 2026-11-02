"""Booking API: transactional rate limiting, idempotency, and concurrency safety."""
import base64
import binascii
import hashlib
import json
import math
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from src.database import get_session
from src.models import Booking, BookingAttempt, IdempotencyKey, RateLimitLock, Slot
from src.slots_api import require_api_key

router = APIRouter(dependencies=[Depends(require_api_key)])
WINDOW_SECONDS = 60
MAX_ATTEMPTS = 5


class BookingInput(BaseModel):
    slot_id: str = Field(min_length=1, max_length=255)
    name: str = Field(min_length=1, max_length=255)
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


def failure(status: int, message: str, headers: dict | None = None):
    return JSONResponse(status_code=status, content={"error": message}, headers=headers)


def store_idempotent_response(body: dict, headers: dict) -> dict:
    """Persist retry-relevant headers alongside the body, never in the public JSON."""
    if not headers:
        return body  # Compatible with existing stored responses.
    return {"__koya_response_v1__": {"body": body, "headers": headers}}


def replay_idempotent_response(status: int, saved: dict) -> JSONResponse:
    """Restore the original status, response body, and Retry-After header."""
    if isinstance(saved, dict) and set(saved) == {"__koya_response_v1__"}:
        envelope = saved["__koya_response_v1__"]
        if isinstance(envelope, dict) and "body" in envelope and "headers" in envelope:
            return JSONResponse(status_code=status, content=envelope["body"], headers=envelope["headers"])
    return JSONResponse(status_code=status, content=saved)


@router.post("/bookings")
def create_booking(
    payload: BookingInput,
    idempotency_key: str | None = Header(default=None),
    session: Session = Depends(get_session),
):
    if idempotency_key is not None and (not idempotency_key or len(idempotency_key) > 255):
        return failure(400, "invalid idempotency key")

    normalized_email = str(payload.email).strip().lower()
    payload_hash = hashlib.sha256(json.dumps({
        "slot_id": payload.slot_id, "name": payload.name,
        "email": normalized_email,
    }, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    code = 201
    body = {}
    response_headers = {}

    with session.begin():
        if idempotency_key is not None:
            session.execute(
                pg_insert(IdempotencyKey).values(
                    key=idempotency_key, request_hash=payload_hash,
                    status_code=None, response_body=None,
                    created_at=datetime.now(timezone.utc),
                ).on_conflict_do_nothing(index_elements=["key"])
            )
            prior = session.scalar(
                select(IdempotencyKey)
                .where(IdempotencyKey.key == idempotency_key)
                .with_for_update()
            )
            if prior.request_hash != payload_hash:
                return failure(422, "idempotency key already used for different request")
            if prior.status_code is not None:
                # A retry is not a new booking attempt.
                return replay_idempotent_response(prior.status_code, prior.response_body)

        # Serialize attempts for the same normalized email across Vercel instances.
        session.execute(
            pg_insert(RateLimitLock).values(email=normalized_email)
            .on_conflict_do_nothing(index_elements=["email"])
        )
        session.scalar(
            select(RateLimitLock).where(RateLimitLock.email == normalized_email).with_for_update()
        )
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=WINDOW_SECONDS)
        recent = session.scalars(
            select(BookingAttempt.attempted_at)
            .where(
                BookingAttempt.email == normalized_email,
                BookingAttempt.attempted_at > window_start,
            )
            .order_by(BookingAttempt.attempted_at)
        ).all()

        if len(recent) >= MAX_ATTEMPTS:
            retry = max(1, math.ceil((recent[0] + timedelta(seconds=WINDOW_SECONDS) - now).total_seconds()))
            code = 429
            body = {"error": "too many booking attempts"}
            response_headers["Retry-After"] = str(retry)
        else:
            session.add(BookingAttempt(email=normalized_email, attempted_at=now))
            # Lock the slot row, ensuring concurrent bookings are serialized.
            slot = session.scalar(
                select(Slot).where(Slot.id == payload.slot_id).with_for_update()
            )
            if slot is None:
                code, body = 404, {"error": "slot not found"}
            elif slot.start <= now:
                code, body = 400, {"error": "slot has already started"}
            elif session.scalar(
                select(Booking.id).where(
                    Booking.slot_id == payload.slot_id,
                    Booking.status == "confirmed",
                )
            ) is not None:
                code, body = 409, {"error": "slot already booked"}
            else:
                booking = Booking(
                    id=str(uuid4()),
                    slot_id=payload.slot_id,
                    name=payload.name,
                    email=normalized_email,
                    status="confirmed",
                    created_at=now,
                )
                session.add(booking)
                session.flush()
                code, body = 201, booking_json(booking)

        if idempotency_key is not None:
            prior.status_code = code
            prior.response_body = store_idempotent_response(body, response_headers)

    return JSONResponse(status_code=code, content=body, headers=response_headers)


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
            data = json.loads(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)))
            created_at = datetime.fromisoformat(data["t"])
            booking_id = data["id"]
            if not isinstance(booking_id, str) or created_at.tzinfo is None:
                raise ValueError()
        except (ValueError, TypeError, KeyError, UnicodeDecodeError, binascii.Error):
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
    with session.begin():
        booking = session.scalar(
            select(Booking).where(Booking.id == booking_id).with_for_update()
        )
        if booking is None:
            raise HTTPException(status_code=404, detail="booking not found")
        if booking.status == "cancelled":
            raise HTTPException(status_code=409, detail="booking already cancelled")
        booking.status = "cancelled"
        session.flush()
        body = booking_json(booking)
    return body
