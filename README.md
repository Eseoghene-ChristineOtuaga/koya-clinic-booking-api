# Koya Clinic Booking API

A full-stack clinic appointment booking system for the Koya Academy Cohort 4 assessment. Built with **FastAPI**, **PostgreSQL (Supabase)**, and **vanilla HTML/CSS/JavaScript**; deployed on **Vercel**.

- **Live webpage:** https://koya-clinic-booking-api.vercel.app/
- **Interactive API documentation:** https://koya-clinic-booking-api.vercel.app/docs
- **Database health:** https://koya-clinic-booking-api.vercel.app/ready
- **Assessment contract:** https://koyaacademy.com/assessment-api

## Implemented features

| Level | Features |
| --- | --- |
| 1 | List appointment slots, book a slot, retrieve a booking |
| 2 | API key authorization, validated booking details, JSON errors |
| 3 | PostgreSQL row locks and unique confirmed-slot constraint, cancellation |
| 4 | Transactional idempotency keys (including replayed `Retry-After`), cursor-based booking pagination |
| 5 | Per-normalized-email, rolling 60-second limit of five booking attempts |

**Implementation is not proof of correctness:** run the smoke tests and live verification suite below. The live test suite deliberately uses fictional details, and **never calls `/reset`**.


## API surfaces and responses

- **Assessment API (requires `X-API-Key`):** `GET /slots`, `POST /reset`, `POST /bookings`, `GET /bookings/{booking_id}`, `GET /bookings?email=...&limit=...&cursor=...`, and `DELETE /bookings/{booking_id}`.
- **Patient-facing website API (no shared key prompt):** `GET /web/slots`, `POST /web/bookings`, `GET /web/bookings/{booking_id}?email=...`, and `POST /web/bookings/{booking_id}/cancel` with JSON body `{"email":"patient@example.com"}`. These `/web` routes are hidden from assessment Swagger documentation to keep the contract clear.
- Booking creation returns `201` on success; errors include `400` invalid input, `401` missing/incorrect assessment key, `404` unknown slot/booking, `409` occupied slot or repeated cancellation, `422` reused idempotency key with changed request, and `429` excessive booking attempts (with `Retry-After`).
- `POST /reset` **deletes all booking and rate-limit history, replaces every slot, and should only be used deliberately for assessment setup**. Cancelling a booking retains its history instead.
- `GET /health` checks the application, whereas `GET /ready` checks PostgreSQL connectivity.

## Run locally (Windows PowerShell)

Requirements: Python 3.11+ and Git.

```powershell
git clone https://github.com/Eseoghene-ChristineOtuaga/koya-clinic-booking-api.git
cd koya-clinic-booking-api
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

To run the API locally, create a **private, uncommitted** `.env` with your database URL and API key, load it into your shell, and run:

```powershell
python -m uvicorn src.index:app --reload
```

The UI is served at `/`; the API docs at `/docs`.

## Verify the live assessment requirements

Run **after** the unit tests and after production reports `READY` in Vercel:

```powershell
python scripts/verify_live.py
```

The script prompts **privately** for your API key (it is not saved). By default it tests `https://koya-clinic-booking-api.vercel.app`.

It checks:

1. Slot listing, provider filtering, booking creation, and lookup.
2. Authentication and invalid booking fields.
3. Two simultaneous booking requests for one slot (exactly one succeeds), cancellation, repeat cancellation, and slot release.
4. Same-key booking retry, key reuse with different payload (422), two pages of email-filtered bookings, and invalid pagination limit.
5. Six rapid booking attempts by one email: the first five reach slot handling, the sixth gets 429 + integer `Retry-After`. It also checks replaying that 429 with the same idempotency key retains the **exact** status, body, and header.

**Prerequisites:** at least three future, unbooked slots, and network access to the live API.

**Safety:** the script never resets slots, uses uniquely generated `example.com` fictional patient emails, cancels successful test bookings in a `finally` block, and prints a warning if a cancellation fails. Cancelled booking history and rate-limit attempt records remain (by design). Prefer running against a dedicated staging deployment and database if available; use production only when these limited test writes are acceptable. Check the output before submitting. If a test fails, investigate rather than repeatedly running it.

For a non-production deployment, override the base URL in PowerShell:

```powershell
$env:KOYA_BASE_URL="https://YOUR-STAGING-DEPLOYMENT.vercel.app"
python scripts/verify_live.py
```

## Manual browser checklist

Open the live website at desktop and mobile widths. No API key is needed on the patient-facing webpage. Select a clinician, an available date and time, and submit a **fictional** booking. Copy its booking reference; under **Manage booking**, enter both the reference and booking email, retrieve the record, and cancel it. Verify the slot becomes available again. Test the mobile hamburger menu and the header transition on scroll.

The protected assessment routes (`/slots`, `/bookings`, and `/reset`) still require the `X-API-Key` request header. The patient-facing website instead calls separate `/web/*` routes without the shared API key. `/web/reset` does not exist. The key is never bundled into browser code.

**Privacy limitations:** Patient booking lookup and cancellation on `/web/*` require a booking reference and matching email, but this is **not authenticated patient login**. A production clinic must use verified sessions or one-time links before accessing or changing personal bookings. Public booking creation is limited by normalized email (five attempts per rolling 60 seconds); this does not stop all automated abuse. Use fictional patient details only.

## Deployment and security

Vercel recognizes `src/index.py` and the `vercel.json` FastAPI setting. Configure `API_KEY` and `DATABASE_URL` as **sensitive server environment variables**, not Git-tracked files. Use Supabase PostgreSQL transaction pooling (port 6543) and the `postgresql+psycopg://` URL scheme. The schema `koya_clinic` is isolated from other application schemas.

For demo/testing use fictional patients. Rotate any API key that has appeared in screenshots or shared messages before final submission. The assessment also requires a demonstration video of at most five minutes.

## Source structure

```text
src/index.py                 FastAPI ASGI entrypoint and static routes
src/bookings_api.py          Booking, cancellation, pagination, rate limit
src/slots_api.py             Protected API-key validation, reset, slot listing
src/web_api.py               Keyless patient booking routes (reference+email lookup)
src/models.py                PostgreSQL/SQLAlchemy models
src/database.py              Database session and engine
migrations/                  Alembic database migrations
public/                      Responsive booking webpage
tests/                       Automated Python tests
scripts/verify_live.py       Live contract verification + cleanup
.vscode/mcp.json             Playwright and Chrome DevTools MCP configuration
```

Project notes: https://app.notion.com/p/40c11f4d5e0c8109ae96f780e02c452e
