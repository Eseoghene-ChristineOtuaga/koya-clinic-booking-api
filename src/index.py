"""ASGI entrypoint recognized automatically by Vercel."""
import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.database import get_engine

app = FastAPI(
    title="Koya Clinic Booking API",
    version="0.1.0",
    description="Koya Cohort 4 assessment — database connection setup.",
)


@app.get("/", include_in_schema=False)
def home():
    return {"message": "Koya Clinic Booking API", "status": "setup"}


@app.get("/health", tags=["system"])
def health():
    """Liveness endpoint; database status is checked separately."""
    return {"status": "ok", "database": "not_checked"}


@app.get("/ready", tags=["system"])
def ready():
    """Database connectivity check; never expose URLs or SQL errors."""
    if not os.getenv("DATABASE_URL"):
        return JSONResponse(status_code=503, content={"error": "database not configured"})

    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
    except (SQLAlchemyError, OSError, TimeoutError):
        return JSONResponse(status_code=503, content={"error": "database unavailable"})

    return {"status": "ok", "database": "connected"}


@app.exception_handler(404)
async def not_found(_request, _exception):
    return JSONResponse(status_code=404, content={"error": "not found"})
