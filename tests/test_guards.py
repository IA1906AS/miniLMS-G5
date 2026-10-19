"""Exercise role authorization through Flask requests."""

import pytest
from flask import Flask, Response, jsonify

from app import create_app
from app.auth import create_access_token
from app.errors import UnauthenticatedError
from app.guards import require_role


@pytest.fixture(scope="module")
def guarded_app() -> Flask:
    app = create_app(
        {
            "TESTING": True,
            "JWT_SECRET": "test-only-" + "x" * 32,
            "TOKEN_TTL_SECONDS": "900",
        }
    )

    @app.get("/test/instructor-only")
    @require_role("INSTRUCTOR")
    def instructor_only() -> Response:
        return jsonify(allowed=True)

    @app.get("/test/deny-all")
    @require_role()
    def deny_all() -> Response:
        raise AssertionError("An empty role allowlist must reject every actor")

    return app


def bearer_headers(app: Flask, user_id: str) -> dict[str, str]:
    token = create_access_token(
        user_id,
        app.config["JWT_SECRET"],
        app.config["TOKEN_TTL_SECONDS"],
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize(
    ("user_id", "email", "role"),
    [
        ("u1", "admin@lms.test", "ADMIN"),
        ("u2", "an.gv@lms.test", "INSTRUCTOR"),
        ("u4", "chi.sv@lms.test", "STUDENT"),
    ],
)
def test_me_accepts_each_seed_role(
    guarded_app: Flask, user_id: str, email: str, role: str
) -> None:
    response = guarded_app.test_client().get(
        "/me", headers=bearer_headers(guarded_app, user_id)
    )

    assert response.status_code == 200
    assert response.get_json() == {"id": user_id, "email": email, "role": role}


@pytest.mark.parametrize(
    ("user_id", "expected_status"), [("u1", 403), ("u2", 200), ("u4", 403)]
)
def test_instructor_route_requires_explicit_role(
    guarded_app: Flask, user_id: str, expected_status: int
) -> None:
    response = guarded_app.test_client().get(
        "/test/instructor-only", headers=bearer_headers(guarded_app, user_id)
    )

    assert response.status_code == expected_status
    expected = {"allowed": True} if expected_status == 200 else {"error": "FORBIDDEN"}
    assert response.get_json() == expected


def test_missing_token_returns_401_before_role_check(guarded_app: Flask) -> None:
    response = guarded_app.test_client().get("/test/instructor-only")

    assert response.status_code == 401
    assert response.get_json() == {"error": "UNAUTHENTICATED"}


def test_role_change_applies_to_existing_token(
    guarded_app: Flask, monkeypatch: pytest.MonkeyPatch
) -> None:
    headers = bearer_headers(guarded_app, "u2")
    client = guarded_app.test_client()
    assert client.get("/test/instructor-only", headers=headers).status_code == 200

    user = guarded_app.extensions["store"]["users"]["u2"]
    monkeypatch.setitem(user, "role", "STUDENT")
    response = client.get("/test/instructor-only", headers=headers)

    assert response.status_code == 403
    assert response.get_json() == {"error": "FORBIDDEN"}


def test_empty_allowlist_denies_even_admin(guarded_app: Flask) -> None:
    response = guarded_app.test_client().get(
        "/test/deny-all", headers=bearer_headers(guarded_app, "u1")
    )

    assert response.status_code == 403
    assert response.get_json() == {"error": "FORBIDDEN"}


def test_decorator_rejects_missing_actor(guarded_app: Flask) -> None:
    @require_role("ADMIN")
    def protected_view() -> None:
        raise AssertionError("An unauthenticated actor must not reach the view")

    with guarded_app.test_request_context(), pytest.raises(UnauthenticatedError):
        protected_view()


def test_factory_normalizes_token_ttl(guarded_app: Flask) -> None:
    assert guarded_app.config["TOKEN_TTL_SECONDS"] == 900
    assert isinstance(guarded_app.config["TOKEN_TTL_SECONDS"], int)
