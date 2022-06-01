from app.schemas.school import SchoolIdentity
from app.schemas.user import UserDetail, UserIdentity, UsersSchool


class EducatorIdentity(UserIdentity):
    school: SchoolIdentity


class EducatorBrief(EducatorIdentity):
    school: UsersSchool
    # class_group: ClassGroupBrief | None


class EducatorDetail(UserDetail, EducatorBrief):
    educator_info: dict | None
