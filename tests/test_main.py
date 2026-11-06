from fastapi.testclient import TestClient

from uv_demo import app

client = TestClient(app)


def test_root_health_check() -> None:
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "Hệ thống LMS" in data["message"]


def test_openapi_docs_available() -> None:
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger" in response.text.lower() or "openapi" in response.text.lower()
