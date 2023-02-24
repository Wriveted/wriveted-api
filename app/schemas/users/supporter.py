from __future__ import annotations
from phonenumbers import PhoneNumber

from pydantic import Field
from app.schemas.users.user_identity import UserBrief, UserIdentity


class SupporterBrief(UserBrief):
    phone: PhoneNumber | None = Field(None, alias="info.phone_number")
    readers: list[UserIdentity]
