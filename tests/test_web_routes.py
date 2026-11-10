"""Patient website authentication-boundary smoke tests; no PostgreSQL required."""
import pytest
from fastapi.testclient import TestClient

from src.database import get_session
from src.index import app
from src import web_api


@pytest.fixture
def fake_db():
    def session():
        yield object()
    app.dependency_overrides[get_session] = session
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_patient_routes_registered_but_reset_is_not_public():
    paths = app.openapi()["paths"]
    assert "/web/reset" not in paths
    # Patient-facing routes are deliberately hidden from assessment Swagger.
    assert "/web/bookings" not in paths
    names = {(route.path, tuple(sorted(route.methods))) for route in app.routes}
    assert any(p == "/web/slots" for p, _ in names)
    assert any(p == "/web/bookings" for p, _ in names)
    assert any(p == "/web/bookings/{booking_id}/cancel" for p, _ in names)


def test_public_slots_require_no_shared_key(fake_db, monkeypatch):
    monkeypatch.setattr(web_api, "list_slots", lambda provider, session: {"slots": []})
    response = TestClient(app).get("/web/slots")
    assert response.status_code == 200
    assert response.json() == {"slots": []}


def test_original_assessment_routes_still_require_api_key(monkeypatch):
    monkeypatch.setenv("API_KEY", "unit-test-only")
    client = TestClient(app)
    for method, path in [
        ("GET", "/slots"), ("POST", "/bookings"),
        ("POST", "/reset"), ("GET", "/bookings?email=ada@example.com"),
    ]:
        response = client.request(method, path)
        assert response.status_code == 401


def test_public_lookup_requires_email(fake_db):
    response = TestClient(app).get("/web/bookings/nonexistent")
    assert response.status_code == 400


def test_public_lookup_with_wrong_reference_returns_404(fake_db, monkeypatch):
    class NoBookings:
        def scalar(self, statement):
            return None
    def fake_session():
        yield NoBookings()
    app.dependency_overrides[get_session] = fake_session
    try:
        response = TestClient(app).get("/web/bookings/nonexistent?email=ada@example.com")
    finally:
        app.dependency_overrides.pop(get_session, None)
    assert response.status_code == 404
    assert response.json() == {"error": "booking not found"}
