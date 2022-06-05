import datetime
import enum

from pydantic import BaseModel

from app.schemas.service_account import ServiceAccountBrief
from app.schemas.users.educator import EducatorDetail
from app.schemas.users.parent import ParentDetail
from app.schemas.users.school_admin import SchoolAdminDetail
from app.schemas.users.student import StudentDetail
from app.schemas.users.user import UserDetail
from app.schemas.wriveted_admin import WrivetedAdminDetail


class AccountType(str, enum.Enum):
    user = "user"
    service_account = "service_account"


class AuthenticatedAccountBrief(BaseModel):
    account_type: AccountType
    token_expiry: datetime.datetime
    user: UserDetail | StudentDetail | EducatorDetail | SchoolAdminDetail | WrivetedAdminDetail | ParentDetail | None
    service_account: ServiceAccountBrief | None
