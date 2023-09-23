import datetime
from typing import Annotated, Union

from pydantic import BaseModel, Field

from app.schemas import CaseInsensitiveStringEnum
from app.schemas.service_account import ServiceAccountBrief
from app.schemas.users.educator import EducatorDetail
from app.schemas.users.parent import ParentDetail
from app.schemas.users.reader import PublicReaderDetail
from app.schemas.users.school_admin import SchoolAdminDetail
from app.schemas.users.student import StudentDetail
from app.schemas.users.wriveted_admin import WrivetedAdminDetail


class AccountType(CaseInsensitiveStringEnum):
    user = "user"
    service_account = "service_account"


SpecificUserDetail = Annotated[
    Union[
        StudentDetail,
        SchoolAdminDetail,
        EducatorDetail,
        ParentDetail,
        WrivetedAdminDetail,
        PublicReaderDetail,
        # UserDetail,
    ],
    Field(discriminator="type"),
]


class AuthenticatedAccountBrief(BaseModel):
    account_type: AccountType
    token_expiry: datetime.datetime

    user: SpecificUserDetail | None = None
    service_account: ServiceAccountBrief | None = None
