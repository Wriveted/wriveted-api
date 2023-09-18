from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict

from app.schemas.phone_number import PhoneNumber
from app.schemas.users.user_identity import UserBrief


class UserPatchOptions(BaseModel):
    newsletter: bool


class UserInfo(BaseModel):
    sign_in_provider: str | None = None
    phone_number: PhoneNumber | None = None

    # hoping pictures won't be base64 strings
    picture: AnyHttpUrl | None = None

    # storing each individual user type's info
    # in the base will allow a type of posterity
    # in the event of user type changes
    reader_info: dict | None = None
    student_info: dict | None = None
    educator_info: dict | None = None
    school_admin_info: dict | None = None
    wriveted_admin_info: dict | None = None
    parent_info: dict | None = None

    other: dict | None = None


class UserDetail(UserBrief):
    info: UserInfo | None = None

    created_at: datetime
    updated_at: datetime
    newsletter: bool


class UsersSchool(BaseModel):
    wriveted_identifier: UUID
    official_identifier: str | None = None
    country_code: str
    name: str
    model_config = ConfigDict(from_attributes=True)
