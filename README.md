# Koya Clinic Booking API

A full-stack clinic appointment-booking system for Koya Academy Cohort 4. Built with FastAPI, PostgreSQL (Supabase), and vanilla JavaScript, hosted on Vercel.

> **Current status:** FastAPI starter is deployed. Database schema and Alembic migration files are committed, but no real database migration has been run. Booking endpoints, API-key authentication, and rate limiting are still to be implemented.

## Quick start

Requirements: Python 3.11+ and Git.

```powershell
git clone https://github.com/Eseoghene-ChristineOtuaga/koya-clinic-booking-api.git
cd koya-clinic-booking-api
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m uvicorn src.index:app --reload
```

Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) to view the local OpenAPI documentation. The root path returns a JSON starter response under Uvicorn; the patient-facing placeholder in `public/index.html` is served directly by Vercel.

To run tests:

```powershell
python -m pytest -q
```

## Hosting

Vercel automatically recognizes the exported `app` object in `src/index.py`. The static web page lives in `public/`.

Import this GitHub repository into [Vercel](https://vercel.com/new) and use the **FastAPI** framework (the `vercel.json` file declares it). **Do not add actual API keys or database passwords to Git.**

Database configuration in later milestones:
1. Provision Supabase PostgreSQL.
2. Copy `.env.example` to `.env` for local configuration. Supply the actual `DATABASE_URL` locally; never commit it.
3. Set `DATABASE_URL` and `API_KEY` in Vercel Environment Variables.
4. Apply the initial migration to the new database using `python -m alembic upgrade head` from a trusted development environment. Never run migrations in request handlers.

**Important:** For Vercel serverless functions, use Supabase's *Transaction pooler* URL (port 6543), and change the URL scheme from `postgresql://` or `postgres://` to `postgresql+psycopg://`. The project disables prepared statements and uses SQLAlchemy `NullPool` for this mode. The database connection has not yet been provisioned or live-tested.

The `/health` endpoint intentionally checks only process liveness, not database connectivity.

## Project layout

```text
src/index.py         FastAPI ASGI entrypoint
src/database.py      SQLAlchemy engine/session helpers
src/models.py        PostgreSQL models (not yet migrated)
migrations/          Alembic schema migration files
alembic.ini          Migration configuration
public/              Static UI placeholder
tests/               Initial smoke tests
vercel.json          Vercel framework configuration
.env.example         Environment variable names, no secrets
```

## Specification and progress

- [Koya assessment API contract](https://koyaacademy.com/assessment-api)
- [Notion project board](https://app.notion.com/p/40c11f4d5e0c8109ae96f780e02c452e)
- The eventual API will implement `/reset`, `/slots`, `/bookings`, and `/bookings/{id}` exactly as specified.

## Security

Never commit actual `DATABASE_URL` or `API_KEY` values. Patient details should never be logged in plaintext. The live assessment endpoints will require `X-API-Key`, including the reset endpoint.
