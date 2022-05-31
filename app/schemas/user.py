from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import UUID4, AnyHttpUrl, BaseModel, EmailStr, validator
from sqlalchemy.orm.dynamic import AppenderQuery

from app.models.user import UserAccountType
from app.schemas.event import EventBrief


class UserPatchOptions(BaseModel):
    newsletter: bool


class UserInfo(BaseModel):
    sign_in_provider: Optional[str]

    # hoping pictures won't be base64 strings
    picture: Optional[AnyHttpUrl]
    other: Optional[dict]


class UserCreateIn(BaseModel):
    name: str
    email: EmailStr
    info: Optional[UserInfo]


class UserUpdateIn(BaseModel):
    name: Optional[str]
    is_active: Optional[bool]
    type: Optional[UserAccountType]
    # school: Optional[SchoolBrief]
    info: Optional[UserInfo]


class UsersSchool(BaseModel):
    wriveted_identifier: UUID
    official_identifier: Optional[str]
    country_code: str
    name: str
    collection_count: int

    class Config:
        orm_mode = True

    @validator('collection_count', pre=True)
    def set_collection_count(cls, v):
        return v or 0


class UserIdentity(BaseModel):
    id: UUID4
    name: str
    username: str | None
    type: UserAccountType

    class Config:
        orm_mode = True


class UserBrief(UserIdentity):
    email: str
    is_active: bool
    last_login_at: Optional[datetime]
    school_as_admin: Optional[UsersSchool]


class UserDetail(UserBrief):
    info: Optional[UserInfo]

    created_at: datetime
    updated_at: datetime

    events: list[EventBrief]

    newsletter: bool

    @validator("events", pre=True)
    def limit_events(cls, v):
        return v[:10] if isinstance(v, AppenderQuery) else v
