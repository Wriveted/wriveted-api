from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, EmailStr, UUID4, AnyHttpUrl

from app.models.user import UserAccountType
from app.schemas.event import EventBrief
from app.schemas.school import SchoolBrief


# due to using SSO, not much can be patched at the moment
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
    school: Optional[SchoolBrief]
    info: Optional[UserInfo]


class UserBrief(BaseModel):
    id: UUID4
    name: str
    email: str
    is_active: bool
    type: UserAccountType
    school: Optional[SchoolBrief]

    class Config:
        orm_mode = True


class UserDetail(UserBrief):
    info: Optional[UserInfo]

    created_at: datetime
    updated_at: datetime

    events: List[EventBrief]

    newsletter: bool

    school_id_as_admin: Optional[str]
