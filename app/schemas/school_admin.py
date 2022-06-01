from app.schemas.educator import EducatorBrief, EducatorDetail, EducatorIdentity
from app.schemas.user import UserDetail


class SchoolAdminIdentity(EducatorIdentity):
    pass


class SchoolAdminBrief(EducatorBrief, SchoolAdminIdentity):
    pass


class SchoolAdminDetail(EducatorDetail, UserDetail, SchoolAdminBrief):
    school_admin_info: dict | None
