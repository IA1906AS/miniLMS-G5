from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import create_test_user, get_auth_headers
from uv_demo.models.user import User, UserRole
from uv_demo.services.email import email_service


def test_health_check(client: TestClient) -> None:
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_register_student_success(client: TestClient, db_session: Session) -> None:
    payload = {
        "email": "newstudent@example.com",
        "password": "secretPassword123",
        "full_name": "Nguyễn Văn Sinh Viên",
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 201

    user = db_session.query(User).filter(User.email == "newstudent@example.com").first()
    assert user is not None
    assert user.role == UserRole.SV
    assert user.full_name == "Nguyễn Văn Sinh Viên"


def test_register_duplicate_email_fails(
    client: TestClient, db_session: Session
) -> None:
    create_test_user(db_session, "dup@example.com")
    res = client.post(
        "/api/auth/register",
        json={
            "email": "dup@example.com",
            "password": "password123",
            "full_name": "Duplicate User",
        },
    )
    assert res.status_code == 400
    assert "đã được sử dụng" in res.json()["detail"]


def test_login_success_and_jwt(client: TestClient, db_session: Session) -> None:
    create_test_user(db_session, email="login@example.com", password="mySecretPassword")
    res = client.post(
        "/api/auth/login",
        json={"email": "login@example.com", "password": "mySecretPassword"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["role"] == "SV"


def test_login_wrong_password_fails(client: TestClient, db_session: Session) -> None:
    create_test_user(db_session, email="wrongpass@example.com", password="realPassword")
    res = client.post(
        "/api/auth/login",
        json={"email": "wrongpass@example.com", "password": "wrongPassword"},
    )
    assert res.status_code == 401
    assert "Email hoặc mật khẩu không chính xác" in res.json()["detail"]


def test_login_locked_user_forbidden(client: TestClient, db_session: Session) -> None:
    create_test_user(
        db_session,
        email="locked@example.com",
        password="password123",
        is_active=False,
    )
    res = client.post(
        "/api/auth/login",
        json={"email": "locked@example.com", "password": "password123"},
    )
    assert res.status_code == 403
    assert "Tài khoản của bạn đã bị khóa" in res.json()["detail"]


def test_logout_and_token_revocation(client: TestClient, db_session: Session) -> None:
    user = create_test_user(db_session, email="logout@example.com")
    headers = get_auth_headers(user)

    # Truy cập được khi có token
    res_me = client.get("/api/users/me", headers=headers)
    assert res_me.status_code == 200

    # Đăng xuất thu hồi token trên máy chủ
    res_logout = client.post("/api/auth/logout", headers=headers)
    assert res_logout.status_code == 200

    # Dùng lại token cũ phải bị từ chối 401
    res_retry = client.get("/api/users/me", headers=headers)
    assert res_retry.status_code == 401


def test_password_reset_flow(client: TestClient, db_session: Session) -> None:
    email_service.clear()
    create_test_user(db_session, email="resetme@example.com", password="oldPassword123")

    # 1. Yêu cầu đặt lại mật khẩu
    res_req = client.post(
        "/api/auth/password-reset/request", json={"email": "resetme@example.com"}
    )
    assert res_req.status_code == 200
    assert len(email_service.sent_emails) == 1

    email_sent = email_service.sent_emails[0]
    token = email_sent.content.split("mật khẩu của bạn là: ")[1].split("\n")[0].strip()

    # 2. Xác nhận đặt lại với token nhận được
    res_confirm = client.post(
        "/api/auth/password-reset/confirm",
        json={"token": token, "new_password": "brandNewPassword123"},
    )
    assert res_confirm.status_code == 200

    # 3. Đăng nhập với mật khẩu mới
    res_login = client.post(
        "/api/auth/login",
        json={"email": "resetme@example.com", "password": "brandNewPassword123"},
    )
    assert res_login.status_code == 200


def test_password_change_flow(client: TestClient, db_session: Session) -> None:
    user = create_test_user(
        db_session, email="changepwd@example.com", password="initialPassword123"
    )
    headers = get_auth_headers(user)

    # Nhập sai mật khẩu hiện tại
    res_wrong = client.post(
        "/api/auth/password-change",
        headers=headers,
        json={
            "current_password": "wrongOldPassword",
            "new_password": "nextPassword123",
        },
    )
    assert res_wrong.status_code == 400

    # Nhập đúng mật khẩu hiện tại
    res_ok = client.post(
        "/api/auth/password-change",
        headers=headers,
        json={
            "current_password": "initialPassword123",
            "new_password": "nextPassword123",
        },
    )
    assert res_ok.status_code == 200


def test_security_headers_present(client: TestClient) -> None:
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.headers.get("x-frame-options") == "DENY"
    assert res.headers.get("x-content-type-options") == "nosniff"
    assert res.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert "server" not in res.headers


def test_login_nonexistent_user_generic_error(client: TestClient) -> None:
    res = client.post(
        "/api/auth/login",
        json={"email": "nonexistent@example.com", "password": "wrongPassword123"},
    )
    assert res.status_code == 401
    assert res.json()["detail"] == "Email hoặc mật khẩu không chính xác."
