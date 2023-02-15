from __future__ import annotations
from typing import Literal
import phonenumbers

from pydantic import BaseModel, EmailStr, constr, root_validator
from pydantic.validators import strict_str_validator

from app.schemas.recommendations import HueKeys, ReadingAbilityKey


# thanks https://github.com/pydantic/pydantic/issues/1551
class PhoneNumber(str):
    """Phone Number Pydantic type, using google's phonenumbers"""

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


class AlertRecipient(BaseModel):
    nickname: str | None

    email: EmailStr | None
    phone: PhoneNumber | None
    type: Literal["email", "phone"]

    @root_validator(pre=True)
    def validate(cls, values):
        if values.get("email") and values.get("phone"):
            raise ValueError("Only one of email or phone can be provided.")
        elif values.get("email"):
            values["type"] = "email"
        elif values.get("phone"):
            values["type"] = "phone"
        else:
            raise ValueError("One of email or phone must be provided.")

        return values


class HueyAttributes(BaseModel):
    birthdate: constr(
        regex=r"(\d{4})-(\d{2})-(\d{2})( (\d{2}):(\d{2}):(\d{2}))?"
    ) | None
    last_visited: constr(
        regex=r"(\d{4})-(\d{2})-(\d{2})( (\d{2}):(\d{2}):(\d{2}))?"
    ) | None

    age: int | None
    reading_ability: list[ReadingAbilityKey] | None
    hues: list[HueKeys] | None

    goals: list[str] | None
    genres: list[str] | None
    characters: list[str] | None

    parent_nickname: str | None

    alert_recipients: list[AlertRecipient] | None
