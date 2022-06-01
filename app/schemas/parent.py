from app.schemas.reader import ReaderIdentity
from app.schemas.user import UserBrief, UserDetail, UserIdentity


class ParentIdentity(UserIdentity):
    pass


class ParentBrief(UserBrief, ParentIdentity):
    children: list[ReaderIdentity]


class ParentDetail(UserDetail, ParentBrief):
    parent_info: dict | None
