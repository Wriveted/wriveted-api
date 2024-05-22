from datetime import datetime
from typing import Any, Union

from sqlalchemy import cast, distinct, func, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import DataError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession
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
        description, event = self._create_internal(
            account, description, info, level, school, title
        )
        session.add(event)
        if commit:
            session.commit()
            session.refresh(event)

        # If an event was worth recording in the database we probably also want to log it
        logger.info(
            f"{title} - {description}",
            level=level,
            school=school,
            account=account,
        )
        return event

    async def acreate(
        self,
        session: AsyncSession,
        title: str,
        description: str = None,
        info: dict = None,
        level: EventLevel = EventLevel.NORMAL,
        school: School = None,
        account: Union[ServiceAccount, User] = None,
        commit: bool = True,
    ):
        description, event = self._create_internal(
            account, description, info, level, school, title
        )
        session.add(event)
        if commit:
            await session.commit()
            await session.refresh(event)

        # If an event was worth recording in the database we probably also want to log it
        logger.info(
            f"{title} - {description}",
            level=level,
            school=school,
            account=account,
        )
        return event

    def _create_internal(self, account, description, info, level, school, title):
        description = description or ""
        info = info or {}
        user_id = account.id if isinstance(account, User) else None
        service_account_id = account.id if isinstance(account, ServiceAccount) else None
        school_id = school.id if school is not None else None
        info["description"] = description
        event = Event(
            title=title,
            info=info,
            level=level,
            school_id=school_id,
            user_id=user_id,
            service_account_id=service_account_id,
        )

        return description, event

    def get_all_with_optional_filters_query(
        self,
        db: Session,
        query_string: str | list[str] | None = None,
        match_prefix: bool | None = False,
        level: EventLevel | None = None,
        school: School | None = None,
        user: User | None = None,
        service_account: ServiceAccount | None = None,
        info_jsonpath_match: str = None,
        since: datetime | None = None,
    ):
        event_query = self.get_all_query(db=db, order_by=Event.timestamp.desc())

        if query_string is not None:
            if isinstance(query_string, str):
                query_string = [query_string]

            # https://docs.sqlalchemy.org/en/14/dialects/postgresql.html?highlight=search#full-text-search
            if match_prefix:
                filters = [
                    func.lower(Event.title).startswith(query.lower())
                    for query in query_string
                ]
            else:
                filters = [
                    func.lower(Event.title).contains(query.lower())
                    for query in query_string
                ]
            event_query = event_query.where(or_(*filters))

        if level is not None:
            included_levels = self.get_log_levels_above_level(level)
            event_query = event_query.where(Event.level.in_(included_levels))

        if school is not None:
            event_query = event_query.where(Event.school == school)

        if user is not None:
            event_query = event_query.where(Event.user == user)

        if service_account is not None:
            event_query = event_query.where(Event.service_account == service_account)

        if info_jsonpath_match is not None:
            # Apply the jsonpath filter to the info field
            event_query = event_query.where(
                func.jsonb_path_match(cast(Event.info, JSONB), info_jsonpath_match).is_(
                    True
                )
            )

        if since is not None:
            event_query = event_query.where(Event.timestamp >= since)

        return event_query

    def get_log_levels_above_level(self, level):
        # Include levels that are higher as well!
        logging_levels = ["debug", "normal", "warning", "error"]
        try:
            level_index = logging_levels.index(level)
        except ValueError:
            # If the level is not in the list, just use the highest level
            level_index = len(logging_levels) - 1
        included_levels = logging_levels[level_index:]
        return included_levels

    def get_all_with_optional_filters(
        self,
        db: Session,
        query_string: str | list[str] | None = None,
        match_prefix: bool | None = False,
        level: EventLevel | None = None,
        school: School | None = None,
        user: User | None = None,
        service_account: ServiceAccount | None = None,
        info_jsonpath_match: str | None = None,
        since: datetime | None = None,
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
            "info_jsonpath_match": info_jsonpath_match,
            "since": since,
        }
        logger.debug("Querying events", **optional_filters)
        query = self.apply_pagination(
            self.get_all_with_optional_filters_query(db=db, **optional_filters),
            skip=skip,
            limit=limit,
        )
        try:
            return db.scalars(query).all()
        except (ProgrammingError, DataError) as e:
            logger.error("Error querying events", error=e, **optional_filters)
            raise ValueError("Problem filtering events")

    def get_types(
        self,
        db: Session,
        level: EventLevel | None = None,
        skip: int = 0,
        limit: int = 100,
    ):
        s = select(distinct(Event.title))
        if level is not None:
            included_levels = self.get_log_levels_above_level(level)
            s = s.where(Event.level.in_(included_levels))

        query = self.apply_pagination(s, skip=skip, limit=limit)

        return db.scalars(query).all()


event = CRUDEvent(Event)
