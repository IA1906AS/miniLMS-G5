from datetime import UTC, datetime

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from uv_demo.config import settings
from uv_demo.database import get_db
from uv_demo.models.assignment import Assignment, Submission
from uv_demo.models.course import Course, Enrollment
from uv_demo.models.user import User, UserRole
from uv_demo.schemas.assignment import (
    AssignmentCreate,
    AssignmentResponse,
    GradeSubmissionRequest,
    SubmissionResponse,
)
from uv_demo.security.audit import log_audit
from uv_demo.security.dependencies import (
    check_course_access,
    get_current_user,
    require_roles,
)
from uv_demo.services.storage import storage_service

router = APIRouter(tags=["4. Bài tập và Đánh giá"])


def _to_submission_response(sub: Submission) -> SubmissionResponse:
    return SubmissionResponse(
        id=sub.id,
        assignment_id=sub.assignment_id,
        student_id=sub.student_id,
        student_name=sub.student.full_name if sub.student else None,
        filename=sub.filename,
        submitted_at=sub.submitted_at,
        score=sub.score,
        feedback=sub.feedback,
        graded_at=sub.graded_at,
    )


# ---------------- Assignments ----------------


@router.post(
    "/api/courses/{course_id}/assignments",
    response_model=AssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_assignment(
    course_id: int,
    req: AssignmentCreate,
    current_user: User = Depends(require_roles(UserRole.GV, UserRole.QT)),
    db: Session = Depends(get_db),
) -> AssignmentResponse:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Khóa học không tồn tại."
        )

    # BẢO VỆ CHIA QUYỀN: Giảng viên chỉ được tạo bài tập cho khóa học do mình phụ trách
    if current_user.role == UserRole.GV and course.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền tạo bài tập cho khóa học do giảng viên khác phụ trách.",
        )

    assignment = Assignment(
        course_id=course.id,
        title=req.title.strip(),
        description=req.description,
        deadline=req.deadline,
        max_score=req.max_score,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    log_audit(
        db,
        action="CREATE_ASSIGNMENT",
        entity_type="ASSIGNMENT",
        user_id=current_user.id,
        entity_id=assignment.id,
        details=f"Tạo bài tập '{assignment.title}' cho khóa học {course.code}",
    )
    return AssignmentResponse.model_validate(assignment)


@router.get(
    "/api/courses/{course_id}/assignments", response_model=list[AssignmentResponse]
)
def list_assignments(
    course_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AssignmentResponse]:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Khóa học không tồn tại."
        )

    check_course_access(course, current_user, db)

    assignments = (
        db.query(Assignment)
        .filter(Assignment.course_id == course_id)
        .order_by(Assignment.created_at.desc())
        .all()
    )
    return [AssignmentResponse.model_validate(a) for a in assignments]


# ---------------- Submissions ----------------


@router.post(
    "/api/assignments/{assignment_id}/submit",
    response_model=SubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_assignment(
    assignment_id: int,
    file: UploadFile = File(...),
    current_user: User = Depends(require_roles(UserRole.SV)),
    db: Session = Depends(get_db),
) -> SubmissionResponse:
    """Sinh viên nộp bài làm trong thời hạn quy định."""
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bài tập không tồn tại."
        )

    # Kiểm tra sinh viên có ghi danh vào khóa học này không
    enrollment = (
        db.query(Enrollment)
        .filter(
            Enrollment.course_id == assignment.course_id,
            Enrollment.student_id == current_user.id,
        )
        .first()
    )
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn chưa ghi danh vào khóa học chứa bài tập này.",
        )

    # Kiểm tra thời hạn nộp bài
    now = datetime.now(UTC)
    assignment_deadline = (
        assignment.deadline
        if assignment.deadline.tzinfo
        else assignment.deadline.replace(tzinfo=UTC)
    )
    if now > assignment_deadline:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Đã hết hạn nộp bài cho bài tập này.",
        )

    original_filename, relative_path = await storage_service.save_upload_file(
        file=file,
        subfolder="submissions",
        allowed_extensions=settings.ALLOWED_SUBMISSION_EXTENSIONS,
    )

    # Nếu đã nộp trước đó thì cập nhật bài nộp mới nhất
    existing_sub = (
        db.query(Submission)
        .filter(
            Submission.assignment_id == assignment_id,
            Submission.student_id == current_user.id,
        )
        .first()
    )

    if existing_sub:
        existing_sub.filename = original_filename
        existing_sub.file_path = relative_path
        existing_sub.submitted_at = now
        sub = existing_sub
    else:
        sub = Submission(
            assignment_id=assignment_id,
            student_id=current_user.id,
            filename=original_filename,
            file_path=relative_path,
            submitted_at=now,
        )
        db.add(sub)

    db.commit()
    db.refresh(sub)

    log_audit(
        db,
        action="SUBMIT_ASSIGNMENT",
        entity_type="SUBMISSION",
        user_id=current_user.id,
        entity_id=sub.id,
        details=f"Sinh viên nộp bài làm '{sub.filename}' cho bài tập #{assignment_id}",
    )
    return _to_submission_response(sub)


@router.get(
    "/api/assignments/{assignment_id}/submissions",
    response_model=list[SubmissionResponse],
)
def get_assignment_submissions(
    assignment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SubmissionResponse]:
    """Truy xuất bài nộp:

    - Sinh viên CHỈ xem được bài nộp của bản thân (Chống leo thang đặc quyền ngang).
    - Giảng viên phụ trách hoặc QT xem được toàn bộ bài nộp của lớp.
    """
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bài tập không tồn tại."
        )

    course = db.query(Course).filter(Course.id == assignment.course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Khóa học không tồn tại."
        )

    if current_user.role == UserRole.SV:
        # Sinh viên CHỈ thấy bài của mình
        subs = (
            db.query(Submission)
            .filter(
                Submission.assignment_id == assignment_id,
                Submission.student_id == current_user.id,
            )
            .all()
        )
        return [_to_submission_response(s) for s in subs]

    if current_user.role == UserRole.GV:
        if course.instructor_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không phải giảng viên phụ trách khóa học này.",
            )

    # GV phụ trách hoặc QT xem được tất cả
    subs = (
        db.query(Submission)
        .filter(Submission.assignment_id == assignment_id)
        .order_by(Submission.submitted_at.desc())
        .all()
    )
    return [_to_submission_response(s) for s in subs]


@router.get("/api/submissions/{submission_id}/download")
def download_submission_file(
    submission_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bài nộp không tồn tại."
        )

    assignment = db.query(Assignment).filter(Assignment.id == sub.assignment_id).first()
    course = (
        db.query(Course).filter(Course.id == assignment.course_id).first()
        if assignment
        else None
    )

    # BẢO VỆ CHIA QUYỀN:
    # Sinh viên chỉ tải được bài của mình. Giảng viên chỉ tải được bài của lớp mình phụ trách.
    if current_user.role == UserRole.SV and sub.student_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền tải tệp bài làm của sinh viên khác.",
        )
    if (
        current_user.role == UserRole.GV
        and course
        and course.instructor_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền tải bài nộp của lớp khác.",
        )

    abs_path = storage_service.get_absolute_path(sub.file_path)
    return FileResponse(abs_path, filename=sub.filename)


@router.put("/api/submissions/{submission_id}/grade", response_model=SubmissionResponse)
def grade_submission(
    submission_id: int,
    req: GradeSubmissionRequest,
    current_user: User = Depends(require_roles(UserRole.GV, UserRole.QT)),
    db: Session = Depends(get_db),
) -> SubmissionResponse:
    """Giảng viên ghi nhận điểm số và nhận xét cho từng bài nộp."""
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bài nộp không tồn tại."
        )

    assignment = db.query(Assignment).filter(Assignment.id == sub.assignment_id).first()
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bài tập không tồn tại."
        )

    course = db.query(Course).filter(Course.id == assignment.course_id).first()
    if (
        current_user.role == UserRole.GV
        and course
        and course.instructor_id != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn chỉ có thể chấm điểm bài nộp của khóa học do mình phụ trách.",
        )

    if req.score > assignment.max_score:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Điểm số ({req.score}) không được vượt quá điểm tối đa ({assignment.max_score}).",
        )

    sub.score = req.score
    sub.feedback = req.feedback
    sub.graded_by_id = current_user.id
    sub.graded_at = datetime.now(UTC)
    db.commit()
    db.refresh(sub)

    log_audit(
        db,
        action="GRADE_SUBMISSION",
        entity_type="SUBMISSION",
        user_id=current_user.id,
        entity_id=sub.id,
        details=f"Chấm điểm bài nộp #{sub.id}: {req.score}/{assignment.max_score} điểm",
    )
    return _to_submission_response(sub)


@router.get("/api/my-grades", response_model=list[SubmissionResponse])
def get_my_grades(
    current_user: User = Depends(require_roles(UserRole.SV)),
    db: Session = Depends(get_db),
) -> list[SubmissionResponse]:
    """Sinh viên tra cứu điểm: Chỉ được xem kết quả học tập của chính mình."""
    subs = (
        db.query(Submission)
        .filter(Submission.student_id == current_user.id, Submission.score.isnot(None))
        .order_by(Submission.graded_at.desc())
        .all()
    )
    return [_to_submission_response(s) for s in subs]
