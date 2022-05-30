import datetime
import enum
from typing import Optional, Union

from pydantic import BaseModel

from app.schemas.service_account import ServiceAccountBrief
from app.schemas.user import (
    SchoolAdminDetail,
    StudentDetail,
    UserDetail,
    WrivetedAdminDetail,
)


class AccountType(str, enum.Enum):
    user = "user"
    service_account = "service_account"


class AuthenticatedAccountBrief(BaseModel):
    account_type: AccountType
    token_expiry: datetime.datetime
    user: UserDetail | StudentDetail | SchoolAdminDetail | WrivetedAdminDetail | None
    service_account: ServiceAccountBrief | None
