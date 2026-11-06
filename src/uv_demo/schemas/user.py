from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from uv_demo.models.user import UserRole


class UserProfileResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str
    bio: str | None = None
    contact_info: str | None = None
    avatar_url: str | None = None
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserProfileUpdate(BaseModel):
    # LƯU Ý BẢO MẬT: Người dùng chỉ được sửa thông tin cá nhân.
    # Không cho phép cập nhật 'role' hoặc 'is_active' tại đây!
    full_name: str | None = Field(None, min_length=1, max_length=255)
    bio: str | None = Field(None, max_length=1000)
    contact_info: str | None = Field(None, max_length=255)


class PublicMemberProfile(BaseModel):
    id: int
    full_name: str
    role: UserRole
    avatar_url: str | None = None

    model_config = ConfigDict(from_attributes=True)
