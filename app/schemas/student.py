from app.schemas.reader import ReaderBrief, ReaderDetail, ReaderIdentity
from app.schemas.school import SchoolIdentity
from app.schemas.user import UsersSchool


class StudentIdentity(ReaderIdentity):
    school: SchoolIdentity


class StudentBrief(StudentIdentity, ReaderBrief):
    school: UsersSchool
    # class_group: ClassGroupBrief | None


class StudentDetail(ReaderDetail, StudentBrief):
    student_info: dict | None
