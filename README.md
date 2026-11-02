# Koya Clinic Booking API

A full-stack clinic appointment-booking system for Koya Academy Cohort 4. Built with FastAPI, PostgreSQL (Supabase), and vanilla JavaScript, hosted on Vercel.

> **Current status: Milestone 0 starter only.** The booking endpoints, database migrations, API-key authentication, and rate limiting have not been implemented yet.

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
4. Apply version-controlled schema migrations (not yet created).

The `/health` endpoint intentionally checks only process liveness, not database connectivity.

## Project layout

```text
src/index.py         FastAPI ASGI entrypoint
src/database.py      SQLAlchemy engine/session helpers
src/models.py        Initial database models (not migrated)
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
