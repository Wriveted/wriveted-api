from pydantic import BaseModel

from app.schemas.recommendations import ReadingAbilityKey
from app.schemas.school import SchoolIdentity
from app.schemas.users.reader import ReaderBrief, ReaderDetail
from app.schemas.users.user import UsersSchool
from app.schemas.users.user_identity import ReaderIdentity


class StudentInfo(BaseModel):
    reading_ability_preference: ReadingAbilityKey | None
    age: int | None
    other: dict | None


class StudentIdentity(ReaderIdentity):
    school: SchoolIdentity


class StudentBrief(StudentIdentity, ReaderBrief):
    school: UsersSchool
    # class_group: ClassGroupBrief | None


class StudentDetail(ReaderDetail, StudentBrief):
    student_info: StudentInfo | None
