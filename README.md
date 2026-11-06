# Hệ thống Quản lý Học tập (Learning Management System - LMS)

[![CI](https://github.com/IA1906AS/miniLMS-G5/actions/workflows/ci.yml/badge.svg)](https://github.com/IA1906AS/miniLMS-G5/actions/workflows/ci.yml)

Hệ thống LMS hoàn chỉnh được xây dựng trên **Python 3.12**, quản lý gói bằng **uv**, tuân thủ nghiêm ngặt đặc tả chức năng 7 phần và triển khai kiến trúc phân quyền nhiều lớp nhằm triệt tiêu các nguy cơ **leo thang đặc quyền (Privilege Escalation)**.

---

## 1. Vai trò người dùng (Roles)
- **`SV` - Sinh viên**: Đăng ký tài khoản, tra cứu và ghi danh khóa học, tải tài liệu, nộp bài tập, làm bài trắc nghiệm, trao đổi trên diễn đàn.
- **`GV` - Giảng viên**: Quản lý khóa học được phân công, tải lên tài liệu giảng dạy, tạo & chấm điểm bài tập, tạo bài trắc nghiệm, phát thông báo cho lớp.
- **`QT` - Quản trị viên**: Quản lý người dùng (khóa/mở tài khoản, phân quyền vai trò), quản lý toàn bộ khóa học, giám sát nhật ký hoạt động (Audit Log).

---

## 2. Thiết kế bảo mật chống leo thang đặc quyền (Privilege Escalation Defense)

### A. Chống leo thang đặc quyền dọc (Vertical Privilege Escalation)
1. **Khống chế Schema đăng ký (`RegisterRequest`)**: Endpoint `/api/auth/register` tuyệt đối **không chấp nhận trường `role`** từ phía client. Mọi tài khoản tự đăng ký đều bắt buộc khởi tạo với quyền `SV`.
2. **Cập nhật hồ sơ an toàn (`UserProfileUpdate`)**: Người dùng chỉ được sửa thông tin cá nhân (`full_name`, `bio`, `contact_info`), không thể tự đổi `role` hoặc `is_active`.
3. **Phân quyền vai trò độc quyền cho `QT`**: Endpoint đổi vai trò `/api/admin/users/{id}/role` được bảo vệ bằng dependency `require_roles(UserRole.QT)`.
4. **Bảo vệ chống tự khóa**: Quản trị viên không thể tự khóa tài khoản của chính mình nhằm tránh thảm họa mất quyền truy cập.

### B. Chống leo thang đặc quyền ngang & IDOR (Horizontal Privilege Escalation)
1. **Cô lập bài nộp (`Submissions`)**:
   - Sinh viên chỉ có thể xem và tải về file bài nộp của chính mình (`submission.student_id == current_user.id`).
   - Truy cập bài nộp của sinh viên khác lập tức bị chặn với HTTP `403 Forbidden`.
2. **Kiểm soát quyền sở hữu khóa học của Giảng viên**:
   - Giảng viên A không thể chỉnh sửa, thêm tài liệu, tạo bài tập hoặc chấm điểm trong khóa học do Giảng viên B phụ trách (`course.instructor_id == current_user.id`).
3. **Kiểm soát quyền truy cập khóa học theo ghi danh**:
   - Sinh viên chỉ có thể tải tài liệu, xem bài tập và tham gia thảo luận nếu đã được ghi danh (`Enrollment`) vào khóa học đó.
4. **Bảo vệ quyền tác giả trên Diễn đàn**:
   - Người dùng chỉ có quyền sửa hoặc xóa chủ đề/bình luận do chính mình tạo ra (`author_id == current_user.id` hoặc `QT`).

### C. Chống gian lận thi trắc nghiệm & Rò rỉ đáp án
- Khi sinh viên lấy đề kiểm tra qua API `/api/quizzes/{id}`, thuộc tính `is_correct` trong các đáp án lựa chọn **được lọc bỏ hoàn toàn** ở tầng Schema (`QuizOptionStudentOut`), ngăn chặn việc xem đáp án qua DevTools/Network Tab.
- Việc so khớp đáp án và tính điểm được thực hiện **100% tại máy chủ (Server-side auto-grading)**.
- Kiểm soát số lần làm bài (`max_attempts`) nghiêm ngặt trên database.

### D. Bảo vệ tệp tải lên (File Storage Security)
- Tên tệp lưu trữ được tạo ngẫu nhiên bằng `UUID4` để triệt tiêu lỗ hổng **Path Traversal (`../`)**.
- Kiểm tra whitelist đuôi tệp (`.pdf`, `.docx`, `.zip`, `.png`,...) và giới hạn dung lượng tải lên tối đa (15 MB).

---

## 3. Cài đặt và Chạy kiểm thử

```bash
# 1. Cài đặt toàn bộ môi trường và dependencies
uv sync

# 2. Kiểm tra chất lượng code và định dạng
uv run ruff check src tests
uv run ruff format --check src tests

# 3. Kiểm tra kiểu dữ liệu tĩnh nghiêm ngặt
uv run mypy src tests

# 4. Chạy toàn bộ 24 bài unit & integration test và đo độ bao phủ
uv run pytest

# 5. Quét lỗ hổng bảo mật thư viện (SCA)
uv run pip-audit

# 6. Chạy server phát triển (OpenAPI docs tại http://127.0.0.1:8000/docs)
uv run python -m uv_demo
```
