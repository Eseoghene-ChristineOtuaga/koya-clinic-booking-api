"""ASGI entrypoint recognized automatically by Vercel."""
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.database import get_engine
from src.slots_api import router as clinic_router
from src.bookings_api import router as bookings_router

app = FastAPI(
    title="Koya Clinic Booking API",
    version="0.1.0",
    description="Koya Cohort 4 assessment — database connection setup.",
)


app.include_router(clinic_router)
app.include_router(bookings_router)

PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(PUBLIC_DIR / "index.html", media_type="text/html")


@app.get("/styles.css", include_in_schema=False)
def stylesheet():
    return FileResponse(PUBLIC_DIR / "styles.css", media_type="text/css")


@app.get("/app.js", include_in_schema=False)
def frontend_script():
    return FileResponse(PUBLIC_DIR / "app.js", media_type="application/javascript")


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


@app.exception_handler(HTTPException)
async def http_error(_request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": str(exc.detail)}, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def request_validation_error(_request: Request, _exc: RequestValidationError):
    return JSONResponse(status_code=400, content={"error": "invalid request"})
