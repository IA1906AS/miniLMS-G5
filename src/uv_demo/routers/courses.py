from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from uv_demo.config import settings
from uv_demo.database import get_db
from uv_demo.models.course import Course, Enrollment, Material
from uv_demo.models.user import User, UserRole
from uv_demo.schemas.auth import MessageResponse
from uv_demo.schemas.course import (
    CourseCreate,
    CourseResponse,
    CourseUpdate,
    EnrollmentCreate,
    EnrollStudentByInstructor,
    MaterialResponse,
)
from uv_demo.security.audit import log_audit
from uv_demo.security.dependencies import (
    check_course_access,
    get_current_user,
    require_roles,
)
from uv_demo.services.storage import storage_service

router = APIRouter(prefix="/api/courses", tags=["3. Quản lý khoá học"])


def _to_course_response(
    course: Course, user: User | None = None, db: Session | None = None
) -> CourseResponse:
    enrolled = True
    if user and db:
        if user.role == UserRole.QT or (
            user.role == UserRole.GV and course.instructor_id == user.id
        ):
            enrolled = True
        else:
            enrolled = (
                db.query(Enrollment)
                .filter(
                    Enrollment.course_id == course.id,
                    Enrollment.student_id == user.id,
                )
                .first()
                is not None
            )
    return CourseResponse(
        id=course.id,
        code=course.code,
        title=course.title,
        description=course.description,
        instructor_id=course.instructor_id,
        instructor_name=course.instructor.full_name if course.instructor else None,
        is_active=course.is_active,
        is_enrolled=enrolled,
        created_at=course.created_at,
    )


def _get_course_or_404(db: Session, course_id: int) -> Course:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Khóa học không tồn tại."
        )
    return course


def _require_course_instructor(course: Course, user: User, detail: str) -> None:
    if user.role == UserRole.GV and course.instructor_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


@router.get("", response_model=list[CourseResponse])
def list_and_search_courses(
    search: str | None = Query(None, description="Tìm kiếm theo tên khóa học hoặc mã"),
    instructor_name: str | None = Query(None, description="Lọc theo tên giảng viên"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[CourseResponse]:
    query = db.query(Course).filter(Course.is_active.is_(True))
    if search:
        search_filter = f"%{search.strip()}%"
        query = query.filter(
            (Course.title.ilike(search_filter)) | (Course.code.ilike(search_filter))
        )
    if instructor_name:
        query = query.join(Course.instructor).filter(
            User.full_name.ilike(f"%{instructor_name.strip()}%")
        )
    courses = query.order_by(Course.created_at.desc()).all()
    return [_to_course_response(c, current_user, db) for c in courses]


@router.get("/{course_id}", response_model=CourseResponse)
def get_course_detail(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CourseResponse:
    return _to_course_response(_get_course_or_404(db, course_id), current_user, db)


@router.post("", response_model=CourseResponse, status_code=status.HTTP_201_CREATED)
def create_course(
    req: CourseCreate,
    current_user: User = Depends(require_roles(UserRole.GV, UserRole.QT)),
    db: Session = Depends(get_db),
) -> CourseResponse:
    # BẢO VỆ CHIA QUYỀN: Chỉ Giảng viên (GV) hoặc Quản trị viên (QT) mới được tạo khóa học.
    existing = db.query(Course).filter(Course.code == req.code.strip().upper()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Mã khóa học '{req.code}' đã tồn tại trong hệ thống.",
        )

    course = Course(
        code=req.code.strip().upper(),
        title=req.title.strip(),
        description=req.description,
        instructor_id=current_user.id,
        is_active=True,
    )
    db.add(course)
    db.commit()
    db.refresh(course)

    log_audit(
        db,
        action="CREATE_COURSE",
        entity_type="COURSE",
        user_id=current_user.id,
        entity_id=course.id,
        details=f"Khởi tạo khóa học {course.code} - {course.title}",
    )
    return _to_course_response(course)


@router.put("/{course_id}", response_model=CourseResponse)
def update_course(
    course_id: int,
    req: CourseUpdate,
    current_user: User = Depends(require_roles(UserRole.GV, UserRole.QT)),
    db: Session = Depends(get_db),
) -> CourseResponse:
    course = _get_course_or_404(db, course_id)
    _require_course_instructor(
        course,
        current_user,
        "Bạn không có quyền chỉnh sửa khóa học do giảng viên khác phụ trách.",
    )
    if req.title is not None:
        course.title = req.title.strip()
    if req.description is not None:
        course.description = req.description

    db.commit()
    db.refresh(course)
    log_audit(
        db,
        action="UPDATE_COURSE",
        entity_type="COURSE",
        user_id=current_user.id,
        entity_id=course.id,
        details=f"Cập nhật thông tin khóa học {course.code}",
    )
    return _to_course_response(course)


@router.post("/enroll", response_model=MessageResponse)
def student_self_enroll(
    req: EnrollmentCreate,
    current_user: User = Depends(require_roles(UserRole.SV)),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Sinh viên ghi danh vào khóa học bằng mã khóa học."""
    course = (
        db.query(Course)
        .filter(
            Course.code == req.course_code.strip().upper(), Course.is_active.is_(True)
        )
        .first()
    )
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy khóa học với mã '{req.course_code}'.",
        )

    existing = (
        db.query(Enrollment)
        .filter(
            Enrollment.course_id == course.id, Enrollment.student_id == current_user.id
        )
        .first()
    )
    if existing:
        return MessageResponse(message="Bạn đã ghi danh vào khóa học này từ trước.")

    db.add(Enrollment(course_id=course.id, student_id=current_user.id))
    db.commit()
    log_audit(
        db,
        action="ENROLL_STUDENT",
        entity_type="COURSE",
        user_id=current_user.id,
        entity_id=course.id,
        details=f"Sinh viên {current_user.email} tự ghi danh vào khóa học {course.code}",
    )
    return MessageResponse(
        message=f"Ghi danh thành công vào khóa học: {course.code} - {course.title}!"
    )


@router.post("/{course_id}/enroll-student", response_model=MessageResponse)
def instructor_add_student(
    course_id: int,
    req: EnrollStudentByInstructor,
    current_user: User = Depends(require_roles(UserRole.GV, UserRole.QT)),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Giảng viên bổ sung sinh viên vào danh sách lớp."""
    course = _get_course_or_404(db, course_id)
    _require_course_instructor(
        course,
        current_user,
        "Bạn không có quyền quản lý danh sách lớp của khóa học này.",
    )
    student = db.query(User).filter(User.email == req.student_email.lower()).first()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy sinh viên có email {req.student_email}.",
        )
    if student.role != UserRole.SV:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chỉ có thể ghi danh người dùng có vai trò là Sinh viên (SV).",
        )

    existing = (
        db.query(Enrollment)
        .filter(Enrollment.course_id == course.id, Enrollment.student_id == student.id)
        .first()
    )
    if existing:
        return MessageResponse(message="Sinh viên này đã có trong danh sách lớp.")

    db.add(Enrollment(course_id=course.id, student_id=student.id))
    db.commit()
    log_audit(
        db,
        action="INSTRUCTOR_ADD_STUDENT",
        entity_type="COURSE",
        user_id=current_user.id,
        entity_id=course.id,
        details=f"Thêm sinh viên {student.email} vào lớp {course.code}",
    )
    return MessageResponse(
        message=f"Đã thêm sinh viên {student.full_name} vào lớp thành công."
    )


@router.post("/{course_id}/materials", response_model=MaterialResponse)
async def upload_course_material(
    course_id: int,
    title: str = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(require_roles(UserRole.GV, UserRole.QT)),
    db: Session = Depends(get_db),
) -> MaterialResponse:
    course = _get_course_or_404(db, course_id)
    _require_course_instructor(
        course,
        current_user,
        "Bạn chỉ có thể tải lên tài liệu cho khóa học do mình phụ trách.",
    )
    original_name, relative_path = await storage_service.save_upload_file(
        file=file,
        subfolder="materials",
        allowed_extensions=settings.ALLOWED_MATERIAL_EXTENSIONS,
    )
    material = Material(
        course_id=course.id,
        title=title.strip(),
        filename=original_name,
        file_path=relative_path,
        uploaded_by_id=current_user.id,
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    log_audit(
        db,
        action="UPLOAD_MATERIAL",
        entity_type="MATERIAL",
        user_id=current_user.id,
        entity_id=material.id,
        details=f"Tải lên tài liệu '{material.title}' cho khóa học {course.code}",
    )
    return MaterialResponse.model_validate(material)


@router.get("/{course_id}/materials", response_model=list[MaterialResponse])
def list_course_materials(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MaterialResponse]:
    course = _get_course_or_404(db, course_id)
    check_course_access(course, current_user, db)
    materials = (
        db.query(Material)
        .filter(Material.course_id == course_id)
        .order_by(Material.created_at.desc())
        .all()
    )
    return [MaterialResponse.model_validate(m) for m in materials]


@router.get("/materials/{material_id}/download")
def download_course_material(
    material_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    material = db.query(Material).filter(Material.id == material_id).first()
    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Tài liệu không tồn tại."
        )
    course = _get_course_or_404(db, material.course_id)
    check_course_access(course, current_user, db)
    abs_path = storage_service.get_absolute_path(material.file_path)
    return FileResponse(abs_path, filename=material.filename)
