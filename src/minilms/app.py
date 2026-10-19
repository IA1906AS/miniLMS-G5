"""Entry point for the Mini LMS web application."""

from flask import Flask, Response, jsonify


def create_app() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)

    @app.get("/")
    def index() -> Response:
        return jsonify(
            name="Mini LMS",
            message="Chào mừng đến với hệ thống quản lý học tập.",
        )

    return app


app = create_app()
