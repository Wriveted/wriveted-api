from typing import Literal

from app.schemas.users import UserBrief
from app.schemas.users.educator import EducatorDetail
from app.schemas.users.user import UserDetail


class SchoolAdminBrief(UserBrief):
    type: Literal["school_admin"]


class SchoolAdminDetail(EducatorDetail, UserDetail, SchoolAdminBrief):
    school_admin_info: dict | None
