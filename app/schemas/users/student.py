from typing import Literal

from app.schemas.school_identity import SchoolIdentity
from app.schemas.users.reader import ReaderBrief, ReaderDetail, ReaderIdentity
from app.schemas.users.user import UsersSchool

# from app.schemas.class_group import ClassGroupBrief


class StudentIdentity(ReaderIdentity):
    type: Literal["student"]
    username: str
    school: SchoolIdentity


class StudentBrief(StudentIdentity, ReaderBrief):
    school: UsersSchool
    # class_group: ClassGroupBrief | None


class StudentDetail(ReaderDetail, StudentBrief):
    pass
