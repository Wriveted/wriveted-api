from app.schemas.pagination import PaginatedResponse
from app.schemas.users import UserBrief
from app.schemas.users.educator import EducatorBrief
from app.schemas.users.parent import ParentBrief
from app.schemas.users.reader import ReaderBrief
from app.schemas.users.school_admin import SchoolAdminBrief
from app.schemas.users.student import StudentBrief
from app.schemas.users.wriveted_admin import WrivetedAdminBrief

SpecificUserBrief = (
    StudentBrief
    | ReaderBrief
    | SchoolAdminBrief
    | EducatorBrief
    | ParentBrief
    | WrivetedAdminBrief
    | UserBrief
)


class UserListsResponse(PaginatedResponse):
    data: list[SpecificUserBrief]
