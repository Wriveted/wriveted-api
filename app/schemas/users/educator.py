from __future__ import annotations

from app.schemas.users.user import UserDetail, UsersSchool
from app.schemas.users.user_identity import UserBrief


class EducatorBrief(UserBrief):
    school: UsersSchool
    # class_group: ClassGroupBrief | None


class EducatorDetail(UserDetail, EducatorBrief):
    educator_info: dict | None = None
