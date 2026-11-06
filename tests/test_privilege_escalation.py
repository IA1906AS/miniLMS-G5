import io
from datetime import UTC

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import create_test_user, get_auth_headers
from uv_demo.config import settings
from uv_demo.models.assignment import Assignment, Submission
from uv_demo.models.course import Course, Enrollment, Material
from uv_demo.models.forum import ForumComment, ForumTopic
from uv_demo.models.quiz import Quiz, QuizOption, QuizQuestion
from uv_demo.models.user import User, UserRole


def test_vertical_escalation_registration_ignores_role(
    client: TestClient, db_session: Session
) -> None:
    """Tấn công leo thang đặc quyền dọc khi đăng ký:

    Attacker cố tình gửi `role: "QT"` hoặc `role: "GV"` trong body đăng ký.
    Hệ thống PHẢI phớt lờ và luôn chỉ cấp quyền SV (Sinh viên).
    """
    payload = {
        "email": "hacker@example.com",
        "password": "password123",
        "full_name": "Hacker WannaBeAdmin",
        "role": "QT",  # Cố tình leo thang
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 201

    user = db_session.query(User).filter(User.email == "hacker@example.com").first()
    assert user is not None
    assert user.role == UserRole.SV  # Bắt buộc là SV


def test_vertical_escalation_student_cannot_access_admin(
    client: TestClient, db_session: Session
) -> None:
    student = create_test_user(db_session, "sv_attacker@example.com", role=UserRole.SV)
    headers = get_auth_headers(student)

    # 1. Xem danh sách user
    res1 = client.get("/api/admin/users", headers=headers)
    assert res1.status_code == 403

    # 2. Tự nâng quyền cho mình thành QT
    res2 = client.put(
        f"/api/admin/users/{student.id}/role",
        headers=headers,
        json={"role": "QT"},
    )
    assert res2.status_code == 403

    # 3. Khóa tài khoản người khác
    res3 = client.put(
        f"/api/admin/users/{student.id}/lock",
        headers=headers,
        json={"is_active": False},
    )
    assert res3.status_code == 403

    # 4. Xem nhật ký hoạt động
    res4 = client.get("/api/admin/audit-logs", headers=headers)
    assert res4.status_code == 403


def test_vertical_escalation_student_cannot_act_as_instructor(
    client: TestClient, db_session: Session
) -> None:
    student = create_test_user(db_session, "sv_fake_gv@example.com", role=UserRole.SV)
    headers = get_auth_headers(student)

    # 1. Sinh viên tạo khóa học
    res_course = client.post(
        "/api/courses",
        headers=headers,
        json={"code": "CS999", "title": "Illegal Course"},
    )
    assert res_course.status_code == 403

    # Tạo khóa học hợp lệ bởi GV thật
    gv = create_test_user(db_session, "real_gv@example.com", role=UserRole.GV)
    course = Course(
        code="CS101",
        title="Python Core",
        instructor_id=gv.id,
        is_active=True,
    )
    db_session.add(course)
    db_session.commit()

    # 2. Sinh viên cố tạo bài tập
    res_assign = client.post(
        f"/api/courses/{course.id}/assignments",
        headers=headers,
        json={
            "title": "Hack Assignment",
            "deadline": "2030-01-01T00:00:00Z",
            "max_score": 10.0,
        },
    )
    assert res_assign.status_code == 403

    # 3. Sinh viên cố tạo bài trắc nghiệm
    res_quiz = client.post(
        f"/api/courses/{course.id}/quizzes",
        headers=headers,
        json={
            "title": "Fake Quiz",
            "time_limit_minutes": 10,
            "max_attempts": 1,
            "questions": [],
        },
    )
    assert res_quiz.status_code == 403


def test_horizontal_escalation_student_cannot_view_other_submission(
    client: TestClient, db_session: Session
) -> None:
    """Tấn công IDOR / Leo thang ngang giữa 2 sinh viên:

    Sinh viên A không được phép tải hoặc xem bài nộp của Sinh viên B.
    """
    gv = create_test_user(db_session, "gv_owner@example.com", role=UserRole.GV)
    sv_a = create_test_user(db_session, "student_a@example.com", role=UserRole.SV)
    sv_b = create_test_user(db_session, "student_b@example.com", role=UserRole.SV)

    course = Course(
        code="MATH101", title="Calculus", instructor_id=gv.id, is_active=True
    )
    db_session.add(course)
    db_session.flush()

    db_session.add(Enrollment(course_id=course.id, student_id=sv_a.id))
    db_session.add(Enrollment(course_id=course.id, student_id=sv_b.id))

    from datetime import datetime

    # Tạo tệp bài làm giả lập trong settings.UPLOAD_DIR / "submissions"
    sub_dir = settings.UPLOAD_DIR / "submissions"
    sub_dir.mkdir(parents=True, exist_ok=True)
    sample_file = sub_dir / "sample_sub_b.pdf"
    sample_file.write_bytes(b"%PDF-1.4 sample content")

    assign = Assignment(
        course_id=course.id,
        title="Homework 1",
        deadline=datetime(2030, 1, 1, tzinfo=UTC),
        max_score=10.0,
    )
    db_session.add(assign)
    db_session.flush()

    sub_b = Submission(
        assignment_id=assign.id,
        student_id=sv_b.id,
        filename="solution_b.pdf",
        file_path="submissions/sample_sub_b.pdf",
    )

    db_session.add(sub_b)
    db_session.commit()

    # Sinh viên A cố tải bài làm của Sinh viên B bằng ID của B
    headers_a = get_auth_headers(sv_a)
    res_download = client.get(
        f"/api/submissions/{sub_b.id}/download", headers=headers_a
    )
    assert res_download.status_code == 403
    assert (
        "Bạn không có quyền tải tệp bài làm của sinh viên khác"
        in res_download.json()["detail"]
    )

    # Sinh viên A xem danh sách bài nộp của assignment -> chỉ thấy bài của A (hoặc rỗng nếu A chưa nộp)
    res_list = client.get(
        f"/api/assignments/{assign.id}/submissions", headers=headers_a
    )
    assert res_list.status_code == 200
    submissions_seen = res_list.json()
    assert all(s["student_id"] == sv_a.id for s in submissions_seen)


def test_horizontal_escalation_instructor_cannot_modify_other_course(
    client: TestClient, db_session: Session
) -> None:
    """Tấn công IDOR giữa các giảng viên:

    Giảng viên 1 không được phép sửa đổi khóa học hay chấm điểm bài tập của Giảng viên 2.
    """
    gv1 = create_test_user(db_session, "gv1@example.com", role=UserRole.GV)
    gv2 = create_test_user(db_session, "gv2@example.com", role=UserRole.GV)

    course2 = Course(
        code="PHYS101", title="Physics", instructor_id=gv2.id, is_active=True
    )
    db_session.add(course2)
    db_session.commit()

    headers_gv1 = get_auth_headers(gv1)

    # GV 1 cố cập nhật thông tin khóa học của GV 2
    res_update = client.put(
        f"/api/courses/{course2.id}",
        headers=headers_gv1,
        json={"title": "Hacked Title"},
    )
    assert res_update.status_code == 403
    assert (
        "Bạn không có quyền chỉnh sửa khóa học do giảng viên khác phụ trách"
        in res_update.json()["detail"]
    )

    # GV 1 cố tải tài liệu lên khóa học của GV 2
    res_mat = client.post(
        f"/api/courses/{course2.id}/materials",
        headers=headers_gv1,
        data={"title": "Unauthorized Lecture"},
        files={"file": ("lecture.pdf", io.BytesIO(b"data"), "application/pdf")},
    )
    assert res_mat.status_code == 403


def test_horizontal_escalation_non_enrolled_student_cannot_access_materials(
    client: TestClient, db_session: Session
) -> None:
    gv = create_test_user(db_session, "gv_chem@example.com", role=UserRole.GV)
    sv_outsider = create_test_user(db_session, "outsider@example.com", role=UserRole.SV)

    course = Course(
        code="CHEM101", title="Chemistry", instructor_id=gv.id, is_active=True
    )
    db_session.add(course)
    db_session.flush()

    material = Material(
        course_id=course.id,
        title="Secret Exam Material",
        filename="exam.pdf",
        file_path="materials/exam.pdf",
        uploaded_by_id=gv.id,
    )
    db_session.add(material)
    db_session.commit()

    headers_outsider = get_auth_headers(sv_outsider)

    # Sinh viên chưa ghi danh cố truy xuất danh sách tài liệu
    res_list = client.get(
        f"/api/courses/{course.id}/materials", headers=headers_outsider
    )
    assert res_list.status_code == 403
    assert "Bạn chưa ghi danh vào khóa học này" in res_list.json()["detail"]


def test_forum_tampering_protection(client: TestClient, db_session: Session) -> None:
    """Bảo vệ diễn đàn: User A không được sửa hoặc xóa bài của User B."""
    gv = create_test_user(db_session, "gv_forum@example.com", role=UserRole.GV)
    user_a = create_test_user(db_session, "user_a@example.com", role=UserRole.SV)
    user_b = create_test_user(db_session, "user_b@example.com", role=UserRole.SV)

    course = Course(code="ENG101", title="English", instructor_id=gv.id, is_active=True)
    db_session.add(course)
    db_session.flush()

    db_session.add(Enrollment(course_id=course.id, student_id=user_a.id))
    db_session.add(Enrollment(course_id=course.id, student_id=user_b.id))

    topic_b = ForumTopic(
        course_id=course.id,
        author_id=user_b.id,
        title="User B Question",
        content="How to learn grammar?",
    )
    db_session.add(topic_b)
    db_session.flush()

    comment_b = ForumComment(
        topic_id=topic_b.id, author_id=user_b.id, content="Extra note"
    )
    db_session.add(comment_b)
    db_session.commit()

    headers_a = get_auth_headers(user_a)

    # User A cố sửa topic của User B
    res_edit_topic = client.put(
        f"/api/topics/{topic_b.id}",
        headers=headers_a,
        json={"title": "Defaced by A"},
    )
    assert res_edit_topic.status_code == 403

    # User A cố xóa comment của User B
    res_del_comm = client.delete(f"/api/comments/{comment_b.id}", headers=headers_a)
    assert res_del_comm.status_code == 403


def test_quiz_anti_cheat_no_correct_answers_leaked(
    client: TestClient, db_session: Session
) -> None:
    """Kiểm tra chống gian lận trong trắc nghiệm:

    Khi sinh viên lấy đề trắc nghiệm, response KHÔNG ĐƯỢC chứa thuộc tính `is_correct`.
    """
    gv = create_test_user(db_session, "gv_quiz@example.com", role=UserRole.GV)
    sv = create_test_user(db_session, "sv_quiz@example.com", role=UserRole.SV)

    course = Course(code="BIO101", title="Biology", instructor_id=gv.id, is_active=True)
    db_session.add(course)
    db_session.flush()
    db_session.add(Enrollment(course_id=course.id, student_id=sv.id))

    quiz = Quiz(
        course_id=course.id,
        title="Bio Quiz 1",
        time_limit_minutes=15,
        max_attempts=1,
    )
    db_session.add(quiz)
    db_session.flush()

    q = QuizQuestion(quiz_id=quiz.id, content="DNA stands for?", points=1.0)
    db_session.add(q)
    db_session.flush()

    opt1 = QuizOption(
        question_id=q.id, content="Deoxyribonucleic Acid", is_correct=True
    )
    opt2 = QuizOption(
        question_id=q.id, content="Data Network Analysis", is_correct=False
    )
    db_session.add_all([opt1, opt2])
    db_session.commit()

    # Sinh viên lấy đề thi
    headers_sv = get_auth_headers(sv)
    res = client.get(f"/api/quizzes/{quiz.id}", headers=headers_sv)
    assert res.status_code == 200

    data = res.json()
    for question in data["questions"]:
        for option in question["options"]:
            assert "is_correct" not in option  # Không được rò rỉ đáp án đúng!
