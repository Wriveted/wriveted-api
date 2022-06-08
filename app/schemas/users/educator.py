from __future__ import annotations

from app.schemas.school_identity import SchoolIdentity
from app.schemas.users.user import UserDetail, UsersSchool
from app.schemas.users.user_identity import UserIdentity


class EducatorIdentity(UserIdentity):
    school: SchoolIdentity


class EducatorBrief(EducatorIdentity):
    school: UsersSchool
    # class_group: ClassGroupBrief | None


class EducatorDetail(UserDetail, EducatorBrief):
    educator_info: dict | None
