import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from uv_demo.config import settings
from uv_demo.models.assignment import Assignment, IdempotencyRecord, Submission
from uv_demo.models.user import User
from uv_demo.schemas.assignment import SubmissionResponse
from uv_demo.security.audit import log_audit
from uv_demo.services.storage import storage_service

IDEMPOTENCY_TTL_HOURS = 24
MAX_IDEMPOTENCY_KEY_LENGTH = 128


def normalize_idempotency_key(raw_key: str | None) -> str | None:
    """Chuẩn hóa và kiểm tra tính hợp lệ của Idempotency-Key từ header."""
    if raw_key is None:
        return None
    cleaned = raw_key.strip()
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Header Idempotency-Key không được để trống.",
        )
    if len(cleaned) > MAX_IDEMPOTENCY_KEY_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Header Idempotency-Key vượt quá độ dài tối đa "
                f"({MAX_IDEMPOTENCY_KEY_LENGTH} ký tự)."
            ),
        )
    return cleaned


def compute_submission_fingerprint(
    assignment_id: int, filename: str, content: bytes
) -> str:
    """Tạo mã băm SHA-256 đại diện cho nội dung yêu cầu nộp bài."""
    safe_name = Path(filename).name if filename else ""
    hasher = hashlib.sha256()
    hasher.update(f"{assignment_id}:{safe_name}:".encode())
    hasher.update(content)
    return hasher.hexdigest()


def _ensure_aware_utc(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def acquire_idempotency_slot(
    db: Session,
    *,
    user_id: int,
    assignment_id: int,
    idempotency_key: str,
    request_hash: str,
    ttl_hours: int = IDEMPOTENCY_TTL_HOURS,
) -> tuple[SubmissionResponse | None, IdempotencyRecord | None]:
    """Kiểm tra khóa Idempotency hoặc tạo khóa PROCESSING mới.

    Trả về:
    - `(cached_response, None)` nếu yêu cầu đã từng hoàn tất trước đó với cùng payload.
    - `(None, record)` nếu đây là yêu cầu mới và đã giữ khóa thành công.
    """
    now = datetime.now(UTC)
    existing = (
        db.query(IdempotencyRecord)
        .filter(
            IdempotencyRecord.user_id == user_id,
            IdempotencyRecord.idempotency_key == idempotency_key,
        )
        .first()
    )

    if existing is not None:
        if _ensure_aware_utc(existing.expires_at) <= now:
            db.delete(existing)
            db.flush()
        else:
            if (
                existing.assignment_id != assignment_id
                or existing.request_hash != request_hash
            ):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail=(
                        "Idempotency-Key đã được sử dụng cho một tệp bài làm "
                        "hoặc bài tập khác."
                    ),
                )
            if existing.status != "COMPLETED" or not existing.response_body:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Yêu cầu nộp bài với Idempotency-Key này đang được xử lý, "
                        "vui lòng không gửi lặp."
                    ),
                )
            cached = SubmissionResponse.model_validate_json(existing.response_body)
            return cached, None

    record = IdempotencyRecord(
        idempotency_key=idempotency_key,
        user_id=user_id,
        assignment_id=assignment_id,
        request_hash=request_hash,
        status="PROCESSING",
        created_at=now,
        expires_at=now + timedelta(hours=ttl_hours),
    )
    try:
        with db.begin_nested():
            db.add(record)
            db.flush()
    except IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Yêu cầu nộp bài với Idempotency-Key này đang được xử lý đồng thời."
            ),
        ) from exc

    return None, record


def complete_idempotency_slot(
    record: IdempotencyRecord | None, response: SubmissionResponse
) -> None:
    """Đánh dấu bản ghi Idempotency đã hoàn tất và lưu lại kết quả phản hồi."""
    if record is None:
        return
    record.status = "COMPLETED"
    record.response_body = response.model_dump_json()


async def submit_assignment_idempotent(
    *,
    db: Session,
    assignment: Assignment,
    current_user: User,
    file: UploadFile,
    raw_idempotency_key: str | None,
) -> SubmissionResponse:
    """Thực thi nộp bài tập bảo vệ bởi Idempotency Key Pattern."""
    idem_key = normalize_idempotency_key(raw_idempotency_key)
    record: IdempotencyRecord | None = None

    if idem_key is not None:
        content = await file.read()
        await file.seek(0)
        fingerprint = compute_submission_fingerprint(
            assignment_id=assignment.id,
            filename=file.filename or "",
            content=content,
        )
        cached_response, record = acquire_idempotency_slot(
            db,
            user_id=current_user.id,
            assignment_id=assignment.id,
            idempotency_key=idem_key,
            request_hash=fingerprint,
        )
        if cached_response is not None:
            return cached_response

    now = datetime.now(UTC)
    if now > _ensure_aware_utc(assignment.deadline):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Đã hết hạn nộp bài cho bài tập này.",
        )

    original_filename, relative_path = await storage_service.save_upload_file(
        file=file,
        subfolder="submissions",
        allowed_extensions=settings.ALLOWED_SUBMISSION_EXTENSIONS,
    )

    existing_sub = (
        db.query(Submission)
        .filter(
            Submission.assignment_id == assignment.id,
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
            assignment_id=assignment.id,
            student_id=current_user.id,
            filename=original_filename,
            file_path=relative_path,
            submitted_at=now,
        )
        db.add(sub)

    db.flush()
    response = SubmissionResponse(
        id=sub.id,
        assignment_id=sub.assignment_id,
        student_id=sub.student_id,
        student_name=current_user.full_name,
        filename=sub.filename,
        submitted_at=sub.submitted_at,
        score=sub.score,
        feedback=sub.feedback,
        graded_at=sub.graded_at,
    )
    complete_idempotency_slot(record, response)
    db.commit()
    db.refresh(sub)

    log_audit(
        db,
        action="SUBMIT_ASSIGNMENT",
        entity_type="SUBMISSION",
        user_id=current_user.id,
        entity_id=sub.id,
        details=f"Sinh viên nộp bài làm '{sub.filename}' cho bài tập #{assignment.id}",
    )
    return response
