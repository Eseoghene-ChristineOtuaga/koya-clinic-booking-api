"""Regression tests for preserved headers and legacy idempotency records."""
from src.bookings_api import replay_idempotent_response, store_idempotent_response


def test_rate_limit_replay_keeps_retry_after_and_body():
    original = {"error": "too many booking attempts"}
    stored = store_idempotent_response(original, {"Retry-After": "42"})
    response = replay_idempotent_response(429, stored)
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "42"
    import json
    assert json.loads(response.body) == original
    assert "__koya_response_v1__" not in response.body.decode()


def test_legacy_records_still_replay():
    import json
    old_record = {"id": "booking-id", "status": "confirmed"}
    response = replay_idempotent_response(201, old_record)
    assert response.status_code == 201
    assert json.loads(response.body) == old_record
    assert response.headers.get("Retry-After") is None


def test_non_429_responses_keep_public_shape():
    import json
    original = {"error": "slot already booked"}
    stored = store_idempotent_response(original, {})
    response = replay_idempotent_response(409, stored)
    assert response.status_code == 409
    assert json.loads(response.body) == original
