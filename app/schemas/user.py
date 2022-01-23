from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, EmailStr, UUID4, AnyHttpUrl

from app.schemas.event import EventBrief
from app.schemas.school import SchoolBrief

class UserInfo:
    sign_in_provider: str
    # hoping pictures won't be base64 strings
    picture: Optional[AnyHttpUrl]


class UserCreateIn(BaseModel):
    name: str
    email: EmailStr

    info: Optional[dict]


class UserUpdateIn(BaseModel):
    name: Optional[str]
    is_active: Optional[bool]
    is_superuser: Optional[bool]
    school: Optional[SchoolBrief]
    info: Optional[dict]


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
    info: Optional[dict]

    created_at: datetime
    updated_at: datetime

    events: List[EventBrief]
