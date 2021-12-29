from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, EmailStr, UUID4

from app.schemas.event import EventBrief
from app.schemas.school import SchoolBrief


class UserCreateIn(BaseModel):
    name: str
    email: EmailStr

    info: Optional[dict]


class UserUpdateIn(BaseModel):
    pass


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
    info: dict

    created_at: datetime
    updated_at: datetime

    events: List[EventBrief]
