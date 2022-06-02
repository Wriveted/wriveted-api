from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.schemas.reader import ReaderIdentity    

from app.schemas.user import UserBrief, UserDetail, UserIdentity


class ParentIdentity(UserIdentity):
    pass


class ParentBrief(UserBrief, ParentIdentity):
    children: list[ReaderIdentity]


class ParentDetail(UserDetail, ParentBrief):
    parent_info: dict | None
