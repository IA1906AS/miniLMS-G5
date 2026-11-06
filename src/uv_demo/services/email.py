from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class SentEmail:
    to_email: str
    subject: str
    content: str
    sent_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class EmailService:
    def __init__(self) -> None:
        self.sent_emails: list[SentEmail] = []

    def send_email(self, to_email: str, subject: str, content: str) -> SentEmail:
        email = SentEmail(to_email=to_email, subject=subject, content=content)
        self.sent_emails.append(email)
        return email

    def send_password_reset_email(self, to_email: str, reset_token: str) -> SentEmail:
        subject = "Khôi phục mật khẩu - Hệ thống LMS"
        content = (
            f"Xin chào,\n\nBạn đã yêu cầu đặt lại mật khẩu cho tài khoản {to_email}.\n"
            f"Mã xác nhận đặt lại mật khẩu của bạn là: {reset_token}\n"
            "Mã này có hiệu lực trong 30 phút. Vui lòng không chia sẻ mã này cho bất kỳ ai."
        )
        return self.send_email(to_email, subject, content)

    def send_announcement_email(
        self, to_email: str, course_title: str, title: str, content: str
    ) -> SentEmail:
        subject = f"[{course_title}] Thông báo mới: {title}"
        body = f"Giảng viên vừa đăng thông báo mới trong khóa học {course_title}:\n\n{content}"
        return self.send_email(to_email, subject, body)

    def clear(self) -> None:
        self.sent_emails.clear()


email_service = EmailService()
