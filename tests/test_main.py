from pathlib import Path

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


def test_zero_information_disclosure_on_public_web_and_api() -> None:
    # SSOT must strictly be a local Antigravity file, never exposed on web API
    ssot_res = client.get("/api/system/ssot")
    assert ssot_res.status_code == 404

    forbidden_leaks = [
        "admin123",
        "teacher123",
        "student123",
        "admin@lms.edu.vn",
        "teacher@lms.edu.vn",
        "student1@lms.edu.vn",
        "modal-ssot",
        "quickLogin",
    ]
    for route in ["/login", "/register", "/app", "/static/app.js"]:
        res = client.get(route)
        assert res.status_code == 200
        for secret in forbidden_leaks:
            assert secret not in res.text, (
                f"Information disclosure detected in {route}: {secret}"
            )


def test_no_god_files_exceed_350_lines() -> None:
    project_root = Path(__file__).resolve().parent.parent
    for folder in ("src", "tests"):
        for file_path in (project_root / folder).rglob("*"):
            if file_path.is_file() and "__pycache__" not in file_path.parts:
                line_count = len(file_path.read_text(encoding="utf-8").splitlines())
                assert line_count <= 350, (
                    f"God file detected: {file_path.relative_to(project_root)} "
                    f"has {line_count} lines (maximum allowed is 350)."
                )


def test_postgresql_database_url_resolution(monkeypatch: object) -> None:
    import os

    from uv_demo.config import _resolve_database_url

    old_url = os.environ.pop("DATABASE_URL", None)
    try:
        os.environ["POSTGRES_USER"] = "postgres"
        os.environ["POSTGRES_PASSWORD"] = "secret"
        os.environ["POSTGRES_HOST"] = "127.0.0.1"
        os.environ["POSTGRES_PORT"] = "5432"
        os.environ["POSTGRES_DB"] = "minilms"
        resolved = _resolve_database_url()
        assert resolved == "postgresql+psycopg://postgres:secret@127.0.0.1:5432/minilms"

        os.environ["DATABASE_URL"] = "postgresql://postgres:secret@localhost:5432/lms"
        assert (
            _resolve_database_url()
            == "postgresql+psycopg://postgres:secret@localhost:5432/lms"
        )
    finally:
        if old_url is not None:
            os.environ["DATABASE_URL"] = old_url
        else:
            os.environ.pop("DATABASE_URL", None)
