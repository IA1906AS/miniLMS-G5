from collections.abc import Callable
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from uv_demo.database import get_db
from uv_demo.models.course import Course, Enrollment
from uv_demo.models.user import User, UserRole
from uv_demo.security.token import decode_access_token, is_token_revoked

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    if is_token_revoked(token, db):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Phiên làm việc đã bị thu hồi/đăng xuất.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    user_id_raw = payload.get("sub")
    if user_id_raw is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không chứa thông tin định danh.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(user_id_raw)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Thông tin định danh không hợp lệ.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Người dùng không tồn tại.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tài khoản của bạn đã bị khóa bởi Quản trị viên.",
        )

    return user


def require_roles(*allowed_roles: UserRole) -> Callable[[User], User]:
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            allowed_str = ", ".join(r.value for r in allowed_roles)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Bạn không có quyền thực hiện thao tác này. "
                    f"Quyền hiện tại: {current_user.role.value}, yêu cầu: [{allowed_str}]."
                ),
            )
        return current_user

    return role_checker


def check_course_access(
    course: Course, current_user: User, db: Session
) -> dict[str, Any]:
    """Kiểm tra quyền truy cập khóa học để ngăn chặn leo thang đặc quyền ngang.

    - QT: Toàn quyền truy cập mọi khóa học.
    - GV: Chỉ có quyền quản lý khóa học do mình phụ trách (instructor_id).
    - SV: Chỉ có quyền đọc khóa học nếu đã ghi danh (enrolled).
    """
    if current_user.role == UserRole.QT:
        return {"is_admin": True, "is_instructor": True, "is_enrolled": True}

    if current_user.role == UserRole.GV:
        if course.instructor_id == current_user.id:
            return {"is_admin": False, "is_instructor": True, "is_enrolled": True}
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không phải giảng viên phụ trách khóa học này.",
        )

    # Sinh viên (SV)
    enrollment = (
        db.query(Enrollment)
        .filter(
            Enrollment.course_id == course.id, Enrollment.student_id == current_user.id
        )
        .first()
    )
    if enrollment is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn chưa ghi danh vào khóa học này.",
        )

    return {"is_admin": False, "is_instructor": False, "is_enrolled": True}
