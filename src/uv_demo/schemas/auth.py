from pydantic import BaseModel, EmailStr, Field

from uv_demo.models.user import UserRole


class RegisterRequest(BaseModel):
    # LƯU Ý BẢO MẬT: Tuyệt đối không nhận trường 'role' từ client để ngăn chặn
    # leo thang đặc quyền dọc (Vertical Privilege Escalation).
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=255)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    user_id: int
    full_name: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str = Field(..., min_length=10)
    new_password: str = Field(..., min_length=6, max_length=128)


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6, max_length=128)


class MessageResponse(BaseModel):
    message: str
