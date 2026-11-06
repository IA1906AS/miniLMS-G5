import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from uv_demo.config import settings
from uv_demo.database import get_db
from uv_demo.models.user import PasswordResetToken, User, UserRole
from uv_demo.schemas.auth import (
    LoginRequest,
    MessageResponse,
    PasswordChangeRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    RegisterRequest,
    TokenResponse,
)
from uv_demo.security.audit import log_audit
from uv_demo.security.dependencies import get_current_user, oauth2_scheme
from uv_demo.security.password import hash_password, verify_password
from uv_demo.security.ratelimit import login_rate_limiter
from uv_demo.security.token import create_access_token, revoke_token
from uv_demo.services.email import email_service

router = APIRouter(prefix="/api/auth", tags=["1. Quản lý tài khoản & Xác thực"])


@router.post(
    "/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED
)
def register(
    req: RegisterRequest, request: Request, db: Session = Depends(get_db)
) -> MessageResponse:
    existing = db.query(User).filter(User.email == req.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Địa chỉ email này đã được sử dụng trong hệ thống.",
        )

    # BẢO VỆ CHIA QUYỀN: Người dùng tự đăng ký LUÔN LUÔN là Sinh viên (SV).
    # Không thể tự gán quyền GV hoặc QT (Chặn triệt để leo thang đặc quyền dọc).
    user = User(
        email=req.email.lower(),
        hashed_password=hash_password(req.password),
        full_name=req.full_name.strip(),
        role=UserRole.SV,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    client_ip = request.client.host if request.client else None
    log_audit(
        db,
        action="REGISTER",
        entity_type="USER",
        user_id=user.id,
        entity_id=user.id,
        details=f"Sinh viên {user.email} đăng ký tài khoản thành công",
        ip_address=client_ip,
    )

    return MessageResponse(
        message="Đăng ký tài khoản thành công! Bạn có thể đăng nhập bằng email vừa tạo."
    )


# Dummy bcrypt hash dùng để đồng nhất thời gian phản hồi (chống Timing Attack / User Enumeration)
_DUMMY_BCRYPT_HASH = "$2b$12$e8Y/0W.7Ff/r1pE3P4J3OuM4v1L3wK6zZ6p9O8q2v7s5d3g1k9i2a"


@router.post("/login", response_model=TokenResponse)
def login(
    req: LoginRequest, request: Request, db: Session = Depends(get_db)
) -> TokenResponse:
    # 1. Chống Brute-force & DDoS bằng Rate Limiter
    login_rate_limiter.check(request)

    client_ip = request.client.host if request.client else None
    user = db.query(User).filter(User.email == req.email.lower()).first()

    # 2. Chống Timing Attack (CWE-208) & Lộ thông tin tài khoản (Information Disclosure):
    # Dù tài khoản có tồn tại hay không, vẫn thực hiện hash verify để thời gian tính toán là như nhau
    if user:
        is_password_valid = verify_password(req.password, user.hashed_password)
    else:
        verify_password(req.password, _DUMMY_BCRYPT_HASH)
        is_password_valid = False

    if not user or not is_password_valid:
        # Ghi nhận nhật ký đăng nhập thất bại phục vụ phát hiện xâm nhập
        log_audit(
            db,
            action="LOGIN_FAILED",
            entity_type="USER",
            user_id=user.id if user else None,
            entity_id=user.id if user else None,
            details=f"Đăng nhập thất bại đối với email: {req.email}",
            ip_address=client_ip,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email hoặc mật khẩu không chính xác.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản của bạn đã bị khóa. Vui lòng liên hệ Quản trị viên.",
        )

    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role.value}
    )

    log_audit(
        db,
        action="LOGIN",
        entity_type="USER",
        user_id=user.id,
        entity_id=user.id,
        details=f"Đăng nhập thành công với vai trò {user.role.value}",
        ip_address=client_ip,
    )

    return TokenResponse(
        access_token=access_token,
        role=user.role,
        user_id=user.id,
        full_name=user.full_name,
    )


@router.post("/token", response_model=TokenResponse, include_in_schema=False)
def login_for_swagger(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
) -> TokenResponse:
    """Hỗ trợ đăng nhập trực tiếp qua nút Authorize trên Swagger UI."""
    return login(
        LoginRequest(email=form_data.username, password=form_data.password),
        Request({"type": "http"}),
        db,
    )


@router.post("/logout", response_model=MessageResponse)
def logout(
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    revoke_token(token, db)
    log_audit(
        db,
        action="LOGOUT",
        entity_type="USER",
        user_id=current_user.id,
        entity_id=current_user.id,
        details="Người dùng đã đăng xuất và thu hồi phiên làm việc trên máy chủ",
    )
    return MessageResponse(message="Đăng xuất thành công! Phiên làm việc đã bị hủy.")


@router.post("/password-reset/request", response_model=MessageResponse)
def request_password_reset(
    req: PasswordResetRequest, db: Session = Depends(get_db)
) -> MessageResponse:
    user = db.query(User).filter(User.email == req.email.lower()).first()
    # Để tránh enumeration email, luôn trả về thông điệp thành công chung
    if user and user.is_active:
        token_str = secrets.token_urlsafe(32)
        expire_at = datetime.now(UTC) + timedelta(
            minutes=settings.RESET_TOKEN_EXPIRE_MINUTES
        )
        reset_token = PasswordResetToken(
            user_id=user.id, token=token_str, expires_at=expire_at
        )
        db.add(reset_token)
        db.commit()

        email_service.send_password_reset_email(user.email, token_str)
        log_audit(
            db,
            action="REQUEST_PASSWORD_RESET",
            entity_type="USER",
            user_id=user.id,
            entity_id=user.id,
            details=f"Yêu cầu đặt lại mật khẩu cho {user.email}",
        )

    return MessageResponse(
        message="Nếu email tồn tại trong hệ thống, liên kết đặt lại mật khẩu đã được gửi tới hộp thư của bạn."
    )


@router.post("/password-reset/confirm", response_model=MessageResponse)
def confirm_password_reset(
    req: PasswordResetConfirm, db: Session = Depends(get_db)
) -> MessageResponse:
    now = datetime.now(UTC)
    token_entry = (
        db.query(PasswordResetToken)
        .filter(
            PasswordResetToken.token == req.token,
            PasswordResetToken.is_used.is_(False),
            PasswordResetToken.expires_at > now,
        )
        .first()
    )
    if not token_entry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mã khôi phục mật khẩu không hợp lệ hoặc đã hết hạn.",
        )

    user = db.query(User).filter(User.id == token_entry.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Người dùng không tồn tại."
        )

    user.hashed_password = hash_password(req.new_password)
    token_entry.is_used = True
    db.commit()

    log_audit(
        db,
        action="RESET_PASSWORD",
        entity_type="USER",
        user_id=user.id,
        entity_id=user.id,
        details="Đặt lại mật khẩu mới thành công qua email",
    )
    return MessageResponse(
        message="Mật khẩu của bạn đã được cập nhật thành công. Vui lòng đăng nhập lại."
    )


@router.post("/password-change", response_model=MessageResponse)
def change_password(
    req: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    if not verify_password(req.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mật khẩu hiện tại không chính xác.",
        )

    current_user.hashed_password = hash_password(req.new_password)
    db.commit()

    log_audit(
        db,
        action="CHANGE_PASSWORD",
        entity_type="USER",
        user_id=current_user.id,
        entity_id=current_user.id,
        details="Người dùng đổi mật khẩu thành công",
    )
    return MessageResponse(message="Đổi mật khẩu thành công!")
