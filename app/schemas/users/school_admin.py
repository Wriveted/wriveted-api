from app.schemas.users.educator import EducatorBrief, EducatorDetail, EducatorIdentity
from app.schemas.users.user import UserDetail


class SchoolAdminIdentity(EducatorIdentity):
    pass


class SchoolAdminBrief(EducatorBrief, SchoolAdminIdentity):
    pass


class SchoolAdminDetail(EducatorDetail, UserDetail, SchoolAdminBrief):
    school_admin_info: dict | None
