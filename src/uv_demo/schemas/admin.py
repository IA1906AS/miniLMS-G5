from datetime import datetime

from pydantic import BaseModel, ConfigDict

from uv_demo.models.user import UserRole


class UserAdminUpdateRole(BaseModel):
    role: UserRole


class UserAdminLock(BaseModel):
    is_active: bool


class AuditLogResponse(BaseModel):
    id: int
    user_id: int | None = None
    action: str
    entity_type: str
    entity_id: int | None = None
    details: str | None = None
    ip_address: str | None = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
