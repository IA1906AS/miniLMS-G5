import io

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import create_test_user, get_auth_headers
from uv_demo.models.course import Course, Enrollment
from uv_demo.models.user import UserRole


def test_admin_lock_and_unlock_user(client: TestClient, db_session: Session) -> None:
    admin = create_test_user(db_session, "super_admin@lms.edu", role=UserRole.QT)
    target_user = create_test_user(db_session, "target_lock@lms.edu", role=UserRole.SV)
    headers_admin = get_auth_headers(admin)

    # Khóa người dùng
    res_lock = client.put(
        f"/api/admin/users/{target_user.id}/lock",
        headers=headers_admin,
        json={"is_active": False},
    )
    assert res_lock.status_code == 200
    assert res_lock.json()["is_active"] is False

    # Admin không thể tự khóa chính mình
    res_self_lock = client.put(
        f"/api/admin/users/{admin.id}/lock",
        headers=headers_admin,
        json={"is_active": False},
    )
    assert res_self_lock.status_code == 400

    # Mở khóa người dùng
    res_unlock = client.put(
        f"/api/admin/users/{target_user.id}/lock",
        headers=headers_admin,
        json={"is_active": True},
    )
    assert res_unlock.status_code == 200
    assert res_unlock.json()["is_active"] is True


def test_instructor_manual_enroll_student(
    client: TestClient, db_session: Session
) -> None:
    gv = create_test_user(db_session, "gv_manual@lms.edu", role=UserRole.GV)
    sv = create_test_user(db_session, "sv_manual@lms.edu", role=UserRole.SV)
    course = Course(code="MANUAL101", title="Manual Course", instructor_id=gv.id)
    db_session.add(course)
    db_session.commit()

    headers_gv = get_auth_headers(gv)

    # Giảng viên thêm sinh viên vào lớp
    res = client.post(
        f"/api/courses/{course.id}/enroll-student",
        headers=headers_gv,
        json={"student_email": sv.email},
    )
    assert res.status_code == 200
    assert "thành công" in res.json()["message"]

    # Thêm lại lần 2 -> báo đã có trong danh sách
    res_dup = client.post(
        f"/api/courses/{course.id}/enroll-student",
        headers=headers_gv,
        json={"student_email": sv.email},
    )
    assert res_dup.status_code == 200
    assert "đã có trong danh sách" in res_dup.json()["message"]


def test_forum_topic_and_comment_lifecycle(
    client: TestClient, db_session: Session
) -> None:
    gv = create_test_user(db_session, "gv_flow@lms.edu", role=UserRole.GV)
    sv = create_test_user(db_session, "sv_flow@lms.edu", role=UserRole.SV)
    course = Course(code="FORUM202", title="Forum Course", instructor_id=gv.id)
    db_session.add(course)
    db_session.flush()
    db_session.add(Enrollment(course_id=course.id, student_id=sv.id))
    db_session.commit()

    headers_sv = get_auth_headers(sv)

    # SV tạo topic
    res_t = client.post(
        f"/api/courses/{course.id}/topics",
        headers=headers_sv,
        json={"title": "Original Title", "content": "Original Content"},
    )
    assert res_t.status_code == 201
    topic_id = res_t.json()["id"]

    # SV cập nhật topic
    res_t_update = client.put(
        f"/api/topics/{topic_id}",
        headers=headers_sv,
        json={"title": "Updated Title", "content": "Updated Content"},
    )
    assert res_t_update.status_code == 200
    assert res_t_update.json()["title"] == "Updated Title"

    # SV thêm comment
    res_c = client.post(
        f"/api/topics/{topic_id}/comments",
        headers=headers_sv,
        json={"content": "My Comment"},
    )
    assert res_c.status_code == 201
    comment_id = res_c.json()["id"]

    # SV sửa comment
    res_c_update = client.put(
        f"/api/comments/{comment_id}",
        headers=headers_sv,
        json={"content": "Updated Comment"},
    )
    assert res_c_update.status_code == 200
    assert res_c_update.json()["content"] == "Updated Comment"

    # SV xóa comment
    res_c_del = client.delete(f"/api/comments/{comment_id}", headers=headers_sv)
    assert res_c_del.status_code == 200

    # SV xóa topic
    res_t_del = client.delete(f"/api/topics/{topic_id}", headers=headers_sv)
    assert res_t_del.status_code == 200


def test_avatar_upload_and_download(client: TestClient, db_session: Session) -> None:
    user = create_test_user(db_session, "avatar_user@lms.edu", role=UserRole.SV)
    headers = get_auth_headers(user)

    # Tải lên avatar
    res_upload = client.post(
        "/api/users/me/avatar",
        headers=headers,
        files={
            "file": (
                "myavatar.png",
                io.BytesIO(b"\x89PNG\r\n\x1a\nfakeavatar"),
                "image/png",
            )
        },
    )
    assert res_upload.status_code == 200

    # Tải về avatar
    res_get = client.get(f"/api/users/avatar/{user.id}")
    assert res_get.status_code == 200
