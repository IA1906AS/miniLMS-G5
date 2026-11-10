import io
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.conftest import create_test_user, get_auth_headers
from uv_demo.models.assignment import Assignment, IdempotencyRecord, Submission
from uv_demo.models.course import Course, Enrollment
from uv_demo.models.user import AuditLog, UserRole


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


def test_assignment_submission_idempotency_key_pattern(
    client: TestClient, db_session: Session
) -> None:
    gv = create_test_user(db_session, "gv_idem@lms.edu", role=UserRole.GV)
    sv1 = create_test_user(db_session, "sv1_idem@lms.edu", role=UserRole.SV)
    sv2 = create_test_user(db_session, "sv2_idem@lms.edu", role=UserRole.SV)

    course = Course(code="IDEM101", title="Idempotency Course", instructor_id=gv.id)
    db_session.add(course)
    db_session.flush()
    db_session.add_all(
        [
            Enrollment(course_id=course.id, student_id=sv1.id),
            Enrollment(course_id=course.id, student_id=sv2.id),
        ]
    )
    assignment = Assignment(
        course_id=course.id,
        title="Idempotent Assignment",
        description="Test Idempotency Key Pattern",
        deadline=datetime.now(UTC) + timedelta(days=7),
        max_score=10.0,
    )
    db_session.add(assignment)
    db_session.commit()

    headers_sv1 = {**get_auth_headers(sv1), "Idempotency-Key": "idem-submit-key-001"}
    payload_bytes = b"print('hello idempotent world')"

    # 1. Lần gửi đầu tiên: tạo bài nộp mới
    res1 = client.post(
        f"/api/assignments/{assignment.id}/submit",
        headers=headers_sv1,
        files={"file": ("solution.py", io.BytesIO(payload_bytes), "text/x-python")},
    )
    assert res1.status_code == 201
    data1 = res1.json()

    sub_record = (
        db_session.query(Submission)
        .filter(
            Submission.assignment_id == assignment.id,
            Submission.student_id == sv1.id,
        )
        .one()
    )
    first_file_path = sub_record.file_path

    # 2. Gửi lặp lần 2 với cùng Idempotency-Key và cùng nội dung file -> trả về kết quả cũ, không ghi đè file/audit log
    res2 = client.post(
        f"/api/assignments/{assignment.id}/submit",
        headers=headers_sv1,
        files={"file": ("solution.py", io.BytesIO(payload_bytes), "text/x-python")},
    )
    assert res2.status_code == 201
    data2 = res2.json()
    assert data2["id"] == data1["id"]
    assert data2["submitted_at"] == data1["submitted_at"]

    db_session.refresh(sub_record)
    assert sub_record.file_path == first_file_path
    audit_count = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.user_id == sv1.id,
            AuditLog.action == "SUBMIT_ASSIGNMENT",
        )
        .count()
    )
    assert audit_count == 1

    # 3. Dùng lại cùng Idempotency-Key nhưng thay đổi nội dung file -> 422 Unprocessable Entity
    res_mismatch = client.post(
        f"/api/assignments/{assignment.id}/submit",
        headers=headers_sv1,
        files={
            "file": (
                "solution.py",
                io.BytesIO(b"print('different payload')"),
                "text/x-python",
            )
        },
    )
    assert res_mismatch.status_code == 422

    # 4. Sinh viên khác (sv2) dùng cùng chuỗi Idempotency-Key vẫn hoạt động độc lập
    headers_sv2 = {**get_auth_headers(sv2), "Idempotency-Key": "idem-submit-key-001"}
    res_sv2 = client.post(
        f"/api/assignments/{assignment.id}/submit",
        headers=headers_sv2,
        files={"file": ("sv2_work.py", io.BytesIO(b"print('sv2')"), "text/x-python")},
    )
    assert res_sv2.status_code == 201


def test_idempotency_key_edge_cases(client: TestClient, db_session: Session) -> None:
    gv = create_test_user(db_session, "gv_idem_edge@lms.edu", role=UserRole.GV)
    sv = create_test_user(db_session, "sv_idem_edge@lms.edu", role=UserRole.SV)
    course = Course(code="IDEM102", title="Edge Course", instructor_id=gv.id)
    db_session.add(course)
    db_session.flush()
    db_session.add(Enrollment(course_id=course.id, student_id=sv.id))
    assignment = Assignment(
        course_id=course.id,
        title="Edge Assignment",
        deadline=datetime.now(UTC) + timedelta(days=3),
        max_score=10.0,
    )
    db_session.add(assignment)
    db_session.commit()

    base_headers = get_auth_headers(sv)

    # Key rỗng hoặc quá dài -> 400 Bad Request
    for bad_key in ("   ", "k" * 129):
        res_bad = client.post(
            f"/api/assignments/{assignment.id}/submit",
            headers={**base_headers, "Idempotency-Key": bad_key},
            files={"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")},
        )
        assert res_bad.status_code == 400

    # Key đang ở trạng thái PROCESSING (request đồng thời) -> 409 Conflict
    from uv_demo.services.idempotency import compute_submission_fingerprint

    content = b"in-flight content"
    fp = compute_submission_fingerprint(assignment.id, "test.txt", content)
    in_flight = IdempotencyRecord(
        idempotency_key="in-flight-key",
        user_id=sv.id,
        assignment_id=assignment.id,
        request_hash=fp,
        status="PROCESSING",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    db_session.add(in_flight)
    db_session.commit()

    res_conflict = client.post(
        f"/api/assignments/{assignment.id}/submit",
        headers={**base_headers, "Idempotency-Key": "in-flight-key"},
        files={"file": ("test.txt", io.BytesIO(content), "text/plain")},
    )
    assert res_conflict.status_code == 409

    # Key đã hết hạn (expires_at <= now) -> được làm mới và nộp thành công
    in_flight.expires_at = datetime.now(UTC) - timedelta(minutes=5)
    db_session.commit()

    res_expired = client.post(
        f"/api/assignments/{assignment.id}/submit",
        headers={**base_headers, "Idempotency-Key": "in-flight-key"},
        files={"file": ("test.txt", io.BytesIO(content), "text/plain")},
    )
    assert res_expired.status_code == 201
