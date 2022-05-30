from datetime import datetime
from typing import Optional
from uuid import UUID
import uuid

from pydantic import UUID4, AnyHttpUrl, BaseModel, EmailStr, validator
from sqlalchemy.orm.dynamic import AppenderQuery

from app.models.user import UserAccountType
from app.schemas.event import EventBrief
from app.schemas.recommendations import ReadingAbilityKey


class UserPatchOptions(BaseModel):
    newsletter: bool


class UserInfo(BaseModel):
    sign_in_provider: str | None

    # hoping pictures won't be base64 strings
    picture: AnyHttpUrl | None
    other: dict | None


class StudentInfo(BaseModel):
    reading_ability_preference: ReadingAbilityKey | None
    age: int | None
    other: dict | None


class UserCreateIn(BaseModel):
    name: str
    email: EmailStr | None
    username: str | None
    info: UserInfo | None
    type: UserAccountType | None


class SchoolAdminCreateIn(UserCreateIn):
    type = UserAccountType.LIBRARY
    school_id: int | None


class StudentCreateIn(UserCreateIn):
    type = UserAccountType.STUDENT
    school_id: int | None
    class_group_id: UUID | None


class UserUpdateIn(BaseModel):
    name: str | None
    is_active: bool | None
    type: UserAccountType | None
    # school: Optional[SchoolBrief]
    info: UserInfo | None


class UsersSchool(BaseModel):
    wriveted_identifier: UUID
    official_identifier: str | None
    country_code: str
    name: str
    collection_count: int

    class Config:
        orm_mode = True


class UserIdentity(BaseModel):
    id: UUID4
    name: str
    username: str | None
    type: UserAccountType

    class Config:
        orm_mode = True


class StudentIdentity(UserIdentity):
    first_name: str
    last_name_initial: str


class UserBrief(UserIdentity):
    email: str
    is_active: bool
    last_login_at: datetime | None


class StudentBrief(UserBrief):
    school: UsersSchool | None
    # class_group: ClassGroupBrief | None


class SchoolAdminBrief(UserBrief):
    school: UsersSchool | None
    # class_group: ClassGroupBrief | None


class WrivetedAdminBrief(UserBrief):
    pass


class UserDetail(UserBrief):
    info: UserInfo | None

    created_at: datetime
    updated_at: datetime

    events: list[EventBrief]

    newsletter: bool

    @validator("events", pre=True)
    def limit_events(cls, v):
        return v[:10] if isinstance(v, AppenderQuery) else v


class StudentDetail(UserDetail, StudentBrief):
    student_info: StudentInfo | None


class SchoolAdminDetail(UserDetail, SchoolAdminBrief):
    school_admin_info: dict | None


class WrivetedAdminDetail(UserDetail, WrivetedAdminBrief):
    wriveted_admin_info: dict | None
