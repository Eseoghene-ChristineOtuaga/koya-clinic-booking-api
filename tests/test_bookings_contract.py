"""Contract-level smoke checks that do not require live PostgreSQL."""
import pytest
from fastapi.testclient import TestClient

from src.database import get_session

from src.index import app


@pytest.fixture
def no_database():
    """Validation tests never query PostgreSQL; avoid engine creation in CI."""
    def fake_get_session():
        yield None

    app.dependency_overrides[get_session] = fake_get_session
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_booking_routes_are_registered():
    paths = app.openapi()["paths"]
    assert "post" in paths["/bookings"]
    assert "get" in paths["/bookings"]
    assert "get" in paths["/bookings/{booking_id}"]
    assert "delete" in paths["/bookings/{booking_id}"]


def test_bookings_require_authentication(monkeypatch):
    monkeypatch.setenv("API_KEY", "unit-test-only")
    client = TestClient(app)
    for method, path in [
        ("POST", "/bookings"),
        ("GET", "/bookings?email=ada@example.com"),
        ("GET", "/bookings/unlisted"),
        ("DELETE", "/bookings/unlisted"),
    ]:
        response = client.request(method, path)
        assert response.status_code == 401
        assert response.json() == {"error": "invalid API key"}


def test_invalid_booking_is_json_error(monkeypatch, no_database):
    monkeypatch.setenv("API_KEY", "unit-test-only")
    response = TestClient(app).post(
        "/bookings",
        headers={"X-API-Key": "unit-test-only"},
        json={"slot_id": "s1", "name": "   ", "email": "not-an-email"},
    )
    assert response.status_code == 400
    assert "error" in response.json()


def test_booking_limit_validation(monkeypatch, no_database):
    monkeypatch.setenv("API_KEY", "unit-test-only")
    response = TestClient(app).get(
        "/bookings?email=ada@example.com&limit=51",
        headers={"X-API-Key": "unit-test-only"},
    )
    assert response.status_code == 400
    assert "error" in response.json()
