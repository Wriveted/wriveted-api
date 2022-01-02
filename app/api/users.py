from typing import List

from fastapi import Depends, APIRouter
from sqlalchemy.orm import Session
from structlog import get_logger

from app import crud
from app.api.common.pagination import PaginatedQueryParams
from app.api.dependencies.security import get_current_active_superuser_or_backend_service_account, \
    get_current_active_user_or_service_account
from app.db.session import get_session
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
        pagination: PaginatedQueryParams = Depends(),
        session: Session = Depends(get_session)
):
    """
    List all users
    """
    logger.info("Listing users")
    return crud.user.get_all(db=session, skip=pagination.skip, limit=pagination.limit)


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


@router.delete("/users/{uuid}")
async def deactivate_user(
        uuid: str,
        purge: bool = False,
        account = Depends(get_current_active_user_or_service_account),
        session: Session = Depends(get_session)
):
    """
    Mark user INACTIVE.

    Delete user entirely from database if `purge` is `True`.

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