from fastapi.testclient import TestClient

from uv_demo import app

client = TestClient(app)


def test_health_check() -> None:
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "FastAPI CI Service" in data["message"]


def test_calculate_add() -> None:
    response = client.post("/add", json={"a": 12.5, "b": 7.5})
    assert response.status_code == 200
    data = response.json()
    assert data["a"] == 12.5
    assert data["b"] == 7.5
    assert data["result"] == 20.0


def test_calculate_add_invalid() -> None:
    response = client.post("/add", json={"a": "not-a-number", "b": 5})
    assert response.status_code == 422
