from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from uv_demo.config import settings
from uv_demo.database import get_db
from uv_demo.models.course import Course, Enrollment
from uv_demo.models.user import User
from uv_demo.schemas.auth import MessageResponse
from uv_demo.schemas.user import (
    PublicMemberProfile,
    UserProfileResponse,
    UserProfileUpdate,
)
from uv_demo.security.dependencies import check_course_access, get_current_user
from uv_demo.services.storage import storage_service

router = APIRouter(prefix="/api/users", tags=["2. Hồ sơ người dùng"])


@router.get("/me", response_model=UserProfileResponse)
def get_my_profile(
    current_user: User = Depends(get_current_user),
) -> UserProfileResponse:
    return UserProfileResponse.model_validate(current_user)


@router.put("/me", response_model=UserProfileResponse)
def update_my_profile(
    update_data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserProfileResponse:
    # BẢO VỆ CHIA QUYỀN: Người dùng chỉ được sửa thông tin cá nhân của chính mình.
    # Không thể cập nhật id, email, role hay is_active tại đây.
    if update_data.full_name is not None:
        current_user.full_name = update_data.full_name.strip()
    if update_data.bio is not None:
        current_user.bio = update_data.bio
    if update_data.contact_info is not None:
        current_user.contact_info = update_data.contact_info

    db.commit()
    db.refresh(current_user)
    return UserProfileResponse.model_validate(current_user)


@router.post("/me/avatar", response_model=MessageResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    _, relative_path = await storage_service.save_upload_file(
        file=file,
        subfolder="avatars",
        allowed_extensions=settings.ALLOWED_AVATAR_EXTENSIONS,
    )
    current_user.avatar_url = f"/api/users/avatar/{current_user.id}"
    # Lưu relative path nội bộ
    current_user.contact_info = (
        current_user.contact_info or ""
    )  # keep contact_info if needed
    db.commit()
    return MessageResponse(message="Tải lên ảnh đại diện thành công!")


@router.get("/avatar/{user_id}")
def get_user_avatar(user_id: int, db: Session = Depends(get_db)) -> FileResponse:
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.avatar_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Người dùng chưa thiết lập ảnh đại diện.",
        )
    # Tìm tệp trong thư mục avatars
    avatar_dir = settings.UPLOAD_DIR / "avatars"
    if not avatar_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy tệp ảnh đại diện.",
        )

    for item in avatar_dir.iterdir():
        if item.is_file():
            return FileResponse(item)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy tệp ảnh đại diện."
    )


@router.get("/members/course/{course_id}", response_model=list[PublicMemberProfile])
def get_course_members(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[PublicMemberProfile]:
    """Xem hồ sơ công khai của các thành viên cùng khoá học.

    BẢO VỆ CHIA QUYỀN: Chỉ thành viên đã ghi danh, giảng viên khóa học hoặc QT
    mới được phép xem danh sách lớp (chống leo thang đặc quyền ngang / rò rỉ dữ liệu).
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Khóa học không tồn tại."
        )

    # Xác thực quyền truy cập khóa học
    check_course_access(course, current_user, db)

    # Lấy giảng viên
    members: list[PublicMemberProfile] = []
    if course.instructor:
        members.append(PublicMemberProfile.model_validate(course.instructor))

    # Lấy các sinh viên đã ghi danh
    enrollments = db.query(Enrollment).filter(Enrollment.course_id == course_id).all()
    for en in enrollments:
        if en.student and en.student.id != course.instructor_id:
            members.append(PublicMemberProfile.model_validate(en.student))

    return members
