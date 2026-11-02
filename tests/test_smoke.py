from fastapi.testclient import TestClient

from src.index import app


def test_home():
    response = TestClient(app).get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "koyaclinic." in response.text


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


def test_ready_without_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    response = TestClient(app).get("/ready")
    assert response.status_code == 503
    assert response.json() == {"error": "database not configured"}


def test_frontend_assets():
    client = TestClient(app)
    css = client.get("/styles.css")
    js = client.get("/app.js")
    assert css.status_code == 200
    assert "text/css" in css.headers["content-type"]
    assert js.status_code == 200
    assert "javascript" in js.headers["content-type"]
