from typing import Optional

from pydantic import BaseModel

from app.schemas.service_account import ServiceAccountBrief
from app.schemas.user import UserDetail


class AuthenticatedAccountBrief(BaseModel):
    account_type: str
    user: Optional[UserDetail]
    service_account: Optional[ServiceAccountBrief]