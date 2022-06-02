from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.schemas.event import EventBrief
    from app.schemas.reader import ReadingPreferences

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import UUID4, AnyHttpUrl, BaseModel, EmailStr, root_validator, validator
from sqlalchemy.orm.dynamic import AppenderQuery

from app.models.user import UserAccountType


class UserPatchOptions(BaseModel):
    newsletter: bool


class UserInfo(BaseModel):
    sign_in_provider: Optional[str]

    # hoping pictures won't be base64 strings
    picture: Optional[AnyHttpUrl]
    other: Optional[dict]


class UserCreateIn(BaseModel):
    # all users
    name: str
    email: EmailStr
    info: UserInfo | None
    type: UserAccountType | None = UserAccountType.PUBLIC

    # readers
    username: str | None
    first_name: str | None
    last_name_initial: str | None

    # students / educators
    school_id: int | None
    class_id: UUID | None

    student_info: dict | None
    school_admin_info: dict | None
    wriveted_admin_info: dict | None

    @root_validator
    def validate_user_creation(cls, values):
        match values.get("type"):
            case UserAccountType.STUDENT:
                if not (
                    values.get("first_name")
                    and values.get("last_name_initial")
                    and values.get("school_id")
                ):
                    raise ValueError(
                        "Student users must provide first_name, last_name_initial, and school_id."
                    )
            case UserAccountType.EDUCATOR:
                if not (
                    values.get("first_name")
                    and values.get("last_name_initial")
                    and values.get("school_id")
                ):
                    raise ValueError("Educator users must provide school_id.")
            case UserAccountType.SCHOOL_ADMIN:
                if not (values.get("school_id")):
                    raise ValueError("SchoolAdmin users must provide school_id.")
            case _:
                pass

        return values


class UserUpdateIn(BaseModel):
    # all users
    name: str | None
    is_active: bool | None
    email: EmailStr | None
    info: UserInfo | None
    type: UserAccountType | None

    # readers
    username: str | None
    first_name: str | None
    last_name_initial: str | None
    reading_preferences: ReadingPreferences | None = {}

    # students / educators
    school_id: int | None
    class_id: UUID | None

    student_info: dict | None
    school_admin_info: dict | None
    wriveted_admin_info: dict | None


class UsersSchool(BaseModel):
    wriveted_identifier: UUID
    official_identifier: Optional[str]
    country_code: str
    name: str
    collection_count: int

    class Config:
        orm_mode = True

    @validator("collection_count", pre=True)
    def set_collection_count(cls, v):
        return v or 0


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


class UserDetail(UserBrief):
    info: Optional[UserInfo]

    created_at: datetime
    updated_at: datetime

    events: list[EventBrief]

    newsletter: bool

    @validator("events", pre=True)
    def limit_events(cls, v):
        return v[:10] if isinstance(v, AppenderQuery) else v
