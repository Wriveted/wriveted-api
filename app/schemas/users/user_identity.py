from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import UUID4, BaseModel, ConfigDict

from app.models.user import UserAccountType


class UserBase(BaseModel):
    id: UUID4
    type: UserAccountType
    model_config = ConfigDict(from_attributes=True)


class UserIdentity(UserBase):
    name: str


class UserBrief(UserIdentity):
    email: str | None = None
    is_active: bool
    last_login_at: Optional[datetime] = None
