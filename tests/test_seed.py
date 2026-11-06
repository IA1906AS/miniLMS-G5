from sqlalchemy.orm import Session

from uv_demo.models.course import Course
from uv_demo.models.user import User, UserRole
from uv_demo.seed import seed_initial_data


def test_seed_initial_data_idempotent(db_session: Session) -> None:
    # 1. Chạy seed lần đầu
    seed_initial_data(db_session)

    admin = db_session.query(User).filter(User.role == UserRole.QT).first()
    assert admin is not None
    assert admin.email == "admin@lms.edu.vn"

    teacher = db_session.query(User).filter(User.role == UserRole.GV).first()
    assert teacher is not None
    assert teacher.email == "teacher@lms.edu.vn"

    students = db_session.query(User).filter(User.role == UserRole.SV).all()
    assert len(students) >= 2

    courses = db_session.query(Course).all()
    assert len(courses) >= 2

    # 2. Chạy seed lần thứ hai để đảm bảo tính idempotent (không nhân bản dữ liệu)
    seed_initial_data(db_session)
    admin_count = (
        db_session.query(User).filter(User.email == "admin@lms.edu.vn").count()
    )
    assert admin_count == 1
