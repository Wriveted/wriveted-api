from typing import Literal

from pydantic import BaseModel

from app.schemas.recommendations import ReadingAbilityKey
from app.schemas.school_identity import SchoolIdentity
from app.schemas.users.reader import ReaderBrief, ReaderDetail, ReaderIdentity
from app.schemas.users.user import UsersSchool


class StudentInfo(BaseModel):
    reading_ability_preference: ReadingAbilityKey | None
    age: int | None
    other: dict | None


class StudentIdentity(ReaderIdentity):
    type: Literal["student"]
    school: SchoolIdentity


class StudentBrief(StudentIdentity, ReaderBrief):
    school: UsersSchool
    # class_group: ClassGroupBrief | None


class StudentDetail(ReaderDetail, StudentBrief):
    student_info: StudentInfo | None
