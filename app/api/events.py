from typing import List, Union
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi_permissions import has_permission
from sqlalchemy.orm import Session
from starlette import status
from structlog import get_logger

from app import crud
from app.api.common.pagination import PaginatedQueryParams
from app.api.dependencies.security import (
    get_active_principals,
    get_current_active_user_or_service_account,
)
from app.db.session import get_session
from app.models.event import EventLevel
from app.models.service_account import ServiceAccount
from app.models.user import User
from app.schemas.event import EventCreateIn
from app.schemas.event_detail import EventDetail, EventListsResponse
from app.schemas.pagination import Pagination
from app.services.background_tasks import queue_background_task

logger = get_logger()

router = APIRouter(
    tags=["Events"],
    dependencies=[Security(get_current_active_user_or_service_account)],
)


@router.post("/events", response_model=EventDetail)
async def create(
    data: EventCreateIn,
    account: Union[ServiceAccount, User] = Depends(
        get_current_active_user_or_service_account
    ),
    principals: List = Depends(get_active_principals),
    session: Session = Depends(get_session),
):
    if data.school_id is not None:
        school = crud.school.get_by_wriveted_id_or_404(
            db=session, wriveted_id=data.school_id
        )
        if (
            not has_permission(principals, "read", school)
            and "role:kiosk" not in principals
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"The current account is not allowed to create an event associated with that school",
            )
    else:
        school = None

    event = crud.event.create(
        session=session,
        title=data.title,
        description=data.description,
        info=data.info,
        level=data.level,
        school=school,
        account=account,
    )

    # Queue a background task to process the created event
    queue_background_task(
        "process-event",
        {"event_id": str(event.id)},
    )

    return event


@router.get("/events", response_model=EventListsResponse)
async def get_events(
    query: str = None,
    level: EventLevel = None,
    school_id: UUID = None,
    user_id: UUID = None,
    service_account_id: UUID = None,
    pagination: PaginatedQueryParams = Depends(),
    account: Union[ServiceAccount, User] = Depends(
        get_current_active_user_or_service_account
    ),
    principals: List = Depends(get_active_principals),
    session: Session = Depends(get_session),
):
    """
    Get a filtered and paginated list of events.

    Note in most cases you will need to provide a school or user to filter events
    by.
    """

    # We will filter the events before returning them, but we want to avoid
    # querying the database for all events if the user isn't allowed to get
    # all events.
    if school_id is None and user_id is None:
        # Only admins can get events across all users & schools
        if "role:admin" not in principals:
            logger.debug("Forbidding unfiltered event request for non admin user")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"The current account is not allowed to request global events. Try filtering by your school or user.",
            )

    # At this point we know that we have either a school id, a user id or the request is from an admin
    if user_id is not None:
        user = crud.user.get_or_404(db=session, id=user_id)
        if not has_permission(principals, "read", user):
            logger.warning(
                "Forbidden event request due to lack of permissions to read user account"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"The current account is not allowed to filter events associated with that user",
            )
    else:
        user = None

    service_account = (
        crud.service_account.get_or_404(db=session, id=service_account_id)
        if service_account_id
        else None
    )

    if school_id is not None:
        school = crud.school.get_by_wriveted_id_or_404(
            db=session, wriveted_id=school_id
        )
        if not has_permission(principals, "read", school):
            logger.warning(
                "Forbidden event request due to to lack of read permission on school"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"The current account is not allowed to filter events associated with that school",
            )
    else:
        school = None

    events = crud.event.get_all_with_optional_filters(
        session,
        query_string=query,
        level=level,
        school=school,
        user=user,
        service_account=service_account,
        skip=pagination.skip,
        limit=pagination.limit,
    )
    filtered_events = [e for e in events if has_permission(principals, "read", e)]
    if len(filtered_events) != len(events):
        logger.info(
            f"Filtering out {len(events)-len(filtered_events)} events", account=account
        )

    return EventListsResponse(
        pagination=Pagination(**pagination.to_dict(), total=None), data=filtered_events
    )
