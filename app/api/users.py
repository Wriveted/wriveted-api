from typing import List, Optional

from fastapi import Depends, APIRouter, Query
from sqlalchemy.orm import Session
from structlog import get_logger

from app import crud
from app.api.common.pagination import PaginatedQueryParams
from app.api.dependencies.security import get_current_active_superuser_or_backend_service_account, \
    get_current_active_user_or_service_account
from app.db.session import get_session
from app.models.user import UserAccountType
from app.schemas.user import UserBrief, UserDetail, UserUpdateIn
from app.services.events import create_event

logger = get_logger()

router = APIRouter(
    tags=["Security"],
    dependencies=[
        Depends(get_current_active_superuser_or_backend_service_account)
    ]
)


@router.get("/users", response_model=List[UserBrief])
async def get_users(
        q: Optional[str] = Query(None, description='Filter users by name'),
        is_active: Optional[bool] = Query(None, description="Return active or inactive users. Default is all."),
        type: Optional[UserAccountType] = Query(None, description="Filter users by account type. Default is all."),
        pagination: PaginatedQueryParams = Depends(),
        session: Session = Depends(get_session)
):
    """
    List all users
    """
    logger.info("Listing users")
    return crud.user.get_all_with_optional_filters(
        db=session,
        query_string=q,
        is_active=is_active,
        type=type,
        skip=pagination.skip,
        limit=pagination.limit
    )


@router.get("/user/{uuid}", response_model=UserDetail)
async def get_user(
        uuid: str,
        session: Session = Depends(get_session)
):
    logger.info("Retrieving details on one user")
    return crud.user.get(db=session, id=uuid)


@router.put("/user/{uuid}", response_model=UserDetail)
async def update_user(
        uuid: str,
        user_update: UserUpdateIn,
        session: Session = Depends(get_session)
):
    logger.info("Updating a user")
    user = crud.user.get(db=session, id=uuid)

    updated_user = crud.user.update(session, db_obj=user, obj_in=user_update)
    return updated_user


@router.delete("/user/{uuid}")
async def deactivate_user(
        uuid: str,
        purge: bool = False,
        account = Depends(get_current_active_user_or_service_account),
        session: Session = Depends(get_session)
):
    """
    Mark user INACTIVE.

    If `purge` is `True` we instead delete the user entirely from the database.
    Note the user can then sign up again and a purge will delete all associated events.
    """
    user = crud.user.get(db=session, id=uuid)
    logger.info("Request to delete a user", user_to_delete=user, account=account)

    create_event(
        title="User account deleted",
        description=f"User {user.name} marked inactive by {account}",
        account=account,
        session=session
    )
    user.is_active = False
    session.flush()

    if purge:
        logger.info("Trying to purge user", user=user)
        session.delete(user)

    session.commit()
    return "ok"
