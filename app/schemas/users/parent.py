from __future__ import annotations

from app.schemas.users import ParentIdentity
from app.schemas.users.user import UserDetail
from app.schemas.users.user_identity import ReaderIdentity, UserBrief


class ParentBrief(UserBrief, ParentIdentity):
    children: list[ReaderIdentity]


class ParentDetail(UserDetail, ParentBrief):
    parent_info: dict | None
