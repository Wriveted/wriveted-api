from typing import Literal

from app.schemas.users.user import UserDetail
from app.schemas.users.user_identity import UserBrief


class WrivetedAdminBrief(UserBrief):
    type: Literal["wriveted"]


class WrivetedAdminDetail(UserDetail, WrivetedAdminBrief):
    pass
