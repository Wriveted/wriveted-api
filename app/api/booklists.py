from typing import List, Union

from fastapi import APIRouter, Depends, Security, HTTPException
from fastapi_permissions import Allow, Authenticated
from sqlalchemy import delete, func, update, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette import status
from structlog import get_logger

from app import crud
from app.api.common.pagination import PaginatedQueryParams
from app.api.dependencies.booklist import get_booklist_from_wriveted_id
from app.api.dependencies.school import get_school_from_wriveted_id
from app.api.dependencies.security import get_current_active_user_or_service_account
from app.db.session import get_session
from app.models import School, BookList, User, ServiceAccount
from app.permissions import Permission
from app.schemas.booklist import (
    BookListDetail,
    BookListBrief,
    BookListsResponse,
    BookListCreateIn,
    BookListUpdateIn,
    ItemUpdateType,
)
from app.services.booklists import *
from app.services.events import create_event

logger = get_logger()

router = APIRouter(
    tags=["Booklists"],
    dependencies=[Security(get_current_active_user_or_service_account)],
)

# Placeholder bulk access control rules
bulk_booklist_access_control_list = [
    (Allow, Authenticated, "create"),
    (Allow, Authenticated, "read"),
    (Allow, Authenticated, "update"),
    (Allow, "role:admin", "delete"),
]


@router.post(
    "/lists",
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
    session: Session = Depends(get_session),
):
    logger.info("Creating a book list")
    try:
        if booklist.items is None:
            logger.info("Creating an empty book list")
            booklist.items = []

        booklist_orm_object = crud.booklist.create(
            db=session, obj_in=booklist, commit=True
        )

        create_event(
            session=session,
            title=f"Booklist created",
            description=f"{account.name} created booklist '{booklist.name}'",
            properties={
                "type": booklist.type,
                "id": str(booklist_orm_object.id),
            },
            account=account,
        )
        return booklist_orm_object

    except IntegrityError as e:
        logger.warning("Database integrity error while adding booklist", exc_info=e)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Couldn't create booklist",
        )


@router.get(
    "/lists",
    response_model=BookListsResponse,
)
async def get_booklists(
    pagination: PaginatedQueryParams = Depends(),
    session: Session = Depends(get_session),
):
    logger.debug("Getting list of booklists", pagination=pagination)
    booklists = crud.booklist.get_all(
        db=session, skip=pagination.skip, limit=pagination.limit
    )

    return BookListsResponse(
        pagination=pagination.to_dict(),
        data=booklists,
    )


@router.get(
    "/lists/{wriveted_identifier}",
    response_model=BookListDetail,
)
async def get_booklist_detail(
    booklist: BookList = Permission("read", get_booklist_from_wriveted_id),
    pagination: PaginatedQueryParams = Depends(),
    session: Session = Depends(get_session),
):
    logger.debug("Getting booklist", booklist=booklist)
    # item_query = booklist.items.statement.offset(pagination.skip).limit(pagination.limit)
    # logger.debug("Item query", query=str(item_query))
    # booklist_items = session.scalars(item_query).all()
    booklist_items = list(booklist.items)[
        pagination.skip : pagination.limit + pagination.skip
    ]
    logger.debug("Items", items=booklist_items)
    logger.debug("Returning paginated booklist", item_count=len(booklist_items))
    booklist.data = booklist_items
    booklist.pagination = pagination.to_dict()
    return BookListDetail.from_orm(booklist)


@router.patch(
    "/lists/{wriveted_identifier}",
    response_model=BookListBrief,
)
async def update_booklist(
    changes: BookListUpdateIn,
    booklist: BookList = Permission("update", get_booklist_from_wriveted_id),
    session: Session = Depends(get_session),
):
    logger.debug("Updating booklist", booklist=booklist)

    updated_booklist = crud.booklist.update(db=session, db_obj=booklist, obj_in=changes)

    return updated_booklist
