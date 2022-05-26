from typing import List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi_permissions import Allow, Authenticated, has_permission, All, Deny
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette import status
from structlog import get_logger

from app import crud
from app.api.common.pagination import PaginatedQueryParams
from app.api.dependencies.booklist import get_booklist_from_wriveted_id
from app.api.dependencies.security import (
    get_active_principals,
    get_current_active_user_or_service_account,
)
from app.db.session import get_session
from app.models import BookList, ServiceAccount, User
from app.models.booklist import ListType
from app.permissions import Permission

from app.schemas.pagination import Pagination

logger = get_logger()


router = APIRouter(
    tags=["Schools"],
    dependencies=[Security(get_current_active_user_or_service_account)],
)

"""
Bulk access control rules apply to calling the create and get classes endpoints.

Further access control is applied inside each endpoint.
"""
bulk_class_access_control_list = [
    (Allow, Authenticated, "read"),
    (Allow, "role:admin", All),
    (Allow, "role:teacher", All),
]


@router.get(
    "/classes",
    response_model=ClassesResponse,
)
async def get_classes(
    pagination: PaginatedQueryParams = Depends(),
    principals: List = Depends(get_active_principals),
    session: Session = Depends(get_session),
):
    """
    Retrieve a filtered list of Book Lists.


    """

@router.post(
    "/list",
    dependencies=[
        Permission("create", bulk_booklist_access_control_list),
    ],
    response_model=BookListBrief,
)
async def add_booklist(
    booklist: BookListCreateIn,
    account: Union[User, ServiceAccount] = Depends(
        get_current_active_user_or_service_account
    ),
    principals: List = Depends(get_active_principals),
    session: Session = Depends(get_session),
):
    logger.info("Creating a book list", account=account, type=booklist.type)