from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from uv_demo.database import get_db
from uv_demo.models.course import Course
from uv_demo.models.user import AuditLog, User, UserRole
from uv_demo.schemas.admin import (
    AuditLogResponse,
    UserAdminLock,
    UserAdminUpdateRole,
)
from uv_demo.schemas.auth import MessageResponse
from uv_demo.schemas.course import CourseResponse
from uv_demo.schemas.user import UserProfileResponse
from uv_demo.security.audit import log_audit
from uv_demo.security.dependencies import require_roles

router = APIRouter(
    prefix="/api/admin",
    tags=["7. Quản trị hệ thống (Chỉ dành cho QT)"],
    dependencies=[Depends(require_roles(UserRole.QT))],
)


# ---------------- Quản lý người dùng ----------------


@router.get("/users", response_model=list[UserProfileResponse])
def admin_list_users(
    search: str | None = Query(None, description="Tìm theo tên hoặc email"),
    role: UserRole | None = Query(None, description="Lọc theo vai trò"),
    db: Session = Depends(get_db),
) -> list[UserProfileResponse]:
    query = db.query(User)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            (User.email.ilike(pattern)) | (User.full_name.ilike(pattern))
        )
    if role:
        query = query.filter(User.role == role)

    users = query.order_by(User.id.asc()).all()
    return [UserProfileResponse.model_validate(u) for u in users]


@router.put("/users/{user_id}/role", response_model=UserProfileResponse)
def admin_change_user_role(
    user_id: int,
    req: UserAdminUpdateRole,
    current_admin: User = Depends(require_roles(UserRole.QT)),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    """Thay đổi vai trò người dùng (SV <-> GV <-> QT).

    CHỈ Quản trị viên (QT) mới có quyền thực thi.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Người dùng không tồn tại."
        )

    old_role = user.role.value
    user.role = req.role
    db.commit()
    db.refresh(user)

    log_audit(
        db,
        action="CHANGE_USER_ROLE",
        entity_type="USER",
        user_id=current_admin.id,
        entity_id=user.id,
        details=f"Thay đổi vai trò của {user.email} từ {old_role} sang {req.role.value}",
    )
    return UserProfileResponse.model_validate(user)


@router.put("/users/{user_id}/lock", response_model=UserProfileResponse)
def admin_lock_user(
    user_id: int,
    req: UserAdminLock,
    current_admin: User = Depends(require_roles(UserRole.QT)),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    """Khóa hoặc mở khóa tài khoản người dùng."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Người dùng không tồn tại."
        )

    if user.id == current_admin.id and not req.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quản trị viên không thể tự khóa tài khoản của chính mình.",
        )

    user.is_active = req.is_active
    db.commit()
    db.refresh(user)

    action_name = "LOCK_USER" if not req.is_active else "UNLOCK_USER"
    log_audit(
        db,
        action=action_name,
        entity_type="USER",
        user_id=current_admin.id,
        entity_id=user.id,
        details=f"Trạng thái hoạt động của {user.email} được đặt thành: is_active={req.is_active}",
    )
    return UserProfileResponse.model_validate(user)


# ---------------- Quản lý khóa học ----------------


@router.get("/courses", response_model=list[CourseResponse])
def admin_list_all_courses(db: Session = Depends(get_db)) -> list[CourseResponse]:
    courses = db.query(Course).order_by(Course.created_at.desc()).all()
    return [
        CourseResponse(
            id=c.id,
            code=c.code,
            title=c.title,
            description=c.description,
            instructor_id=c.instructor_id,
            instructor_name=c.instructor.full_name if c.instructor else None,
            is_active=c.is_active,
            created_at=c.created_at,
        )
        for c in courses
    ]


@router.delete("/courses/{course_id}", response_model=MessageResponse)
def admin_remove_course(
    course_id: int,
    current_admin: User = Depends(require_roles(UserRole.QT)),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Gỡ bỏ khóa học trên toàn hệ thống."""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Khóa học không tồn tại."
        )

    code = course.code
    db.delete(course)
    db.commit()

    log_audit(
        db,
        action="DELETE_COURSE",
        entity_type="COURSE",
        user_id=current_admin.id,
        entity_id=course_id,
        details=f"Quản trị viên đã xóa khóa học {code} khỏi hệ thống",
    )
    return MessageResponse(message=f"Đã gỡ bỏ khóa học {code} thành công.")


# ---------------- Nhật ký hoạt động (Audit log) ----------------


@router.get("/audit-logs", response_model=list[AuditLogResponse])
def admin_get_audit_logs(
    action: str | None = Query(None, description="Lọc theo hành động"),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[AuditLogResponse]:
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action.strip().upper())

    logs = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return [AuditLogResponse.model_validate(item) for item in logs]
