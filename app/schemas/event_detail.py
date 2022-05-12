from app.schemas.event import EventBrief
from app.schemas.school import SchoolWrivetedIdentity
from app.schemas.service_account import ServiceAccountBrief
from app.schemas.user import UserIdentity


class EventDetail(EventBrief):
    school: SchoolWrivetedIdentity | None
    user: UserIdentity | None
    service_account: ServiceAccountBrief | None
