from typing import List

from fastapi import APIRouter, Depends, Security
from pydantic import ValidationError
from sqlalchemy import delete, update, select
from sqlalchemy.orm import Session
from structlog import get_logger

from app import crud
from app.api.common.pagination import PaginatedQueryParams
from app.api.dependencies.school import get_school_from_wriveted_id
from app.api.dependencies.security import get_current_active_user_or_service_account
from app.db.session import get_session
from app.models import CollectionItem, School, Edition
from app.permissions import Permission
from app.schemas.collection import (
    CollectionItemBrief,
    CollectionUpdate,
    CollectionUpdateType,
    CollectionItemIn,
)
from app.schemas.edition import EditionCreateIn
from app.services.collections import add_editions_to_collection, add_editions_to_collection_by_isbn

logger = get_logger()

router = APIRouter(
    tags=["Schools"],
    dependencies=[
        # Shouldn't be necessary
        Security(get_current_active_user_or_service_account)
    ],
)


@router.get(
    "/school/{wriveted_identifier}/collection", response_model=List[CollectionItemBrief]
)
async def get_school_collection(
    school: School = Permission("read", get_school_from_wriveted_id),
    pagination: PaginatedQueryParams = Depends(),
    session: Session = Depends(get_session),
):
    logger.debug("Getting collection", pagination=pagination)
    collection_items = session.scalars(
        school.collection.statement.offset(pagination.skip).limit(pagination.limit)
    ).all()
    logger.debug("Loading collection", collection_size=len(collection_items))
    return collection_items


@router.post(
    "/school/{wriveted_identifier}/collection",
)
async def set_school_collection(
    collection_data: List[CollectionItemIn],
    school: School = Permission("update", get_school_from_wriveted_id),
    account=Depends(get_current_active_user_or_service_account),
    session: Session = Depends(get_session),
):
    """
    From a list of barebones Edition identifiers, get or create editions for each, then add
    to target school's collection. Primarily for the very first
    collection upload, but can be re-used if schools wish to add more
    editions later, using the same method.
    """
    logger.info(
        "Resetting the entire collection for school", school=school, account=account
    )
    session.execute(delete(CollectionItem).where(CollectionItem.school == school))
    session.commit()

    logger.info(
        f"Adding/syncing {len(collection_data)} ISBNs with school collection", school=school, account=account
    )
    if len(collection_data) > 0:
        isbns = [item.isbn for item in collection_data]
        await add_editions_to_collection_by_isbn(session, isbns, school, account)

    return {"msg": "updated"}


@router.patch(
    "/school/{wriveted_identifier}/collection",
)
async def update_school_collection(
    collection_update_data: List[CollectionUpdate],
    school: School = Permission("update", get_school_from_wriveted_id),
    account=Depends(get_current_active_user_or_service_account),
    session: Session = Depends(get_session),
):
    """
    Update a school library collection with a list of changes.

    Changes can be to add, remove, or update editions of books. Many
    changes of different types can be added in a single call to this
    API, they must however all refer to one school.

    If the edition are already in the Wriveted database only the ISBN
    and `"action"` is required. For example adding known editions to a
    collection can be achieved with entries of this form:

    ```json
    { "isbn": "XYZ", "action": "add" }
    ```

    Note: any unknown editions will be created as unhydrated, empty objects in the db.
    To provide metadata for new books, please use the `POST /editions` endpoint.

    ### Action Types

    - `add`
    - `remove`
    - `update` - change the `copies_total` and `copies_available`

    """
    logger.info("Updating collection for school", school=school, account=account)

    isbns_to_remove: List[str] = []
    isbns_to_add: List[str] = []

    for update_info in collection_update_data:
        if update_info.action == CollectionUpdateType.REMOVE:
            isbns_to_remove.append(update_info.isbn)
        elif update_info.action == CollectionUpdateType.ADD:
            isbns_to_add.append(update_info.isbn)
        elif update_info.action == CollectionUpdateType.UPDATE:
            # Update the "copies_total and "copies_available"
            # TODO consider a bulk update version of this
            stmt = (
                update(CollectionItem)
                .where(CollectionItem.school_id == school.id)
                .where(
                    # Note execution_options(synchronize_session="fetch") must be set
                    # for this subquery where clause to work.
                    # Ref https://docs.sqlalchemy.org/en/14/orm/session_basics.html#update-and-delete-with-arbitrary-where-clause
                    CollectionItem.edition.has(Edition.isbn == update_info.isbn)
                    # this is a more manual way that emits an IN instead of an EXISTS
                    # CollectionItem.edition_id.in_(
                    #     select(Edition.id).where(Edition.isbn == update_info.isbn).scalar_subquery()
                    # )
                    # TODO consider/try just using unit of work approach. Get the CollectionItem and update the
                    # fields directly, then at the end commit them.
                )
                .values(
                    copies_total=update_info.copies_total,
                    copies_available=update_info.copies_available,
                )
                .execution_options(synchronize_session="fetch")
            )

            session.execute(stmt)

    if len(isbns_to_remove) > 0:
        logger.info(f"Removing {len(isbns_to_remove)} items from collection")
        stmt = (
            delete(CollectionItem)
            .where(CollectionItem.school_id == school.id)
            .where(
                CollectionItem.edition_id.in_(
                    select(Edition.id).where(Edition.isbn.in_(isbns_to_remove))
                )
            )
            .execution_options(synchronize_session="fetch")
        )
        logger.info("Delete stmt", stmts=str(stmt))
        session.execute(stmt)

    if len(isbns_to_add) > 0:
        logger.info(f"Adding {len(isbns_to_add)} editions to collection")
        await add_editions_to_collection_by_isbn(session, isbns_to_add, school, account)

    logger.info(f"Committing transaction")
    session.commit()

    return {"msg": "updated"}
