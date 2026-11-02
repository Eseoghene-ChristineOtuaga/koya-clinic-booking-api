"""Protected administrative reset and slot listing routes."""
import os
import secrets
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import delete, exists, select
from sqlalchemy.orm import Session

from src.database import get_session
from src.models import Booking, BookingAttempt, IdempotencyKey, RateLimitLock, Slot

router = APIRouter()


def require_api_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    configured = os.getenv("API_KEY")
    if not configured:
        raise HTTPException(status_code=503, detail="API not configured")
    if not x_api_key or not secrets.compare_digest(x_api_key, configured):
        raise HTTPException(status_code=401, detail="invalid API key")


class SlotInput(BaseModel):
    id: str = Field(min_length=1, max_length=255)
    provider: str = Field(min_length=1, max_length=255)
    start: datetime
    end: datetime

    @field_validator("id", "provider")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("must not be blank")
        return value

    @model_validator(mode="after")
    def valid_period(self):
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("slot times must include timezone")
        if self.end <= self.start:
            raise ValueError("slot end must be after start")
        return self


class ResetInput(BaseModel):
    slots: list[SlotInput]


@router.post("/reset", dependencies=[Depends(require_api_key)])
def reset(payload: ResetInput, session: Session = Depends(get_session)):
    ids = [slot.id for slot in payload.slots]
    if len(ids) != len(set(ids)):
        raise HTTPException(status_code=400, detail="duplicate slot id")

    # All changes are in one transaction; FK children are deleted first.
    with session.begin():
        session.execute(delete(Booking))
        session.execute(delete(IdempotencyKey))
        session.execute(delete(BookingAttempt))
        session.execute(delete(RateLimitLock))
        session.execute(delete(Slot))
        session.add_all(
            Slot(id=s.id, provider=s.provider, start=s.start, end=s.end)
            for s in payload.slots
        )

    return {"slots": len(payload.slots)}


@router.get("/slots", dependencies=[Depends(require_api_key)])
def list_slots(provider: str | None = Query(default=None), session: Session = Depends(get_session)):
    booked = exists(select(Booking.id).where(
        Booking.slot_id == Slot.id, Booking.status == "confirmed"
    ))
    statement = select(Slot, booked.label("booked")).order_by(Slot.start, Slot.id)
    if provider is not None:
        statement = statement.where(Slot.provider == provider)
    result = session.execute(statement).all()
    return {"slots": [
        {
            "id": slot.id,
            "provider": slot.provider,
            "start": slot.start.isoformat().replace("+00:00", "Z"),
            "end": slot.end.isoformat().replace("+00:00", "Z"),
            "available": not has_booking,
        }
        for slot, has_booking in result
    ]}
