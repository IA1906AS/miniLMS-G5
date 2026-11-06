"""SSOT - Single Source of Truth (Nguồn Chân Lý Duy Nhất) cho Hệ thống MiniLMS.

Chứa toàn bộ định nghĩa chuẩn mực duy nhất về:
1. Phân quyền và vai trò người dùng (SV, GV, QT)
2. Ma trận quyền hạn & kiểm soát truy cập (Access Control Matrix)
3. Cơ chế bảo vệ chống leo thang đặc quyền (Privilege Escalation Prevention)
4. Chính sách chống rò rỉ thông tin (Information Disclosure Safeguards)
5. Dữ liệu tài khoản kiểm thử mẫu chuẩn
"""

from typing import Any

SSOT_SPEC: dict[str, Any] = {
    "system": {
        "name": "MiniLMS - Hệ Thống Quản Trị Học Tập",
        "version": "1.0.0",
        "architecture": "FastAPI + uv + SQLAlchemy + Tailwind CSS Web Client",
        "security_standard": "OWASP Top 10 (A01: Broken Access Control, A02: Cryptographic Failures, A04: Insecure Design, A05: Security Misconfiguration, CWE-200: Information Disclosure)",
    },
    "roles": {
        "SV": {
            "code": "SV",
            "name": "Sinh viên",
            "english": "Student",
            "color": "sky",
            "badge_class": "bg-sky-100 text-sky-800 border-sky-300",
            "description": "Người học tham gia vào các khóa học được phân công hoặc tự ghi danh bằng mã môn.",
            "allowed_actions": [
                "Xem danh mục tất cả khóa học đang mở trong hệ thống",
                "Tự ghi danh vào khóa học bằng mã môn học hợp lệ (/api/courses/enroll)",
                "Tải về tài liệu học tập, slide bài giảng từ khóa học đã ghi danh",
                "Nộp bài tập trực tuyến (tải lên file mã nguồn/tài liệu và ghi chú)",
                "Làm bài kiểm tra trắc nghiệm tính giờ trực tiếp (đồng hồ đếm ngược tự động nộp bài)",
                "Xem sổ điểm cá nhân (/api/courses/{id}/my-grades và /api/my-grades)",
                "Tạo chủ đề thảo luận và gửi bình luận trong diễn đàn khóa học",
                "Xem thông báo quan trọng do giảng viên phát hành",
                "Chỉnh sửa hồ sơ cá nhân của chính mình (họ tên, bio, thông tin liên hệ)",
            ],
            "forbidden_actions": [
                "Không được phép tạo mới hoặc chỉnh sửa khóa học (Chặn 403 Forbidden)",
                "Không được phép xem hoặc tải bài làm của sinh viên khác (Chặn IDOR / Horizontal Escalation)",
                "Không được phép nhận dữ liệu đáp án đúng của bài trắc nghiệm trước khi hoàn thành",
                "Không được phép tự nâng cấp vai trò thành GV hoặc QT (Chặn Vertical Escalation)",
                "Không được phép truy cập cổng quản trị hệ thống /api/admin/*",
            ],
        },
        "GV": {
            "code": "GV",
            "name": "Giảng viên",
            "english": "Teacher / Instructor",
            "color": "emerald",
            "badge_class": "bg-emerald-100 text-emerald-800 border-emerald-300",
            "description": "Người phụ trách chuyên môn, quản lý danh sách lớp, tài liệu, bài tập và đánh giá điểm số.",
            "allowed_actions": [
                "Khởi tạo khóa học mới trong hệ thống (/api/courses)",
                "Cập nhật nội dung khóa học do mình phụ trách",
                "Bổ sung sinh viên vào danh sách lớp bằng email sinh viên",
                "Tải lên giáo trình, tài liệu bài giảng (.pdf, .docx, .zip)",
                "Giao bài tập với thời hạn nộp (deadline) và thang điểm tối đa",
                "Xem toàn bộ danh sách bài nộp của sinh viên trong khóa học mình phụ trách",
                "Tải bài nộp của sinh viên về để đánh giá",
                "Chấm điểm và phản hồi nhận xét trực tiếp cho từng sinh viên",
                "Soạn đề thi trắc nghiệm (nhiều câu hỏi, cấu hình đáp án đúng, thời gian làm bài)",
                "Xem lịch sử nộp bài trắc nghiệm của sinh viên",
                "Đăng thông báo khóa học (tự động phát thông báo tới sinh viên)",
                "Điều phối thảo luận trên diễn đàn môn học",
                "Xem bảng điểm toàn diện của toàn bộ sinh viên trong lớp (Gradebook)",
            ],
            "forbidden_actions": [
                "Không được phép chỉnh sửa, giao bài hoặc chấm điểm trên khóa học của giảng viên khác",
                "Không được phép tự gán quyền Quản trị viên (QT) cho chính mình hoặc người khác",
                "Không được phép truy cập cổng quản trị hệ thống (/api/admin/*)",
                "Không được phép xem bài nộp trên các khóa học mình không được phân công",
            ],
        },
        "QT": {
            "code": "QT",
            "name": "Quản trị viên",
            "english": "Admin / System Administrator",
            "color": "purple",
            "badge_class": "bg-purple-100 text-purple-800 border-purple-300",
            "description": "Người chịu trách nhiệm cao nhất về vận hành, giám sát người dùng, toàn vẹn hệ thống và an toàn thông tin.",
            "allowed_actions": [
                "Xem toàn bộ danh sách người dùng trong hệ thống (/api/admin/users)",
                "Thay đổi vai trò của người dùng bất kỳ (SV ⇄ GV ⇄ QT)",
                "Khóa hoặc mở khóa tài khoản người dùng khi phát hiện vi phạm",
                "Xem toàn bộ danh mục khóa học và gỡ bỏ khóa học vi phạm chính sách",
                "Truy xuất và lọc nhật ký kiểm toán an toàn (Security Audit Logs)",
                "Giám sát mọi hành vi đăng nhập, đăng xuất, nộp bài, chấm điểm và nâng quyền",
            ],
            "forbidden_actions": [
                "Không thể tự khóa tài khoản quản trị của chính mình (Bảo vệ an toàn vận hành)",
                "Không thể chỉnh sửa hoặc làm sai lệch nhật ký kiểm toán (Audit Logs bất biến)",
            ],
        },
    },
    "test_accounts": [
        {
            "role": "SV",
            "name": "Trần Văn An",
            "email": "student1@lms.edu.vn",
            "password": "student123",
            "purpose": "Kiểm thử vai trò Sinh viên (SV): Ghi danh, nộp bài, thi trắc nghiệm, xem điểm cá nhân.",
        },
        {
            "role": "SV",
            "name": "Phạm Thị Bích",
            "email": "student2@lms.edu.vn",
            "password": "student123",
            "purpose": "Kiểm thử chống leo thang ngang (IDOR): Kiểm tra sinh viên Bích không thể xem bài nộp của An.",
        },
        {
            "role": "GV",
            "name": "Thầy Nguyễn Hoàng Giang",
            "email": "teacher@lms.edu.vn",
            "password": "teacher123",
            "purpose": "Kiểm thử vai trò Giảng viên (GV): Tạo môn học, tải tài liệu, chấm bài, soạn đề trắc nghiệm.",
        },
        {
            "role": "QT",
            "name": "Quản Trị Viên Trưởng",
            "email": "admin@lms.edu.vn",
            "password": "admin123",
            "purpose": "Kiểm thử vai trò Quản trị viên (QT): Đổi quyền người dùng, khóa tài khoản, xem Audit Log.",
        },
    ],
    "security_safeguards": {
        "information_disclosure": [
            "Không để lộ tài khoản quản trị viên và mật khẩu trần trụi ngoài giao diện đăng nhập mặc định (CWE-200)",
            "Chống User Enumeration: Thông báo đăng nhập luôn đồng nhất 'Email hoặc mật khẩu không chính xác'",
            "Chống Timing Attack (CWE-208): Thực hiện tính toán hash bcrypt giả lập khi email không tồn tại để thời gian phản hồi bằng nhau",
            "Chống lộ đáp án trắc nghiệm: Schema QuizOptionStudentOut lược bỏ hoàn toàn trường is_correct khi gửi về client",
            "Chống lộ cấu trúc server (Fingerprinting): Xóa header 'server' và thêm đầy đủ Security Headers (nosniff, DENY, etc.)",
            "Chống rò rỉ mã nguồn/traceback: Bắt toàn bộ ngoại lệ 500 và trả về thông điệp an toàn đã làm sạch",
        ],
        "privilege_escalation": [
            "Vertical Escalation: API /api/auth/register luôn gán cứng role=SV, người dùng không thể gửi role=QT/GV",
            "Vertical Escalation: Mọi endpoint /api/admin/* bắt buộc dependency require_roles(UserRole.QT)",
            "Horizontal Escalation (IDOR): Kiểm tra sở hữu submission.student_id == current_user.id trước khi cho phép tải/xem",
            "Cross-Course Escalation: Giảng viên chỉ được quản lý khóa học có course.instructor_id == current_user.id",
        ],
        "network_and_assets": [
            "Rate Limiting: Giới hạn 15 lượt đăng nhập/phút trên mỗi IP để ngăn Brute-Force & Credential Stuffing",
            "Subresource Integrity (SRI): Gắn mã băm cryptographic hash cho toàn bộ thư viện CDN",
            "Token Revocation: Thu hồi token JWT ngay lập tức khi đăng xuất với TokenBlacklist trong DB",
            "Path Traversal Prevention: Tên file tải lên được đổi thành UUID4 ngẫu nhiên trên máy chủ",
        ],
    },
}
