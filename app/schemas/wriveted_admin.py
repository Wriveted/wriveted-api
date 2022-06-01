from app.schemas.user import UserBrief, UserIdentity


class WrivetedAdminIdentity(UserIdentity):
    pass


class WrivetedAdminBrief(WrivetedAdminIdentity, UserBrief):
    pass


class WrivetedAdminInfo(WrivetedAdminBrief, UserInfo):
    wriveted_admin_info: dict | None
