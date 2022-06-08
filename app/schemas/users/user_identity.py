from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import UUID4, BaseModel

from app.models.user import UserAccountType


class UserIdentity(BaseModel):
    id: UUID4
    name: str
    type: UserAccountType

    class Config:
        orm_mode = True


class UserBrief(UserIdentity):
    email: str | None
    is_active: bool
    last_login_at: Optional[datetime]


class ReaderIdentity(UserIdentity):
    username: str
    first_name: str
    last_name_initial: str


class ParentIdentity(UserIdentity):
    pass
