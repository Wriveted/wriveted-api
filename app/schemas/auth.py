import datetime
import enum
from pydantic import BaseModel

from app.schemas.service_account import ServiceAccountBrief
from app.schemas.user import UserDetail
from app.schemas.student import StudentDetail
from app.schemas.educator import EducatorDetail
from app.schemas.school_admin import SchoolAdminDetail
from app.schemas.wriveted_admin import WrivetedAdminDetail
from app.schemas.parent import ParentDetail


class AccountType(str, enum.Enum):
    user = "user"
    service_account = "service_account"


class AuthenticatedAccountBrief(BaseModel):
    account_type: AccountType
    token_expiry: datetime.datetime
    user: UserDetail | StudentDetail | EducatorDetail | SchoolAdminDetail | WrivetedAdminDetail | ParentDetail | None
    service_account: ServiceAccountBrief | None
