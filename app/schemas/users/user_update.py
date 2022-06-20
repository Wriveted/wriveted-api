from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, EmailStr

from app.models.user import UserAccountType
from app.schemas.users.huey_attributes import HueyAttributes
from app.schemas.users.user import UserInfo


class UserUpdateIn(BaseModel):
    # all users
    name: str | None
    is_active: bool | None
    email: EmailStr | None
    info: UserInfo | None
    type: UserAccountType | None
    newsletter: bool | None

    # readers
    username: str | None
    first_name: str | None
    last_name_initial: str | None
    huey_attributes: HueyAttributes | None = {}

    # students / educators
    school_id: int | None
    class_group_id: UUID | None

    student_info: dict | None
    school_admin_info: dict | None
    wriveted_admin_info: dict | None
