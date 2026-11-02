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
    except Exception as exc:
        # Temporary, deliberately coarse diagnostic. Never return raw errors,
        # connection URLs, usernames, passwords, or driver messages.
        message = str(exc).lower()
        if "password authentication failed" in message or "28p01" in message:
            reason = "authentication_failed"
        elif "name or service not known" in message or "getaddrinfo" in message or "could not translate host" in message:
            reason = "hostname_lookup_failed"
        elif "connection refused" in message or "could not connect to server" in message:
            reason = "connection_refused"
        elif "timeout" in message or "timed out" in message:
            reason = "connection_timeout"
        elif "invalid dsn" in message or "could not parse" in message or "could not parse sql" in message or "can't load plugin" in message or "no such module" in message:
            reason = "connection_configuration"
        elif "ssl" in message or "certificate" in message:
            reason = "tls_error"
        elif "role" in message and "does not exist" in message:
            reason = "database_role_not_found"
        elif "database" in message and "does not exist" in message:
            reason = "database_not_found"
        else:
            reason = "unclassified_connection_error"
        return JSONResponse(
            status_code=503,
            content={"error": "database unavailable", "diagnostic": reason},
        )

    return {"status": "ok", "database": "connected"}


@app.exception_handler(404)
async def not_found(_request, _exception):
    return JSONResponse(status_code=404, content={"error": "not found"})
