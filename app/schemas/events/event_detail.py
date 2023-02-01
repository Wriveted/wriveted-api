from app.schemas.events.event import EventBrief
from app.schemas.pagination import PaginatedResponse
from app.schemas.school_identity import SchoolWrivetedIdentity
from app.schemas.service_account import ServiceAccountBrief
from app.schemas.users.user_identity import UserIdentity


class EventDetail(EventBrief):
    school: SchoolWrivetedIdentity | None
    user: UserIdentity | None
    service_account: ServiceAccountBrief | None


class EventListsResponse(PaginatedResponse):
    data: list[EventDetail]