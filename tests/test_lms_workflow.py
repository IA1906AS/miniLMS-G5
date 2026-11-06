import io

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import create_test_user, get_auth_headers
from uv_demo.models.course import Course
from uv_demo.models.user import UserRole
from uv_demo.services.email import email_service


def test_full_lms_lifecycle(client: TestClient, db_session: Session) -> None:
    # 1. Khởi tạo các vai trò: Quản trị viên (QT), Giảng viên (GV), Sinh viên (SV)
    admin = create_test_user(
        db_session,
        "admin@lms.edu.vn",
        role=UserRole.QT,
        full_name="Quản Trị Viên Hệ Thống",
    )
    headers_admin = get_auth_headers(admin)

    # Đăng ký tài khoản người dùng mới (mặc định là SV)
    res_reg = client.post(
        "/api/auth/register",
        json={
            "email": "teacher_candidate@lms.edu.vn",
            "password": "teacherPassword123",
            "full_name": "Thầy Nguyễn Giáo Viên",
        },
    )
    assert res_reg.status_code == 201

    # Quản trị viên nâng quyền cho tài khoản này thành GV
    users_list = client.get("/api/admin/users", headers=headers_admin).json()
    gv_user_id = next(
        u["id"] for u in users_list if u["email"] == "teacher_candidate@lms.edu.vn"
    )

    res_promote = client.put(
        f"/api/admin/users/{gv_user_id}/role",
        headers=headers_admin,
        json={"role": "GV"},
    )
    assert res_promote.status_code == 200
    assert res_promote.json()["role"] == "GV"

    # Giảng viên đăng nhập
    res_gv_login = client.post(
        "/api/auth/login",
        json={
            "email": "teacher_candidate@lms.edu.vn",
            "password": "teacherPassword123",
        },
    )
    assert res_gv_login.status_code == 200
    token_gv = res_gv_login.json()["access_token"]
    headers_gv = {"Authorization": f"Bearer {token_gv}"}

    # Sinh viên đăng ký và đăng nhập
    client.post(
        "/api/auth/register",
        json={
            "email": "student_lead@lms.edu.vn",
            "password": "studentPassword123",
            "full_name": "Lê Văn Học Sinh",
        },
    )
    res_sv_login = client.post(
        "/api/auth/login",
        json={
            "email": "student_lead@lms.edu.vn",
            "password": "studentPassword123",
        },
    )
    token_sv = res_sv_login.json()["access_token"]
    headers_sv = {"Authorization": f"Bearer {token_sv}"}

    # 2. Giảng viên tạo khóa học
    res_create_course = client.post(
        "/api/courses",
        headers=headers_gv,
        json={
            "code": "CS200",
            "title": "Cấu trúc dữ liệu & Giải thuật",
            "description": "Khóa học DSA chuẩn",
        },
    )
    assert res_create_course.status_code == 201
    course_id = res_create_course.json()["id"]

    # 3. Sinh viên tìm kiếm và ghi danh khóa học bằng mã
    res_search = client.get("/api/courses?search=CS200", headers=headers_sv).json()
    assert len(res_search) == 1

    res_enroll = client.post(
        "/api/courses/enroll",
        headers=headers_sv,
        json={"course_code": "CS200"},
    )
    assert res_enroll.status_code == 200

    # Xem thành viên trong lớp
    res_members = client.get(
        f"/api/users/members/course/{course_id}", headers=headers_sv
    )
    assert res_members.status_code == 200
    assert len(res_members.json()) == 2  # GV + SV

    # 4. Giảng viên tải lên tài liệu bài giảng
    res_mat = client.post(
        f"/api/courses/{course_id}/materials",
        headers=headers_gv,
        data={"title": "Slide Bài 1 - Khởi động"},
        files={
            "file": (
                "slide1.pdf",
                io.BytesIO(b"%PDF-1.4 sample content"),
                "application/pdf",
            )
        },
    )
    assert res_mat.status_code == 200
    material_id = res_mat.json()["id"]

    # Sinh viên xem danh sách tài liệu
    res_mat_list = client.get(f"/api/courses/{course_id}/materials", headers=headers_sv)
    assert res_mat_list.status_code == 200
    assert len(res_mat_list.json()) == 1

    # Sinh viên tải tài liệu
    res_mat_dl = client.get(
        f"/api/courses/materials/{material_id}/download", headers=headers_sv
    )
    assert res_mat_dl.status_code == 200

    # 5. Bài tập và nộp bài
    res_assign = client.post(
        f"/api/courses/{course_id}/assignments",
        headers=headers_gv,
        json={
            "title": "Bài tập 1: Cây nhị phân",
            "description": "Viết thuật toán duyệt cây",
            "deadline": "2030-12-31T23:59:59Z",
            "max_score": 10.0,
        },
    )
    assert res_assign.status_code == 201
    assignment_id = res_assign.json()["id"]

    # Sinh viên nộp bài
    res_submit = client.post(
        f"/api/assignments/{assignment_id}/submit",
        headers=headers_sv,
        files={
            "file": ("solution.py", io.BytesIO(b"# solution code"), "text/x-python")
        },
    )
    assert res_submit.status_code == 201
    submission_id = res_submit.json()["id"]

    # Giảng viên xem bài nộp và chấm điểm
    subs = client.get(
        f"/api/assignments/{assignment_id}/submissions", headers=headers_gv
    ).json()
    assert len(subs) == 1

    res_grade = client.put(
        f"/api/submissions/{submission_id}/grade",
        headers=headers_gv,
        json={"score": 9.5, "feedback": "Code giải thuật tối ưu và sạch sẽ."},
    )
    assert res_grade.status_code == 200
    assert res_grade.json()["score"] == 9.5

    # Sinh viên tra cứu điểm của mình
    res_my_grades = client.get("/api/my-grades", headers=headers_sv)
    assert res_my_grades.status_code == 200
    assert res_my_grades.json()[0]["score"] == 9.5

    # 6. Bài kiểm tra trắc nghiệm & Chấm điểm tự động
    res_quiz = client.post(
        f"/api/courses/{course_id}/quizzes",
        headers=headers_gv,
        json={
            "title": "Quiz 1: Độ phức tạp thuật toán",
            "time_limit_minutes": 20,
            "max_attempts": 2,
            "questions": [
                {
                    "content": "Độ phức tạp của Binary Search là gì?",
                    "points": 5.0,
                    "options": [
                        {"content": "O(log n)", "is_correct": True},
                        {"content": "O(n)", "is_correct": False},
                        {"content": "O(n^2)", "is_correct": False},
                    ],
                },
                {
                    "content": "Stack hoạt động theo cơ chế nào?",
                    "points": 5.0,
                    "options": [
                        {"content": "LIFO", "is_correct": True},
                        {"content": "FIFO", "is_correct": False},
                    ],
                },
            ],
        },
    )
    assert res_quiz.status_code == 201

    # Lấy quiz ID từ database
    course_obj = db_session.query(Course).filter(Course.id == course_id).first()
    assert course_obj is not None
    quiz_id = course_obj.quizzes[0].id

    # Sinh viên lấy đề thi
    quiz_detail = client.get(f"/api/quizzes/{quiz_id}", headers=headers_sv).json()
    assert len(quiz_detail["questions"]) == 2

    # Lấy ID câu hỏi và đáp án để nộp đúng
    q1 = quiz_detail["questions"][0]
    q2 = quiz_detail["questions"][1]
    opt1_id = next(o["id"] for o in q1["options"] if o["content"] == "O(log n)")
    opt2_id = next(o["id"] for o in q2["options"] if o["content"] == "LIFO")

    res_take_quiz = client.post(
        f"/api/quizzes/{quiz_id}/submit",
        headers=headers_sv,
        json={
            "answers": [
                {"question_id": q1["id"], "selected_option_id": opt1_id},
                {"question_id": q2["id"], "selected_option_id": opt2_id},
            ]
        },
    )
    assert res_take_quiz.status_code == 200
    assert res_take_quiz.json()["score"] == 10.0  # Chấm tự động đạt tối đa 10/10

    # 7. Diễn đàn và Thông báo
    # Sinh viên tạo chủ đề trên diễn đàn
    res_topic = client.post(
        f"/api/courses/{course_id}/topics",
        headers=headers_sv,
        json={
            "title": "Hỏi về hàm đệ quy",
            "content": "Thầy cho em hỏi khi nào dùng memoization ạ?",
        },
    )
    assert res_topic.status_code == 201
    topic_id = res_topic.json()["id"]

    # Giảng viên trả lời bình luận
    res_comment = client.post(
        f"/api/topics/{topic_id}/comments",
        headers=headers_gv,
        json={"content": "Memoization dùng khi có các bài toán con trùng lặp em nhé."},
    )
    assert res_comment.status_code == 201

    # Giảng viên gửi thông báo phát tới lớp
    email_service.clear()
    res_announcement = client.post(
        f"/api/courses/{course_id}/announcements",
        headers=headers_gv,
        json={
            "title": "Lịch kiểm tra giữa kỳ",
            "content": "Thứ 6 tuần sau kiểm tra lúc 8h sáng nhé cả lớp.",
        },
    )
    assert res_announcement.status_code == 201
    # Đảm bảo email thông báo đã được gửi đến sinh viên ghi danh
    assert len(email_service.sent_emails) == 1
    assert email_service.sent_emails[0].to_email == "student_lead@lms.edu.vn"

    # 8. Quản trị hệ thống: Xem nhật ký hoạt động & Khóa tài khoản
    audit_logs = client.get("/api/admin/audit-logs", headers=headers_admin).json()
    assert len(audit_logs) >= 5

    # Cập nhật thông tin cá nhân và ảnh đại diện
    res_update_profile = client.put(
        "/api/users/me",
        headers=headers_sv,
        json={"bio": "Sinh viên đam mê lập trình", "contact_info": "0987654321"},
    )
    assert res_update_profile.status_code == 200
    assert res_update_profile.json()["bio"] == "Sinh viên đam mê lập trình"

    # Tải ảnh đại diện
    res_avatar = client.post(
        "/api/users/me/avatar",
        headers=headers_sv,
        files={
            "file": (
                "avatar.png",
                io.BytesIO(b"\x89PNG\r\n\x1a\nfakeimage"),
                "image/png",
            )
        },
    )
    assert res_avatar.status_code == 200

    # Quản trị viên xóa khóa học
    res_del_course = client.delete(
        f"/api/admin/courses/{course_id}", headers=headers_admin
    )
    assert res_del_course.status_code == 200
