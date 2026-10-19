"""Application errors and their JSON responses."""

from flask import Flask, Response, jsonify


class AppError(Exception):
    status_code = 500
    code = "INTERNAL_ERROR"


class ValidationError(AppError):
    status_code = 400
    code = "VALIDATION_ERROR"


class InvalidCredentialsError(AppError):
    status_code = 401
    code = "INVALID_CREDENTIALS"


class UnauthenticatedError(AppError):
    status_code = 401
    code = "UNAUTHENTICATED"


class Forbidden(AppError):  # noqa: N818 - Required by the assignment.
    status_code = 403
    code = "FORBIDDEN"


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(AppError)
    def handle_app_error(error: AppError) -> tuple[Response, int]:
        return jsonify(error=error.code), error.status_code
