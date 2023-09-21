from typing import Literal

from app.models.user import UserAccountType
from app.schemas.school_identity import SchoolIdentity
from app.schemas.users.reader import ReaderBrief, ReaderDetail, ReaderIdentity
from app.schemas.users.user import UsersSchool


class StudentIdentity(ReaderIdentity):
    type: Literal[UserAccountType.STUDENT]
    username: str
    school: SchoolIdentity


class StudentBrief(StudentIdentity, ReaderBrief):
    school: UsersSchool
    # class_group: ClassGroupBrief | None


class StudentDetail(ReaderDetail, StudentBrief):
    pass
