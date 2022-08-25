import datetime
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Security
from fastapi_permissions import Allow, All
from pydantic import ValidationError
from sqlalchemy.orm import Session
from starlette import status
from structlog import get_logger

from app import crud
from app.api.common.pagination import PaginatedQueryParams
from app.api.dependencies.security import (
    create_user_access_token,
    get_active_principals,
    get_current_active_superuser_or_backend_service_account,
    get_current_active_user_or_service_account, get_current_active_user,
)
from app.api.dependencies.user import get_user_from_id
from app.db.session import get_session
from app.models.user import User, UserAccountType
from app.permissions import Permission
from app.schemas.auth import SpecificUserDetail
from app.schemas.pagination import Pagination
from app.schemas.users.user_create import UserCreateIn
from app.schemas.users.user_list import UserListsResponse
from app.schemas.users.user_update import InternalUserUpdateIn, UserUpdateIn

logger = get_logger()

router = APIRouter(
    tags=["Users"],
    dependencies=[Depends(get_current_active_user_or_service_account)],
)
"""
Bulk access control rules apply to calling the create and get lists endpoints.
Further access control is applied inside each endpoint.
"""
bulk_access_control_list = [
    (Allow, "role:admin", All),
    (Allow, "role:parent", "create"),
    (Allow, "role:parent", "read"),
    (Allow, "role:reader", "read"),
    (Allow, "role:parent", "update"),
    (Allow, "role:admin", "delete"),
]


@router.post(
    "/reader",
    response_model=SpecificUserDetail,
    dependencies=[Permission("create", bulk_access_control_list)],
)
async def create_reader(user_data: UserCreateIn, session: Session = Depends(get_session)):
    """
    Endpoint for parents to create a new reader profile.
    """
    logger.info("Creating a reader associated with parent")
    try:
        return crud.user.create(session, obj_in=user_data)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.get(
    "/readers",
    response_model=UserListsResponse,
    dependencies=[
        Permission("read", bulk_access_control_list)
    ]
)
async def get_reader_list(
        user = Depends(get_current_active_user)
):
    """
    List readers associated with current user.
    """
    logger.info("Retrieving reader list", user=user)

    # Get linked readers

    return user


@router.get("/readers/{user_id}", response_model=SpecificUserDetail)
async def get_reader_detail(user: User = Permission("read", get_user_from_id)):
    logger.info("Retrieving reader detail", user=user)
    return user


@router.delete("/readers/{uuid}")
async def deactivate_reader(
    uuid: str,
    purge: bool = False,
    account=Depends(get_current_active_superuser_or_backend_service_account),
    session: Session = Depends(get_session),
):
    """
    Mark reader as INACTIVE.

    If `purge` is `True` we instead delete the reader entirely from the database.

    Note purge will delete all associated events.
    """
    user = crud.user.get(db=session, id=uuid)
    logger.info("Request to delete a reader", user_to_delete=user, account=account)

    crud.event.create(
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
