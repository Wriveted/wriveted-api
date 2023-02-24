from __future__ import annotations
from datetime import datetime
from uuid import UUID
import phonenumbers
from pydantic import AnyHttpUrl, BaseModel
from pydantic.validators import strict_str_validator
from app.schemas.users.user_identity import UserBrief

# thanks https://github.com/pydantic/pydantic/issues/1551
class PhoneNumber(str):
    """Phone number string, E164 format (e.g. +61 400 000 000)"""

    @classmethod
    def __get_validators__(cls):
        yield strict_str_validator
        yield cls.validate

    @classmethod
    def validate(cls, v: str):
        v = v.strip().replace(" ", "")
        try:
            pn = phonenumbers.parse(v)
        except phonenumbers.phonenumberutil.NumberParseException:
            raise ValueError("invalid phone number format")

        return cls(phonenumbers.format_number(pn, phonenumbers.PhoneNumberFormat.E164))


class UserPatchOptions(BaseModel):
    newsletter: bool


class UserInfo(BaseModel):
    sign_in_provider: str | None
    phone_number: PhoneNumber | None

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
    parent_info: dict | None

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
