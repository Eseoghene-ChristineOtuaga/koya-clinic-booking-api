from fastapi.testclient import TestClient

from src.index import app


def test_home():
    response = TestClient(app).get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "setup"


def test_health():
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "not_checked"}


def test_not_found_shape():
    response = TestClient(app).get("/does-not-exist")
    assert response.status_code == 404
    assert response.json() == {"error": "not found"}


def test_openapi_documentation():
    response = TestClient(app).get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"] == "Koya Clinic Booking API"
