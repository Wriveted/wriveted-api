import enum
from typing import Optional

from pydantic import BaseModel

from app.schemas.service_account import ServiceAccountBrief
from app.schemas.user import UserDetail


class AccountType(str, enum.Enum):
    user = "user"
    service_account = "service_account"


class AuthenticatedAccountBrief(BaseModel):
    account_type: AccountType
    user: Optional[UserDetail]
    service_account: Optional[ServiceAccountBrief]