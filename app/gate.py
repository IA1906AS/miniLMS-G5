"""Authenticate requests before they reach application routes."""

from flask import Flask, g, request

from app.auth import verify_access_token
from app.errors import UnauthenticatedError


def register_gate(app: Flask) -> None:
    @app.before_request
    def authenticate_request() -> None:
        # Chỉ miễn xác thực cho đúng endpoint đăng nhập.
        if request.method == "POST" and request.path == "/auth/login":
            return

        authorization = request.headers.get("Authorization", "")
        parts = authorization.split()

        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise UnauthenticatedError()

        user_id = verify_access_token(
            parts[1],
            app.config["JWT_SECRET"],
        )

        user = app.extensions["store"]["users"].get(user_id)

        if user is None:
            raise UnauthenticatedError()

        g.actor = {
            "id": user["id"],
            "email": user["email"],
            "role": user["role"],
        }
