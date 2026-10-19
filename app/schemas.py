"""Validate request bodies."""

from app.errors import ValidationError


def validate_login_body(body: object) -> tuple[str, str]:
    if not isinstance(body, dict) or set(body) != {"email", "password"}:
        raise ValidationError()

    email = body["email"]
    password = body["password"]

    if not isinstance(email, str) or not isinstance(password, str):
        raise ValidationError()

    return email, password
