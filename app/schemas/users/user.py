from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel

from app.schemas.users.user_identity import UserBrief


class UserPatchOptions(BaseModel):
    newsletter: bool


class UserInfo(BaseModel):
    sign_in_provider: str | None

    # hoping pictures won't be base64 strings
    picture: AnyHttpUrl | None

    # storing each individual user type's info
    # in the base will allow a type of posterity
    # in the event of user type changes
    reader_info: dict | None
    student_info: dict | None
    educator_info: dict | None
    school_admin_info: dict | None
    wriveted_admin_info: dict | None

    other: dict | None


class UserDetail(UserBrief):
    info: UserInfo | None

    created_at: datetime
    updated_at: datetime
    newsletter: bool


class UsersSchool(BaseModel):
    wriveted_identifier: UUID
    official_identifier: str | None
    country_code: str
    name: str

    class Config:
        orm_mode = True
