import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr
from app.models.user import UserRole, UserStatus


class UserOut(BaseModel):
    id: uuid.UUID
    email: EmailStr
    role: UserRole
    status: UserStatus
    full_name: str | None
    email_verified: bool
    created_at: datetime
    last_login: datetime | None
    approved_at: datetime | None

    model_config = {"from_attributes": True}


class UserDetail(UserOut):
    approved_by: uuid.UUID | None


class PaginatedUsers(BaseModel):
    items: list[UserOut]
    total: int
    page: int
    limit: int
    pages: int
