from app.schemas.user import UserBrief, UserDetail, UserIdentity


class WrivetedAdminIdentity(UserIdentity):
    pass


class WrivetedAdminBrief(WrivetedAdminIdentity, UserBrief):
    pass


class WrivetedAdminDetail(UserDetail, WrivetedAdminBrief):
    wriveted_admin_info: dict | None
