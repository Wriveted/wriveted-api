from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, EmailStr, UUID4, AnyHttpUrl

from app.schemas.event import EventBrief
from app.schemas.school import SchoolBrief


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
    is_superuser: Optional[bool]
    school: Optional[SchoolBrief]
    info: Optional[UserInfo]


class UserBrief(BaseModel):
    id: UUID4
    name: str
    email: str
    is_active: bool
    is_superuser: bool
    school: Optional[SchoolBrief]

    class Config:
        orm_mode = True


class UserDetail(UserBrief):
    info: Optional[UserInfo]

    created_at: datetime
    updated_at: datetime

    events: List[EventBrief]
