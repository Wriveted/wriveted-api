from typing import Literal

from app.models.user import UserAccountType
from app.schemas.users.user import UserDetail
from app.schemas.users.user_identity import UserBrief


class WrivetedAdminBrief(UserBrief):
    type: Literal[UserAccountType.WRIVETED]


class WrivetedAdminDetail(UserDetail, WrivetedAdminBrief):
    pass
