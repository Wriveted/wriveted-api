"""
DEPRECATED: Use app.repositories.event_repository instead.

This module is maintained for backward compatibility only.
"""

import warnings
from datetime import datetime
from typing import Any, Optional, Union

from sqlalchemy.exc import DataError, ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from structlog import get_logger

from app.crud import CRUDBase
from app.models import Event, ServiceAccount, User
from app.models.event import EventLevel
from app.models.school import School
from app.repositories.event_repository import event_repository
from app.schemas.events.event import EventCreateIn

logger = get_logger()


class CRUDEvent(CRUDBase[Event, EventCreateIn, Any]):
    """DEPRECATED: Use EventRepository from app.repositories instead."""

    def __init__(self, *args, **kwargs):
        warnings.warn(
            "CRUDEvent is deprecated. Use EventRepository from app.repositories.event_repository",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)

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
    ):
        """DEPRECATED: Delegates to event_repository.create()."""
        return event_repository.create(
            session=session,
            title=title,
            description=description,
            info=info,
            level=level,
            school=school,
            account=account,
            commit=commit,
        )

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
    ):
        """DEPRECATED: Delegates to event_repository.acreate()."""
        return await event_repository.acreate(
            session=session,
            title=title,
            description=description,
            info=info,
            level=level,
            school=school,
            account=account,
            commit=commit,
        )

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
        """DEPRECATED: Delegates to event_repository.get_all_with_optional_filters_query()."""
        return event_repository.get_all_with_optional_filters_query(
            db=db,
            query_string=query_string,
            match_prefix=match_prefix,
            level=level,
            school=school,
            user=user,
            service_account=service_account,
            info_jsonpath_match=info_jsonpath_match,
            since=since,
        )

    def get_log_levels_above_level(self, level):
        """DEPRECATED: Delegates to event_repository.get_log_levels_above_level()."""
        return event_repository.get_log_levels_above_level(level)

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
        """DEPRECATED: Delegates to event_repository.get_all_with_optional_filters()."""
        return event_repository.get_all_with_optional_filters(
            db=db,
            query_string=query_string,
            match_prefix=match_prefix,
            level=level,
            school=school,
            user=user,
            service_account=service_account,
            info_jsonpath_match=info_jsonpath_match,
            since=since,
            skip=skip,
            limit=limit,
        )

    def get_types(
        self,
        db: Session,
        level: EventLevel | None = None,
        skip: int = 0,
        limit: int = 100,
    ):
        """DEPRECATED: Delegates to event_repository.get_types()."""
        return event_repository.get_types(db=db, level=level, skip=skip, limit=limit)


event = CRUDEvent(Event)
