from fastapi.testclient import TestClient

from src.index import app


def test_reset_requires_api_key(monkeypatch):
    monkeypatch.setenv("API_KEY", "testing-secret")
    response = TestClient(app).post("/reset", json={"slots": []})
    assert response.status_code == 401
    assert response.json() == {"error": "invalid API key"}


def test_slots_requires_api_key(monkeypatch):
    monkeypatch.setenv("API_KEY", "testing-secret")
    response = TestClient(app).get("/slots")
    assert response.status_code == 401
    assert response.json() == {"error": "invalid API key"}


def test_reset_without_configuration(monkeypatch):
    monkeypatch.delenv("API_KEY", raising=False)
    response = TestClient(app).post("/reset", json={"slots": []})
    assert response.status_code == 503
    assert response.json() == {"error": "API not configured"}
