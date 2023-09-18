from typing import Literal

from app.schemas.users.educator import EducatorBrief, EducatorDetail
from app.schemas.users.user import UserDetail


class SchoolAdminBrief(EducatorBrief):
    type: Literal["school_admin"]


class SchoolAdminDetail(EducatorDetail, UserDetail, SchoolAdminBrief):
    school_admin_info: dict | None = None
