import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from uv_demo.config import settings
from uv_demo.models.user import TokenBlacklist


def create_access_token(
    data: dict[str, Any], expires_delta: timedelta | None = None
) -> str:
    to_encode = data.copy()
    now = datetime.now(UTC)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update(
        {
            "exp": expire,
            "iat": now,
            "jti": str(uuid.uuid4()),  # unique JWT identifier for revocation
        }
    )
    encoded_jwt: str = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload: dict[str, Any] = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên làm việc đã hết hạn. Vui lòng đăng nhập lại.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mã token không hợp lệ.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None


def is_token_revoked(token: str, db: Session) -> bool:
    revoked = db.query(TokenBlacklist).filter(TokenBlacklist.token == token).first()
    return revoked is not None


def revoke_token(token: str, db: Session) -> None:
    if not is_token_revoked(token, db):
        entry = TokenBlacklist(token=token)
        db.add(entry)
        db.commit()
