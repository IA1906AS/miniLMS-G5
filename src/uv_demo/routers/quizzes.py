from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from uv_demo.database import get_db
from uv_demo.models.course import Course, Enrollment
from uv_demo.models.quiz import (
    Quiz,
    QuizAnswer,
    QuizAttempt,
    QuizOption,
    QuizQuestion,
)
from uv_demo.models.user import User, UserRole
from uv_demo.schemas.auth import MessageResponse
from uv_demo.schemas.quiz import (
    QuizAttemptResponse,
    QuizCreate,
    QuizOptionStudentOut,
    QuizQuestionStudentOut,
    QuizStudentDetailOut,
    QuizSubmitRequest,
)
from uv_demo.security.audit import log_audit
from uv_demo.security.dependencies import (
    check_course_access,
    get_current_user,
    require_roles,
)

router = APIRouter(tags=["5. Bài kiểm tra trắc nghiệm"])


@router.post(
    "/api/courses/{course_id}/quizzes",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_quiz(
    course_id: int,
    req: QuizCreate,
    current_user: User = Depends(require_roles(UserRole.GV, UserRole.QT)),
    db: Session = Depends(get_db),
) -> MessageResponse:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Khóa học không tồn tại."
        )

    if current_user.role == UserRole.GV and course.instructor_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn chỉ có thể tạo bài kiểm tra cho khóa học do mình phụ trách.",
        )

    quiz = Quiz(
        course_id=course.id,
        title=req.title.strip(),
        description=req.description,
        time_limit_minutes=req.time_limit_minutes,
        max_attempts=req.max_attempts,
    )
    db.add(quiz)
    db.flush()

    for q_data in req.questions:
        # Kiểm tra xem có ít nhất 1 đáp án đúng
        has_correct = any(opt.is_correct for opt in q_data.options)
        if not has_correct:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Câu hỏi '{q_data.content}' phải có ít nhất 1 đáp án đúng.",
            )

        q = QuizQuestion(quiz_id=quiz.id, content=q_data.content, points=q_data.points)
        db.add(q)
        db.flush()

        for opt_data in q_data.options:
            opt = QuizOption(
                question_id=q.id,
                content=opt_data.content,
                is_correct=opt_data.is_correct,
            )
            db.add(opt)

    db.commit()

    log_audit(
        db,
        action="CREATE_QUIZ",
        entity_type="QUIZ",
        user_id=current_user.id,
        entity_id=quiz.id,
        details=f"Tạo bài trắc nghiệm '{quiz.title}' với {len(req.questions)} câu hỏi",
    )
    return MessageResponse(
        message=f"Tạo bài kiểm tra trắc nghiệm '{quiz.title}' thành công!"
    )


@router.get("/api/quizzes/{quiz_id}", response_model=QuizStudentDetailOut)
def get_quiz_for_taking(
    quiz_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> QuizStudentDetailOut:
    """Lấy nội dung bài kiểm tra để làm bài.

    LƯU Ý BẢO MẬT & CHỐNG GIAN LẬN:
    Đáp án đúng (is_correct) TUYỆT ĐỐI KHÔNG được gửi về client.
    """
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bài kiểm tra không tồn tại."
        )

    course = db.query(Course).filter(Course.id == quiz.course_id).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Khóa học không tồn tại."
        )

    check_course_access(course, current_user, db)

    questions_out: list[QuizQuestionStudentOut] = []
    for q in quiz.questions:
        options_out = [
            QuizOptionStudentOut(id=opt.id, content=opt.content) for opt in q.options
        ]
        questions_out.append(
            QuizQuestionStudentOut(
                id=q.id,
                content=q.content,
                points=q.points,
                options=options_out,
            )
        )

    return QuizStudentDetailOut(
        id=quiz.id,
        course_id=quiz.course_id,
        title=quiz.title,
        description=quiz.description,
        time_limit_minutes=quiz.time_limit_minutes,
        max_attempts=quiz.max_attempts,
        questions=questions_out,
    )


@router.post("/api/quizzes/{quiz_id}/submit", response_model=QuizAttemptResponse)
def submit_quiz_and_auto_grade(
    quiz_id: int,
    req: QuizSubmitRequest,
    current_user: User = Depends(require_roles(UserRole.SV)),
    db: Session = Depends(get_db),
) -> QuizAttemptResponse:
    """Sinh viên nộp bài trắc nghiệm - Chấm điểm tự động hoàn toàn ở phía máy chủ."""
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not quiz:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bài kiểm tra không tồn tại."
        )

    # Kiểm tra sinh viên có trong lớp không
    enrollment = (
        db.query(Enrollment)
        .filter(
            Enrollment.course_id == quiz.course_id,
            Enrollment.student_id == current_user.id,
        )
        .first()
    )
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn chưa ghi danh vào khóa học này.",
        )

    # Kiểm tra số lần làm bài đã vượt giới hạn chưa
    prior_attempts = (
        db.query(QuizAttempt)
        .filter(
            QuizAttempt.quiz_id == quiz_id,
            QuizAttempt.student_id == current_user.id,
        )
        .count()
    )
    if prior_attempts >= quiz.max_attempts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bạn đã đạt giới hạn số lần làm bài ({quiz.max_attempts} lần).",
        )

    # Tạo Attempt
    now = datetime.now(UTC)
    attempt = QuizAttempt(
        quiz_id=quiz.id,
        student_id=current_user.id,
        attempt_number=prior_attempts + 1,
        started_at=now,
        completed_at=now,
    )
    db.add(attempt)
    db.flush()

    total_score = 0.0
    max_possible_score = 0.0

    # Lập bản đồ đáp án của sinh viên theo question_id
    answers_map = {ans.question_id: ans.selected_option_id for ans in req.answers}

    for question in quiz.questions:
        max_possible_score += question.points
        chosen_opt_id = answers_map.get(question.id)

        is_answer_correct = False
        if chosen_opt_id is not None:
            chosen_opt = (
                db.query(QuizOption)
                .filter(
                    QuizOption.id == chosen_opt_id,
                    QuizOption.question_id == question.id,
                )
                .first()
            )
            if chosen_opt and chosen_opt.is_correct:
                is_answer_correct = True
                total_score += question.points

        quiz_ans = QuizAnswer(
            attempt_id=attempt.id,
            question_id=question.id,
            selected_option_id=chosen_opt_id,
            is_correct=is_answer_correct,
        )
        db.add(quiz_ans)

    attempt.score = round(total_score, 2)
    attempt.max_score = round(max_possible_score, 2)
    db.commit()
    db.refresh(attempt)

    log_audit(
        db,
        action="SUBMIT_QUIZ",
        entity_type="QUIZ",
        user_id=current_user.id,
        entity_id=quiz.id,
        details=f"Nộp bài trắc nghiệm #{quiz.id}, điểm tự động: {attempt.score}/{attempt.max_score}",
    )
    return QuizAttemptResponse.model_validate(attempt)


@router.get(
    "/api/quizzes/{quiz_id}/my-attempts", response_model=list[QuizAttemptResponse]
)
def get_my_quiz_attempts(
    quiz_id: int,
    current_user: User = Depends(require_roles(UserRole.SV)),
    db: Session = Depends(get_db),
) -> list[QuizAttemptResponse]:
    attempts = (
        db.query(QuizAttempt)
        .filter(
            QuizAttempt.quiz_id == quiz_id,
            QuizAttempt.student_id == current_user.id,
        )
        .order_by(QuizAttempt.attempt_number.asc())
        .all()
    )
    return [QuizAttemptResponse.model_validate(att) for att in attempts]
