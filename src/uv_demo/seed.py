from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from uv_demo.database import SessionLocal
from uv_demo.models.assignment import Assignment, Submission
from uv_demo.models.course import Course, Enrollment, Material
from uv_demo.models.forum import Announcement, ForumComment, ForumTopic
from uv_demo.models.quiz import Quiz, QuizOption, QuizQuestion
from uv_demo.models.user import User, UserRole
from uv_demo.security.password import hash_password


def seed_initial_data(db: Session) -> None:
    # Nếu đã có dữ liệu thì không tạo lại
    if db.query(User).first():
        return

    now = datetime.now(UTC)

    # 1. Khởi tạo 3 vai trò mẫu chuẩn
    admin = User(
        email="admin@lms.edu.vn",
        hashed_password=hash_password("admin123"),
        full_name="Quản Trị Viên (Admin)",
        role=UserRole.QT,
        is_active=True,
        bio="Quản trị viên trưởng hệ thống LMS",
    )
    teacher = User(
        email="teacher@lms.edu.vn",
        hashed_password=hash_password("teacher123"),
        full_name="Thầy Nguyễn Hoàng Giang (GV)",
        role=UserRole.GV,
        is_active=True,
        bio="Giảng viên Khoa Công nghệ Thông tin",
    )
    student1 = User(
        email="student1@lms.edu.vn",
        hashed_password=hash_password("student123"),
        full_name="Trần Văn An (Sinh viên)",
        role=UserRole.SV,
        is_active=True,
        bio="Sinh viên ngành Kỹ thuật Phần mềm",
    )
    student2 = User(
        email="student2@lms.edu.vn",
        hashed_password=hash_password("student123"),
        full_name="Phạm Thị Bích (Sinh viên)",
        role=UserRole.SV,
        is_active=True,
        bio="Sinh viên ngành Khoa học Máy tính",
    )

    db.add_all([admin, teacher, student1, student2])
    db.flush()

    # 2. Khởi tạo Khóa học mẫu
    course1 = Course(
        code="CS101",
        title="Lập trình Python Nâng cao & Thiết kế Hệ thống",
        description="Khóa học cung cấp kiến trúc ứng dụng web hiện đại, CI/CD, kiểm thử tự động và bảo mật OWASP.",
        instructor_id=teacher.id,
        is_active=True,
    )
    course2 = Course(
        code="CS202",
        title="Cấu trúc Dữ liệu & Giải thuật Ứng dụng",
        description="Nghiên cứu các cấu trúc dữ liệu kinh điển: Cây, Đồ thị, Bảng băm và tối ưu hóa độ phức tạp.",
        instructor_id=teacher.id,
        is_active=True,
    )
    db.add_all([course1, course2])
    db.flush()

    # Ghi danh sinh viên vào khóa học
    enroll1 = Enrollment(course_id=course1.id, student_id=student1.id)
    enroll2 = Enrollment(course_id=course1.id, student_id=student2.id)
    enroll3 = Enrollment(course_id=course2.id, student_id=student1.id)
    db.add_all([enroll1, enroll2, enroll3])

    # 3. Tài liệu bài giảng mẫu
    mat1 = Material(
        course_id=course1.id,
        title="Giáo trình Bài 1: Tổng quan Kiến trúc Hệ thống",
        filename="bai1_tong_quan.pdf",
        file_path="materials/sample_doc.pdf",
        uploaded_by_id=teacher.id,
    )
    db.add(mat1)

    # 4. Bài tập mẫu
    assign1 = Assignment(
        course_id=course1.id,
        title="Bài tập 1: Xây dựng API và Kiểm thử Unit Test",
        description="Viết ứng dụng backend với 5 endpoint và hoàn thành kiểm thử đạt độ bao phủ tối thiểu 80%.",
        deadline=now + timedelta(days=14),
        max_score=10.0,
    )
    db.add(assign1)
    db.flush()

    # Bài nộp mẫu đã chấm điểm
    sub1 = Submission(
        assignment_id=assign1.id,
        student_id=student1.id,
        filename="bai_lam_an_tran.zip",
        file_path="submissions/sample_sub.zip",
        score=9.5,
        feedback="Bài làm xuất sắc! Cấu trúc code sạch sẽ, kiểm thử chặt chẽ.",
        graded_by_id=teacher.id,
        graded_at=now,
    )
    db.add(sub1)

    # 5. Bài trắc nghiệm mẫu
    quiz1 = Quiz(
        course_id=course1.id,
        title="Kiểm tra Trắc nghiệm: Kiến thức Python 3.12 & Web Security",
        description="Bài kiểm tra 3 câu hỏi trắc nghiệm tự động chấm điểm, thời gian làm bài 15 phút.",
        time_limit_minutes=15,
        max_attempts=3,
    )
    db.add(quiz1)
    db.flush()

    q1 = QuizQuestion(
        quiz_id=quiz1.id,
        content="Trong FastAPI, mã trạng thái HTTP nào biểu thị quyền truy cập bị từ chối do không đủ đặc quyền?",
        points=3.5,
    )
    db.add(q1)
    db.flush()
    db.add_all(
        [
            QuizOption(question_id=q1.id, content="401 Unauthorized", is_correct=False),
            QuizOption(question_id=q1.id, content="403 Forbidden", is_correct=True),
            QuizOption(question_id=q1.id, content="404 Not Found", is_correct=False),
            QuizOption(
                question_id=q1.id, content="422 Unprocessable Entity", is_correct=False
            ),
        ]
    )

    q2 = QuizQuestion(
        quiz_id=quiz1.id,
        content="Công cụ nào sau đây trong uv được sử dụng để khóa phiên bản dependencies toàn hệ thống?",
        points=3.5,
    )
    db.add(q2)
    db.flush()
    db.add_all(
        [
            QuizOption(question_id=q2.id, content="pyproject.toml", is_correct=False),
            QuizOption(question_id=q2.id, content="uv.lock", is_correct=True),
            QuizOption(question_id=q2.id, content="requirements.txt", is_correct=False),
        ]
    )

    q3 = QuizQuestion(
        quiz_id=quiz1.id,
        content="Kỹ thuật nào giúp ngăn chặn triệt để tấn công Path Traversal khi lưu tệp tải lên?",
        points=3.0,
    )
    db.add(q3)
    db.flush()
    db.add_all(
        [
            QuizOption(
                question_id=q3.id,
                content="Lưu trực tiếp theo tên file người dùng gửi lên",
                is_correct=False,
            ),
            QuizOption(
                question_id=q3.id,
                content="Đổi tên tệp thành mã định danh ngẫu nhiên (UUID4) trên máy chủ",
                is_correct=True,
            ),
            QuizOption(
                question_id=q3.id,
                content="Chỉ kiểm tra chữ in hoa của tên tệp",
                is_correct=False,
            ),
        ]
    )

    # 6. Thông báo & Diễn đàn mẫu
    announcement1 = Announcement(
        course_id=course1.id,
        author_id=teacher.id,
        title="Chào mừng các bạn sinh viên đến với khóa học CS101!",
        content="Các em chú ý xem tài liệu bài giảng và lịch nộp bài tập số 1 trên hệ thống nhé.",
    )
    db.add(announcement1)

    topic1 = ForumTopic(
        course_id=course1.id,
        author_id=student1.id,
        title="Thảo luận về cách cấu hình Linter Ruff trong dự án",
        content="Thầy và các bạn cho mình hỏi nên bật những rule nào trong ruff để cân bằng giữa nghiêm ngặt và tiện lợi ạ?",
    )
    db.add(topic1)
    db.flush()

    comment1 = ForumComment(
        topic_id=topic1.id,
        author_id=teacher.id,
        content="Em nên bật các nhóm E, W (pycodestyle), F (pyflakes), I (isort) và B (bugbear) như trong tài liệu hướng dẫn nhé.",
    )
    db.add(comment1)

    db.commit()


def run_seed_if_needed() -> None:
    db = SessionLocal()
    try:
        seed_initial_data(db)
    finally:
        db.close()
