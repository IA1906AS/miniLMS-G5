"""Application factory for the LMS API."""

import os
from collections.abc import Mapping

from flask import Flask, Response, g, jsonify

from app.auth import auth_bp
from app.errors import register_error_handlers
from app.gate import register_gate
from app.guards import require_role
from app.store import load_store


def create_app(config: Mapping[str, object] | None = None) -> Flask:
    app = Flask(__name__)

    # Đọc biến môi trường, dùng mặc định nếu chưa có.
    app.config.from_mapping(
        JWT_SECRET=os.getenv("JWT_SECRET"),
        TOKEN_TTL_SECONDS=os.getenv("TOKEN_TTL_SECONDS", "900"),
        AUDIT_LOG_PATH=os.getenv("AUDIT_LOG_PATH", "audit.log"),
    )

    # Config truyền vào được ưu tiên hơn biến môi trường.
    if config is not None:
        app.config.update(config)

    # Kiểm tra cấu hình sau khi đã áp dụng các giá trị ghi đè.
    secret = app.config["JWT_SECRET"]
    if not isinstance(secret, str) or len(secret) < 32:
        raise RuntimeError("JWT_SECRET must contain at least 32 characters.")

    try:
        ttl = int(app.config["TOKEN_TTL_SECONDS"])
    except (TypeError, ValueError) as exc:
        raise RuntimeError("TOKEN_TTL_SECONDS must be a positive integer.") from exc

    if ttl <= 0:
        raise RuntimeError("TOKEN_TTL_SECONDS must be a positive integer.")

    app.config["TOKEN_TTL_SECONDS"] = ttl

    app.extensions["store"] = load_store()

    register_error_handlers(app)
    register_gate(app)
    app.register_blueprint(auth_bp)

    @app.get("/me")
    @require_role("ADMIN", "INSTRUCTOR", "STUDENT")
    def me() -> Response:
        return jsonify(
            id=g.actor["id"],
            email=g.actor["email"],
            role=g.actor["role"],
        )

    return app
