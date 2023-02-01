import uuid
from typing import Any, Union

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
        match_prefix: bool | None = False,
        level: EventLevel | None = None,
        school: School | None = None,
        user: User | None = None,
        service_account: ServiceAccount | None = None,
        info_filters: dict[str, str | int | uuid.UUID] | None = None,
    ):
        event_query = self.get_all_query(db=db, order_by=Event.timestamp.desc())

        if query_string is not None:
            # https://docs.sqlalchemy.org/en/14/dialects/postgresql.html?highlight=search#full-text-search
            if match_prefix:
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
        if info_filters is not None:
            for key, value in info_filters.items():
                if isinstance(value, bool):
                    # convert Python bool to Postgres/JSON bool string
                    value = str(value).lower()

                # We cast the value to a string for simplicity, some info fields are ints or UUIDs
                event_query = event_query.where(
                    Event.info[key].as_string() == str(value)
                )

        return event_query

    def get_all_with_optional_filters(
        self,
        db: Session,
        query_string: str | None = None,
        match_prefix: bool | None = False,
        level: EventLevel | None = None,
        school: School | None = None,
        user: User | None = None,
        service_account: ServiceAccount | None = None,
        info_filters: dict[str, str | int | uuid.UUID] | None = None,
        skip: int = 0,
        limit: int = 100,
    ):
        optional_filters = {
            "query_string": query_string,
            "match_prefix": match_prefix,
            "level": level,
            "school": school,
            "user": user,
            "service_account": service_account,
            "info_filters": info_filters,
        }
        logger.debug("Querying events", **optional_filters)
        query = self.apply_pagination(
            self.get_all_with_optional_filters_query(db=db, **optional_filters),
            skip=skip,
            limit=limit,
        )
        return db.scalars(query).all()


event = CRUDEvent(Event)
