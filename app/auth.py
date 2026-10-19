"""Password helpers, JWT creation, and login."""

import time

import bcrypt
import jwt
from flask import Blueprint, Response, current_app, jsonify, request

from app.errors import InvalidCredentialsError, UnauthenticatedError
from app.schemas import validate_login_body

auth_bp = Blueprint("auth", __name__)


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    password_hash = bcrypt.hashpw(password_bytes, salt)
    return password_hash.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except ValueError:
        return False


def create_access_token(user_id: str, secret: str, ttl: int) -> str:
    now = int(time.time())
    return jwt.encode(
        {"sub": user_id, "iat": now, "exp": now + ttl},
        secret,
        algorithm="HS256",
    )


def verify_access_token(token: str, secret: str) -> str:
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"require": ["sub", "iat", "exp"]},
        )
    except (jwt.InvalidTokenError, TypeError, ValueError) as exc:
        raise UnauthenticatedError() from exc

    user_id = payload["sub"]

    if not isinstance(user_id, str) or not user_id:
        raise UnauthenticatedError()

    return user_id


@auth_bp.post("/auth/login")
def login() -> Response:
    email, password = validate_login_body(request.get_json(silent=True))
    users = current_app.extensions["store"]["users"]
    user = next(
        (user for user in users.values() if user["email"] == email),
        None,
    )

    if user is None or not verify_password(password, user["password_hash"]):
        raise InvalidCredentialsError()

    ttl = current_app.config["TOKEN_TTL_SECONDS"]
    token = create_access_token(
        user["id"],
        current_app.config["JWT_SECRET"],
        ttl,
    )
    return jsonify(accessToken=token, expiresIn=ttl)
