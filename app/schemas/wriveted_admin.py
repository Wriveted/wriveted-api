from app.schemas.users.user import UserDetail
from app.schemas.users.user_identity import UserBrief, UserIdentity


class WrivetedAdminIdentity(UserIdentity):
    pass


class WrivetedAdminBrief(WrivetedAdminIdentity, UserBrief):
    pass


class WrivetedAdminDetail(UserDetail, WrivetedAdminBrief):
    wriveted_admin_info: dict | None
