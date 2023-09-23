from typing import Literal

from app.models.user import UserAccountType
from app.schemas.users.educator import EducatorBrief, EducatorDetail
from app.schemas.users.user import UserDetail


class SchoolAdminBrief(EducatorBrief):
    type: Literal[UserAccountType.SCHOOL_ADMIN]


class SchoolAdminDetail(EducatorDetail, UserDetail, SchoolAdminBrief):
    school_admin_info: dict | None = None
    type: Literal[UserAccountType.SCHOOL_ADMIN]
