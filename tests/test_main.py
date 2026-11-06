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


def test_frontend_web_client_served() -> None:
    # Trình duyệt web gửi header Accept text/html
    response = client.get("/", headers={"Accept": "text/html,application/xhtml+xml"})
    assert response.status_code == 200
    assert "<!DOCTYPE html>" in response.text
    assert "MiniLMS" in response.text


def test_frontend_direct_app_route() -> None:
    response = client.get("/app")
    assert response.status_code == 200
    assert "MiniLMS" in response.text


def test_static_app_js_served() -> None:
    response = client.get("/static/app.js")
    assert response.status_code == 200
    assert "MiniLMS" in response.text


def test_health_check_api_endpoint() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_isolated_login_page_served() -> None:
    response = client.get("/login")
    assert response.status_code == 200
    assert "Đăng Nhập" in response.text
    assert "MiniLMS" in response.text


def test_isolated_register_page_served() -> None:
    response = client.get("/register")
    assert response.status_code == 200
    assert "Đăng Ký Tài Khoản Sinh Viên" in response.text
    assert "MiniLMS" in response.text


def test_get_system_ssot_endpoint() -> None:
    response = client.get("/api/system/ssot")
    assert response.status_code == 200
    data = response.json()
    assert "system" in data
    assert "roles" in data
    assert "test_accounts" in data
    assert "security_safeguards" in data

    # Verify 3 core roles exist
    assert "SV" in data["roles"]
    assert "GV" in data["roles"]
    assert "QT" in data["roles"]

    # Verify security safeguards exist
    safeguards = data["security_safeguards"]
    assert "information_disclosure" in safeguards
    assert "privilege_escalation" in safeguards
    assert "network_and_assets" in safeguards


def test_ssot_elements_in_frontend_pages() -> None:
    # login page
    login_res = client.get("/login")
    assert login_res.status_code == 200
    assert "modal-ssot" in login_res.text
    assert "toggleSSOTModal" in login_res.text
    assert "SSOT (Single Source of Truth)" in login_res.text

    # main index page
    index_res = client.get("/", headers={"Accept": "text/html,application/xhtml+xml"})
    assert index_res.status_code == 200
    assert "modal-ssot" in index_res.text
    assert "openSSOTModal" in index_res.text
