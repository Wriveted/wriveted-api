import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Security
from sqlalchemy.orm import Session
from structlog import get_logger

from app import crud
from app.api.common.pagination import PaginatedQueryParams
from app.api.dependencies.security import (
    create_user_access_token,
    get_current_active_superuser_or_backend_service_account,
    get_current_active_user_or_service_account,
    get_current_user,
)
from app.db.session import get_session
from app.models.user import User, UserAccountType
from app.schemas.user import UserBrief, UserDetail, UserPatchOptions, UserUpdateIn
from app.services.events import create_event

logger = get_logger()

router = APIRouter(
    tags=["Users"],
    dependencies=[Depends(get_current_active_superuser_or_backend_service_account)],
)

public_router = APIRouter(tags=["Public", "Users"])


@router.get("/users", response_model=List[UserBrief])
async def get_users(
    q: Optional[str] = Query(None, description="Filter users by name"),
    is_active: Optional[bool] = Query(
        None, description="Return active or inactive users. Default is all."
    ),
    type: Optional[UserAccountType] = Query(
        None, description="Filter users by account type. Default is all."
    ),
    pagination: PaginatedQueryParams = Depends(),
    session: Session = Depends(get_session),
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
        limit=pagination.limit,
    )


@router.get("/user/{uuid}", response_model=UserDetail)
async def get_user(uuid: str, session: Session = Depends(get_session)):
    logger.info("Retrieving details on one user")
    return crud.user.get(db=session, id=uuid)


@router.put("/user/{uuid}", response_model=UserDetail)
async def update_user(
    uuid: str, user_update: UserUpdateIn, session: Session = Depends(get_session)
):
    logger.info("Updating a user")
    user = crud.user.get(db=session, id=uuid)

    updated_user = crud.user.update(session, db_obj=user, obj_in=user_update)
    return updated_user


@router.post(
    "/user/{uuid}/auth-token",
    responses={
        401: {"description": "Unauthorized"},
        422: {"description": "Invalid data"},
    },
)
def magic_link_endpoint(
    uuid: str,
    session: Session = Depends(get_session),
):
    """
    Create a Wriveted API magic-link token for a user.
    """
    user = crud.user.get(db=session, id=uuid)
    logger.info("Generating magic link access-token for user", user=user)
    wriveted_access_token = create_user_access_token(
        user, expires_delta=datetime.timedelta(days=90)
    )
    return {
        "access_token": wriveted_access_token,
        "token_type": "bearer",
    }


@public_router.patch("/user")
async def patch_update_user(
    patch: UserPatchOptions,
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Optional patch updates to less-essential parts of a User object.
    Self-serve api that extracts the user's info from the bearer token
    (Cannot patch another user)
    """
    output = {}

    if patch.newsletter is not None:
        output["old_newsletter_preference"] = user.newsletter
        user.newsletter = patch.newsletter
        output["new_newsletter_preference"] = user.newsletter

    session.commit()

    return output


@router.delete("/user/{uuid}")
async def deactivate_user(
    uuid: str,
    purge: bool = False,
    account=Depends(get_current_active_user_or_service_account),
    session: Session = Depends(get_session),
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
        session=session,
    )
    user.is_active = False
    session.flush()

    if purge:
        logger.info("Trying to purge user", user=user)
        session.delete(user)

    session.commit()
    return "ok"
