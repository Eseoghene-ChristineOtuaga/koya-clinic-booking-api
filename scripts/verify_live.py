"""Verify Koya levels 1–5 against the deployed API without calling /reset.

Usage:
    python scripts/verify_live.py

No key is stored: the script asks for it using getpass. It creates temporary
fictional bookings in existing future demo slots, cancels successful bookings,
and leaves cancellation history/attempt records as expected for an audit.
"""
from __future__ import annotations

import getpass
import json
import os
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = os.environ.get("KOYA_BASE_URL", "https://koya-clinic-booking-api.vercel.app").rstrip("/")
KEY = os.environ.get("KOYA_API_KEY") or getpass.getpass("Enter Koya API key (hidden): ").strip()
IDENTITY = uuid.uuid4().hex[:12]
created_booking_ids: set[str] = set()
checks = 0
failed = False


def request(method: str, path: str, body: dict | None = None, *, headers: dict | None = None):
    raw = json.dumps(body).encode() if body is not None else None
    final_headers = {"X-API-Key": KEY, **(headers or {})}
    if raw is not None:
        final_headers["Content-Type"] = "application/json"
    req = Request(BASE_URL + path, data=raw, headers=final_headers, method=method)
    try:
        with urlopen(req, timeout=20) as resp:
            status, data, hdrs = resp.status, resp.read(), resp.headers
    except HTTPError as error:
        status, data, hdrs = error.code, error.read(), error.headers
    return status, json.loads(data) if data else {}, hdrs


def expect(label, condition):
    global checks
    if not condition:
        raise AssertionError("FAIL: " + label)
    checks += 1
    print("PASS:", label)


def cancel(booking_id: str):
    status, body, _ = request("DELETE", "/bookings/" + booking_id)
    if status == 200:
        created_booking_ids.discard(booking_id)
    return status, body


def post(slot, name, email, key=None):
    headers = {"Idempotency-Key": key} if key else {}
    return request("POST", "/bookings", {"slot_id": slot, "name": name, "email": email}, headers=headers)


def future_free_slots():
    status, body, _ = request("GET", "/slots")
    expect("Level 1: GET /slots gives JSON", status == 200 and isinstance(body.get("slots"), list))
    slots = [s for s in body["slots"] if s["available"]
             and datetime.fromisoformat(s["start"].replace("Z", "+00:00")) > datetime.now(timezone.utc)]
    return slots


try:
    if not KEY:
        raise RuntimeError("No API key supplied.")

    # Level 2: all protected endpoints must reject missing/wrong keys.
    status, body, _ = request("GET", "/slots", headers={"X-API-Key": "definitely-invalid-key"})
    expect("Level 2: invalid API key rejected", status == 401 and "error" in body)

    slots = future_free_slots()
    expect("Test prerequisites: three future free slots", len(slots) >= 3)

    provider = slots[0]["provider"]
    status, body, _ = request("GET", "/slots?" + urlencode({"provider": provider}))
    expect("Level 1: provider filter", status == 200 and all(s["provider"] == provider for s in body["slots"]))

    status, body, _ = request("POST", "/bookings",
                             {"slot_id": slots[0]["id"], "name": " ", "email": "not-an-email"})
    expect("Level 2: invalid details return 400", status == 400 and "error" in body)

    # Level 3: use two test emails so both requests compete for one free slot.
    concurrent_slot = slots[0]["id"]
    def compete(n):
        return post(concurrent_slot, "Test Patient", f"concurrent-{n}-{IDENTITY}@example.com")
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(compete, range(2)))
    for status, body, _ in responses:
        if status == 201 and body.get("id"):
            created_booking_ids.add(body["id"])
    expect("Level 3: simultaneous requests yield one 201 and one 409",
           sorted(s for s, _, _ in responses) == [201, 409])
    booking_id = next(iter(created_booking_ids))
    status, body, _ = request("GET", "/bookings/" + booking_id)
    expect("Level 1: retrieve created booking", status == 200 and body["id"] == booking_id)
    status, body = cancel(booking_id)
    expect("Level 3: cancel booking", status == 200 and body["status"] == "cancelled")
    status, body = cancel(booking_id)
    expect("Level 3: repeat cancellation is conflict", status == 409)
    status, body, _ = request("GET", "/slots")
    expect("Level 3: cancelled slot becomes available",
           status == 200 and any(s["id"] == concurrent_slot and s["available"] for s in body["slots"]))

    # Level 4: same key + payload must replay exactly; changed payload gets 422.
    idem_slot = slots[1]["id"]
    idem_email = f"idempotent-{IDENTITY}@example.com"
    idem_key = f"koya-verify-success-{IDENTITY}"
    first_status, first, _ = post(idem_slot, "Test Patient", idem_email, idem_key)
    if first_status == 201:
        created_booking_ids.add(first["id"])
    second_status, second, _ = post(idem_slot, "Test Patient", idem_email, idem_key)
    expect("Level 4: retry has original status and booking id",
           first_status == second_status == 201 and first["id"] == second["id"])
    status, body, _ = post(idem_slot, "Different Patient", idem_email, idem_key)
    expect("Level 4: key used for changed payload gives 422", status == 422)
    status, body = cancel(first["id"])
    expect("Level 3: cancel idempotency test booking", status == 200)

    # Level 4: two real bookings, oldest-first pages, one per page.
    email = f"pagination-{IDENTITY}@example.com"
    pagination_ids = []
    for idx, slot in enumerate(slots[1:3]):
        status, booking, _ = post(slot["id"], "Test Pagination", email)
        expect(f"Level 1: create pagination booking {idx + 1}", status == 201)
        created_booking_ids.add(booking["id"])
        pagination_ids.append(booking["id"])
    status, p1, _ = request("GET", "/bookings?" + urlencode({"email": email.upper(), "limit": 1}))
    expect("Level 4: page 1 includes next_cursor",
           status == 200 and len(p1["bookings"]) == 1 and bool(p1["next_cursor"]))
    status, p2, _ = request("GET", "/bookings?" + urlencode(
        {"email": email, "limit": 1, "cursor": p1["next_cursor"]}))
    expect("Level 4: page 2 retrieves the next booking",
           status == 200 and len(p2["bookings"]) == 1
           and p1["bookings"][0]["id"] != p2["bookings"][0]["id"]
           and set(pagination_ids) == {p1["bookings"][0]["id"], p2["bookings"][0]["id"]})
    status, body, _ = request("GET", "/bookings?" + urlencode({"email": email, "limit": 51}))
    expect("Level 4: invalid pagination limit returns 400", status == 400)

    # Level 5: failed attempts at an unknown slot still count.
    spam_email = f"ratelimit-{IDENTITY}@example.com"
    for n in range(5):
        status, body, _ = post(f"nonexistent-{IDENTITY}", "Test Rate Limit", spam_email)
        expect(f"Level 5: failed attempt {n+1} counted", status == 404)
    throttle_key = f"koya-verify-throttle-{IDENTITY}"
    code, limited, headers = post(f"nonexistent-{IDENTITY}", "Test Rate Limit", spam_email, throttle_key)
    retry = headers.get("Retry-After")
    expect("Level 5: sixth attempt returns 429 and integer Retry-After",
           code == 429 and retry is not None and retry.isdecimal() and int(retry) >= 1)
    code2, limited2, headers2 = post(f"nonexistent-{IDENTITY}", "Test Rate Limit", spam_email, throttle_key)
    expect("Level 4+5: replayed 429 preserves body and Retry-After",
           code2 == code and limited2 == limited and headers2.get("Retry-After") == retry)
    status, body, _ = post(f"different-nonexistent-{IDENTITY}", "Test Rate Limit", spam_email, throttle_key)
    expect("Level 4: changed payload under throttled idempotency key gives 422", status == 422)

    print(f"\nALL {checks} CHECKS PASSED. Temporary successful bookings will be cancelled.")
except (AssertionError, RuntimeError, URLError, KeyError, ValueError) as error:
    print("\nFAILED:", error, file=sys.stderr)
    failed = True
finally:
    for booking_id in list(created_booking_ids):
        try:
            status, _ = cancel(booking_id)
            if status != 200:
                print("WARNING: could not cancel test booking", booking_id, "status", status)
        except Exception as e:
            print("WARNING: cleanup failed for booking", booking_id, type(e).__name__)

if failed:
    sys.exit(1)
