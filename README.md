# MiniLMS — Hệ thống Quản trị Học tập Trực tuyến (Full-Stack FastAPI + SPA)

[![CI](https://github.com/IA1906AS/miniLMS-G5/actions/workflows/ci.yml/badge.svg)](https://github.com/IA1906AS/miniLMS-G5/actions/workflows/ci.yml)

Hệ thống **MiniLMS** hoàn chỉnh bao gồm **Backend RESTful API (FastAPI + SQLAlchemy + SQLite + JWT + Bcrypt)** và **Frontend Web Portal** phân quyền 3 vai trò:
- **`SV` — Sinh viên (Student)**
- **`GV` — Giảng viên (Teacher/Instructor)**
- **`QT` — Quản trị viên (Administrator)**

---

## 1. Kiến trúc Hệ thống (Backend & Frontend)

### A. Backend (`src/uv_demo/`)
Hệ thống có **Backend thực tế 100%** viết bằng Python 3.12 + FastAPI + SQLAlchemy ORM (lưu trữ cơ sở dữ liệu SQLite bền vững tại `lms_production.db` và lưu trữ tệp tải lên tại `uploads/`):
- **Xác thực & Phiên làm việc ([`routers/auth.py`](src/uv_demo/routers/auth.py))**:
  - `POST /api/auth/register`: Đăng ký tài khoản mới (cố định vai trò `SV` chống leo thang đặc quyền).
  - `POST /api/auth/login`: Đăng nhập cấp JWT Token, tích hợp Rate Limiting (15 lần/phút/IP) và chống dò tìm tài khoản (Timing Attack Mitigation).
  - `POST /api/auth/logout`: Thu hồi JWT tức thời thông qua bảng `TokenBlacklist`.
  - `POST /api/auth/change-password`: Đổi mật khẩu an toàn.
- **Hồ sơ & Thành viên ([`routers/users.py`](src/uv_demo/routers/users.py))**:
  - `GET /api/users/me`, `PUT /api/users/me`: Xem và cập nhật thông tin cá nhân.
  - `GET /api/users/members/course/{course_id}`: Danh sách thành viên lớp học.
- **Quản lý Khóa học & Tài liệu ([`routers/courses.py`](src/uv_demo/routers/courses.py))**:
  - `GET /api/courses`, `GET /api/courses/{id}`: Tra cứu danh mục và chi tiết khóa học.
  - `POST /api/courses`, `PUT /api/courses/{id}`: Tạo/cập nhật khóa học (dành cho `GV`, `QT`).
  - `POST /api/courses/enroll`: Sinh viên (`SV`) tự ghi danh khóa học.
  - `POST /api/courses/{id}/enroll-student`: Giảng viên (`GV`) thêm sinh viên vào lớp bằng email.
  - `POST /api/courses/{id}/materials`, `GET /api/courses/materials/{id}/download`: Tải lên và tải xuống tài liệu bài giảng (lưu trữ an toàn với tên tệp `UUID4`).
- **Bài tập, Nộp bài & Chấm điểm ([`routers/assignments.py`](src/uv_demo/routers/assignments.py))**:
  - `POST /api/courses/{id}/assignments`, `GET /api/courses/{id}/assignments`: Giao và xem bài tập.
  - `POST /api/assignments/{id}/submit`: Sinh viên nộp bài tập (văn bản và/hoặc tệp đính kèm).
  - `PUT /api/submissions/{id}/grade`: Giảng viên chấm điểm (`0 - 100`) và nhận xét bài làm.
  - `GET /api/courses/{id}/gradebook`, `GET /api/my-grades`: Bảng điểm lớp học và sổ điểm cá nhân.
- **Thi Trắc nghiệm Đếm ngược & Chấm tự động ([`routers/quizzes.py`](src/uv_demo/routers/quizzes.py))**:
  - `POST /api/courses/{id}/quizzes`, `GET /api/quizzes/{id}`: Tạo đề và lấy đề thi (tự động ẩn trường `is_correct` đối với `SV`).
  - `POST /api/quizzes/{id}/attempt`: Nộp bài thi trắc nghiệm và chấm điểm tự động 100% trên Backend.
- **Diễn đàn Thảo luận & Thông báo ([`routers/forum.py`](src/uv_demo/routers/forum.py))**:
  - `POST /api/courses/{id}/announcements`, `GET /api/courses/{id}/announcements`: Thông báo lớp học.
  - `POST /api/courses/{id}/topics`, `POST /api/topics/{id}/comments`: Tạo chủ đề hỏi đáp và bình luận.
- **Quản trị Hệ thống & Nhật ký Kiểm toán ([`routers/admin.py`](src/uv_demo/routers/admin.py))**:
  - `GET /api/admin/users`, `PUT /api/admin/users/{id}/role`, `PUT /api/admin/users/{id}/status`: Quản lý người dùng, cấp quyền `SV`/`GV`/`QT`, khóa/mở khóa tài khoản.
  - `DELETE /api/admin/courses/{id}`: Gỡ bỏ khóa học vi phạm.
  - `GET /api/admin/audit-logs`: Truy vết toàn bộ lịch sử hoạt động nhạy cảm (`AuditLog`).

### B. Frontend (`src/uv_demo/static/`)
- **Cổng đăng nhập độc lập**: `http://127.0.0.1:8000/login` ([`login.html`](src/uv_demo/static/login.html))
- **Cổng đăng ký Sinh viên độc lập**: `http://127.0.0.1:8000/register` ([`register.html`](src/uv_demo/static/register.html))
- **Bảng điều khiển LMS chính**: `http://127.0.0.1:8000/` hoặc `http://127.0.0.1:8000/app` ([`index.html`](src/uv_demo/static/index.html))
- **Tài liệu API tương tác (Swagger UI)**: `http://127.0.0.1:8000/docs`

---

## 2. Hướng dẫn Khởi chạy Hệ thống

 Mở PowerShell tại thư mục dự án và chạy:

```powershell
# 1. Đồng bộ môi trường ảo và thư viện
uv sync

# 2. Khởi chạy Backend + Web Server tại http://127.0.0.1:8000
uv run python -m uv_demo
```

Sau khi server chạy, mở trình duyệt tại:
- **Giao diện Đăng nhập**: `http://127.0.0.1:8000/login`
- **Giao diện Đăng ký (SV)**: `http://127.0.0.1:8000/register`
- **Swagger OpenAPI (Backend टेस्ट)**: `http://127.0.0.1:8000/docs`

---

## 3. Hướng dẫn Sử dụng theo Từng Vai trò (User Guide)

### Vai trò 1: Sinh viên (`SV`)
1. **Đăng ký / Đăng nhập**:
   - Truy cập `/register` để tạo tài khoản Sinh viên mới, hoặc đăng nhập tại `/login`.
2. **Ghi danh Khóa học**:
   - Tại màn hình **Danh sách Khóa học**, nhấn nút **"Ghi danh & Vào học"** ngay trên thẻ khóa học (hoặc nhấn **"Ghi danh bằng mã"** và nhập mã môn như `CS101`).
3. **Học tập & Tương tác**:
   - **Diễn đàn & Thông báo**: Xem thông báo từ giảng viên, nhấn **"+ Đăng câu hỏi mới"** hoặc bình luận trao đổi trong chủ đề.
   - **Tài liệu bài giảng**: Nhấn **"Tải về"** để tải slide/giáo trình của môn học.
   - **Bài tập**: Chọn bài tập $\rightarrow$ Nhập nội dung bài làm hoặc đính kèm file $\rightarrow$ Nhấn **"Gửi bài nộp"**.
   - **Trắc nghiệm**: Nhấn **"Làm bài ngay"**, chọn đáp án trong thời gian đếm ngược và nộp bài để nhận điểm chấm tự động ngay lập tức.
4. **Xem điểm**:
   - Vào tab **"Sổ điểm của tôi"** trên thanh menu hoặc tab **"Bảng điểm"** trong từng khóa học.

### Vai trò 2: Giảng viên (`GV`)
1. **Tạo & Quản lý Khóa học**:
   - Nhấn nút **"+ Tạo khóa học mới"** ở trang Danh sách Khóa học, nhập Mã môn (VD: `SE202`), Tên khóa học và Mô tả.
2. **Quản lý Học liệu & Lớp học** (bên trong khóa học do mình phụ trách):
   - **Thông báo**: Nhấn **"+ Đăng thông báo"** để gửi thông báo cho cả lớp.
   - **Tài liệu**: Vào tab **Tài liệu bài giảng** $\rightarrow$ Nhấn **"Tải lên tài liệu"** để upload file PDF/DOCX/ZIP/Slide.
   - **Thành viên lớp**: Vào tab **Thành viên lớp** $\rightarrow$ Nhập email sinh viên vào ô thêm học viên và nhấn **"+ Thêm vào lớp"**.
3. **Giao bài tập, Chấm điểm & Tạo đề thi**:
   - **Bài tập**: Vào tab **Bài tập** $\rightarrow$ Nhấn **"+ Giao bài tập mới"**. Khi sinh viên nộp bài, nhấn **"Xem & Chấm điểm DS bài nộp"** để nhập điểm (`0 - 100`) và lời phê.
   - **Trắc nghiệm**: Vào tab **Trắc nghiệm** $\rightarrow$ Nhấn **"+ Soạn bài trắc nghiệm"**, thêm các câu hỏi nhiều lựa chọn và cấu hình thời gian làm bài.

### Vai trò 3: Quản trị viên (`QT`)
1. **Truy cập Cổng Quản trị**:
   - Trên thanh điều hướng trên cùng, chọn tab **"Quản trị hệ thống (QT)"**.
2. **Quản lý Người dùng & Phân quyền**:
   - Tìm kiếm người dùng theo tên/email hoặc lọc theo vai trò (`SV`, `GV`, `QT`).
   - Đổi vai trò trực tiếp tại cột **Vai trò (Phân quyền)** (ví dụ: nâng quyền tài khoản từ `SV` lên `GV` hoặc `QT`).
   - Khóa hoặc mở khóa tài khoản vi phạm tại cột **Hành động**.
3. **Quản lý Khóa học & Kiểm toán Bảo mật**:
   - Chuyển sang tab **Quản lý Khóa học** để xem toàn bộ khóa học trên hệ thống và xóa khóa học vi phạm.
   - Chuyển sang tab **Nhật ký Kiểm toán (Audit Logs)** để giám sát mọi thao tác nhạy cảm kèm địa chỉ IP và dấu thời gian.

---

## 4. Kiểm thử Tự động & Kiểm tra Chất lượng Code

```powershell
# Chạy bộ 35 bài kiểm thử tự động (Unit, Integration, RBAC, Anti-Leak, <=350 dòng/file)
uv run pytest

# Kiểm tra định dạng, linter và kiểu dữ liệu tĩnh
uv run ruff check src tests
uv run mypy
```
