"""ASGI entrypoint recognized automatically by Vercel."""
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI(
    title="Koya Clinic Booking API",
    version="0.1.0",
    description="Koya Cohort 4 assessment — Milestone 0 scaffolding.",
)


@app.get("/", include_in_schema=False)
def home():
    return {"message": "Koya Clinic Booking API", "status": "setup"}


@app.get("/health", tags=["system"])
def health():
    """Liveness endpoint; does not claim that the database is connected."""
    return {"status": "ok", "database": "not_checked"}


@app.exception_handler(404)
async def not_found(_request, _exception):
    return JSONResponse(status_code=404, content={"error": "not found"})
