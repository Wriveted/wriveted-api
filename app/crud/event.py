from typing import Any, Optional, Union

from sqlalchemy import func
from sqlalchemy.orm import Session
from structlog import get_logger

from app.crud import CRUDBase
from app.models import Event, ServiceAccount, User
from app.models.event import EventLevel
from app.models.school import School
from app.schemas.events.event import EventCreateIn

logger = get_logger()


class CRUDEvent(CRUDBase[Event, EventCreateIn, Any]):
    def create(
        self,
        session: Session,
        title: str,
        description: str = None,
        info: dict = None,
        level: EventLevel = EventLevel.NORMAL,
        school: School = None,
        account: Union[ServiceAccount, User] = None,
        commit: bool = True,
    ):
        description = description or ""
        info = info or {}
        user = account if isinstance(account, User) else None
        service_account = account if isinstance(account, ServiceAccount) else None
        info["description"] = description
        event = Event(
            title=title,
            info=info,
            level=level,
            school=school,
            user=user,
            service_account=service_account,
        )
        session.add(event)
        if commit:
            session.commit()
            session.refresh(event)

        # If an event was worth recording in the database we probably also want to log it
        logger.info(
            f"{title}\n{description}",
            level=level,
            school=school,
            user=user,
            service_account=service_account,
        )
        return event

    def get_all_with_optional_filters_query(
        self,
        db: Session,
        query_string: str | None = None,
        starts_with: bool | None = False,
        level: EventLevel | None = None,
        school: School | None = None,
        user: User | None = None,
        service_account: ServiceAccount | None = None,
    ):
        event_query = self.get_all_query(db=db, order_by=Event.timestamp.desc())

        if query_string is not None:
            # https://docs.sqlalchemy.org/en/14/dialects/postgresql.html?highlight=search#full-text-search
            if starts_with:
                event_query = event_query.filter(
                    func.lower(Event.title).startswith(query_string.lower())
                )
            else:
                event_query = event_query.where(
                    func.lower(Event.title).contains(query_string.lower())
                )
        if level is not None:
            event_query = event_query.where(Event.level == level)
        if school is not None:
            event_query = event_query.where(Event.school == school)
        if user is not None:
            event_query = event_query.where(Event.user == user)
        if service_account is not None:
            event_query = event_query.where(Event.service_account == service_account)

        return event_query

    def get_all_with_optional_filters(
        self,
        db: Session,
        query_string: str | None = None,
        starts_with: bool | None = False,
        level: EventLevel | None = None,
        school: School | None = None,
        user: User | None = None,
        service_account: ServiceAccount | None = None,
        skip: int = 0,
        limit: int = 100,
    ):
        optional_filters = {
            "query_string": query_string,
            "starts_with": starts_with,
            "level": level,
            "school": school,
            "user": user,
            "service_account": service_account,
        }
        logger.debug("Querying events", **optional_filters)
        query = self.apply_pagination(
            self.get_all_with_optional_filters_query(db=db, **optional_filters),
            skip=skip,
            limit=limit,
        )
        return db.scalars(query).all()


event = CRUDEvent(Event)
