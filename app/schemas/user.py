from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, EmailStr, UUID4, AnyHttpUrl

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


class UserIdentity(BaseModel):
    id: UUID4
    name: str
    type: UserAccountType

    class Config:
        orm_mode = True


class UserBrief(UserIdentity):
    email: str
    is_active: bool
    last_login_at: Optional[datetime]
    school_id_as_admin: Optional[str]
    school_as_admin: Optional[UsersSchool]


class UserDetail(UserBrief):
    info: Optional[UserInfo]

    created_at: datetime
    updated_at: datetime

    events: List[EventBrief]

    newsletter: bool
