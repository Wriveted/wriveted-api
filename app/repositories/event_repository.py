"""
Event repository - domain-focused data access for Event domain.

Replaces the generic CRUDEvent class with proper repository pattern.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Union

from sqlalchemy import cast, distinct, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import DataError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from structlog import get_logger

from app.models import Event, ServiceAccount, User
from app.models.event import EventLevel
from app.models.school import School

logger = get_logger()


class EventRepository(ABC):
    """Repository interface for Event domain operations."""

    @abstractmethod
    def create(
        self,
        session: Session,
        title: str,
        description: Optional[str] = None,
        info: Optional[dict] = None,
        level: EventLevel = EventLevel.NORMAL,
        school: Optional[School] = None,
        account: Optional[Union[ServiceAccount, User]] = None,
        commit: bool = True,
    ) -> Event:
        """Create an event with structured logging."""
        pass

    @abstractmethod
    async def acreate(
        self,
        session: AsyncSession,
        title: str,
        description: Optional[str] = None,
        info: Optional[dict] = None,
        level: EventLevel = EventLevel.NORMAL,
        school: Optional[School] = None,
        account: Optional[Union[ServiceAccount, User]] = None,
        commit: bool = True,
    ) -> Event:
        """Async version of create."""
        pass

    @abstractmethod
    def get_or_404(self, db: Session, id: str) -> Event:
        """Get an event by ID or raise 404."""
        pass

    @abstractmethod
    def get_by_id(self, db: Session, event_id: str):
        """Get an event by its ID."""
        pass

    @abstractmethod
    def get_all_with_optional_filters_query(
        self,
        db: Session,
        query_string: str | list[str] | None = None,
        match_prefix: bool | None = False,
        level: EventLevel | None = None,
        school: School | None = None,
        user: User | None = None,
        service_account: ServiceAccount | None = None,
        info_jsonpath_match: Optional[str] = None,
        since: datetime | None = None,
    ):
        """Build a query with optional filters for events."""
        pass

    @abstractmethod
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
    ) -> list[Event]:
        """Get events with optional filters and pagination."""
        pass

    @abstractmethod
    def get_types(
        self,
        db: Session,
        level: EventLevel | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[str]:
        """Get distinct event titles (types)."""
        pass

    @abstractmethod
    def get_log_levels_above_level(self, level: EventLevel) -> list[str]:
        """Get all log levels at or above the specified level."""
        pass

    @abstractmethod
    def apply_pagination(self, query, skip: int = 0, limit: int = 100):
        """Apply pagination to a query."""
        pass


class EventRepositoryImpl(EventRepository):
    """Implementation of EventRepository."""

    def get_by_id(self, db: Session, event_id: str):
        """Get an event by its ID."""
        return db.get(Event, event_id)

    def get_or_404(self, db: Session, id: str) -> Event:
        """Get an event by ID or raise 404."""
        from fastapi import HTTPException

        event = self.get_by_id(db, id)
        if not event:
            raise HTTPException(status_code=404, detail=f"Event with id {id} not found")
        return event

    def create(
        self,
        session: Session,
        title: str,
        description: Optional[str] = None,
        info: Optional[dict] = None,
        level: EventLevel = EventLevel.NORMAL,
        school: Optional[School] = None,
        account: Optional[Union[ServiceAccount, User]] = None,
        commit: bool = True,
    ) -> Event:
        """Create an event with structured logging."""
        description, event = self._create_internal(
            account, description, info, level, school, title
        )
        session.add(event)
        if commit:
            session.commit()
            session.refresh(event)

        logger.info(f"{title} - {description}", level=level)
        return event

    async def acreate(
        self,
        session: AsyncSession,
        title: str,
        description: Optional[str] = None,
        info: Optional[dict] = None,
        level: EventLevel = EventLevel.NORMAL,
        school: Optional[School] = None,
        account: Optional[Union[ServiceAccount, User]] = None,
        commit: bool = True,
    ) -> Event:
        """Async version of create."""
        description, event = self._create_internal(
            account, description, info, level, school, title
        )
        session.add(event)
        if commit:
            await session.commit()
            await session.refresh(event)

        logger.info(
            f"{title} - {description}",
            level=level,
            school=school,
            account_id=account.id if account else None,
        )
        return event

    def _create_internal(self, account, description, info, level, school, title):
        """Internal helper for event creation."""
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
        info_jsonpath_match: Optional[str] = None,
        since: datetime | None = None,
    ):
        """Build a query with optional filters for events."""
        event_query = select(Event).order_by(Event.timestamp.desc())

        if query_string is not None:
            if isinstance(query_string, str):
                query_string = [query_string]

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
            if filters:
                if len(filters) == 1:
                    event_query = event_query.where(filters[0])
                else:
                    combined_filter = filters[0]
                    for f in filters[1:]:
                        combined_filter = combined_filter | f
                    event_query = event_query.where(combined_filter)

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
            event_query = event_query.where(
                func.jsonb_path_match(cast(Event.info, JSONB), info_jsonpath_match).is_(
                    True
                )
            )

        if since is not None:
            event_query = event_query.where(Event.timestamp >= since)

        return event_query

    def get_log_levels_above_level(self, level: EventLevel) -> list[str]:
        """Get all log levels at or above the specified level."""
        logging_levels = ["debug", "normal", "warning", "error"]
        try:
            level_index = logging_levels.index(level)
        except ValueError:
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
    ) -> list[Event]:
        """Get events with optional filters and pagination."""
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
    ) -> list[str]:
        """Get distinct event titles (types)."""
        s = select(distinct(Event.title))
        if level is not None:
            included_levels = self.get_log_levels_above_level(level)
            s = s.where(Event.level.in_(included_levels))

        query = self.apply_pagination(s, skip=skip, limit=limit)

        return db.scalars(query).all()

    def apply_pagination(self, query, skip: int = 0, limit: int = 100):
        """Apply pagination to a query."""
        return query.offset(skip).limit(limit)


# Singleton instance
event_repository = EventRepositoryImpl()
