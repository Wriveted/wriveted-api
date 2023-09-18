from __future__ import annotations

from typing import Literal

from app.schemas.subscription import SubscriptionBrief, SubscriptionDetail
from app.schemas.users.reader import ReaderIdentity
from app.schemas.users.user import UserDetail
from app.schemas.users.user_identity import UserBrief


class ParentBrief(UserBrief):
    type: Literal["parent"]
    children: list[ReaderIdentity]
    subscription: SubscriptionBrief | None = None


class ParentDetail(UserDetail, ParentBrief):
    parent_info: dict | None = None
    subscription: SubscriptionDetail | None = None
