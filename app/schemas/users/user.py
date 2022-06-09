from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, validator
from sqlalchemy.orm.dynamic import AppenderQuery

from app.schemas.event import EventBrief
from app.schemas.users.user_identity import UserBrief


class UserPatchOptions(BaseModel):
    newsletter: bool


class UserInfo(BaseModel):
    sign_in_provider: str | None

    # hoping pictures won't be base64 strings
    picture: AnyHttpUrl | None
    other: dict | None


class UserDetail(UserBrief):
    info: UserInfo | None

    created_at: datetime
    updated_at: datetime
    events: list[EventBrief]
    newsletter: bool

    @validator("events", pre=True)
    def limit_events(cls, v):
        return v[:10] if isinstance(v, AppenderQuery) else v


class UsersSchool(BaseModel):
    wriveted_identifier: UUID
    official_identifier: str | None
    country_code: str
    name: str

    class Config:
        orm_mode = True
