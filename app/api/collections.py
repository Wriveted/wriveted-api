from typing import List

from fastapi import APIRouter, Depends, Security
from pydantic import ValidationError
from sqlalchemy import delete, update, select
from sqlalchemy.orm import Session
from structlog import get_logger

from app import crud
from app.api.common.pagination import PaginatedQueryParams
from app.api.dependencies.school import get_school_from_path
from app.api.dependencies.security import get_current_active_user_or_service_account
from app.db.session import get_session
from app.models import CollectionItem, School, Edition
from app.permissions import Permission
from app.schemas.collection import CollectionItemBrief, CollectionUpdate, CollectionUpdateType, CollectionItemIn
from app.schemas.edition import EditionCreateIn
from app.services.collections import add_editions_to_collection

logger = get_logger()

router = APIRouter(
    tags=["Schools"],
    dependencies=[
        # Shouldn't be necessary
        Security(get_current_active_user_or_service_account)
    ]
)


@router.get("/school/{country_code}/{school_id}/collection",
            response_model=List[CollectionItemBrief])
async def get_school_collection(
        school: School = Permission("read", get_school_from_path),
        pagination: PaginatedQueryParams = Depends(),
        session: Session = Depends(get_session)
):
    logger.debug("Getting collection", pagination=pagination)
    collection_items = session.scalars(
        school.collection.statement.offset(pagination.skip).limit(pagination.limit)
    ).all()
    logger.debug("Loading collection", collection_size=len(collection_items))
    return collection_items


@router.post(
    "/school/{country_code}/{school_id}/collection",
)
async def set_school_collection(
        collection_data: List[CollectionItemIn],
        school: School = Permission("update", get_school_from_path),
        account=Depends(get_current_active_user_or_service_account),
        session: Session = Depends(get_session)
):
    """
    Replace a school library collection entirely
    """
    logger.info("Resetting the entire collection for school", school=school, account=account)
    session.execute(delete(CollectionItem).where(CollectionItem.school == school))
    session.commit()
    if len(collection_data) > 0:
        await add_editions_to_collection(session, collection_data, school, account)

    return {
        'msg': "updated"
    }


@router.put("/school/{country_code}/{school_id}/collection", )
async def update_school_collection(
        collection_update_data: List[CollectionUpdate],
        school: School = Permission("update", get_school_from_path),
        account=Depends(get_current_active_user_or_service_account),
        session: Session = Depends(get_session)
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
    { "ISBN": "XYZ", "action": "add" }
    ```

    Note any unknown editions will not get included in the update, a list of ISBNs
    that were skipped can be found in the response.

    ### Action Types

    - `add`
    - `remove`
    - `update` - change the `copies_total` and `copies_available`

    ### Adding an unknown work to a collection

    In the case where an edition is not yet in the Wriveted database some more
    information can be provided in the update to automatically add the edition.
    Alternatively, missing Works and Editions can be created using their direct
    endpoints.

    The optional key `edition_info` can be provided for each addition, with the
    same format as the `POST /edition` endpoint.

    """
    logger.info("Updating collection for school", school=school, account=account)

    isbns_to_remove = []
    editions_to_add: List[EditionCreateIn] = []
    skipped_editions: List[str] = []

    for update_info in collection_update_data:
        if update_info.action == CollectionUpdateType.REMOVE:
            isbns_to_remove.append(update_info.ISBN)
        elif update_info.action == CollectionUpdateType.ADD:
            if update_info.edition_info is None:
                # this is a bit hacky and slow.
                # Perhaps better is to query all the ISBNs before looping, or
                # allow the API to throw errors or just require the full EditionCreateIn data for every add
                try:
                    update_info.edition_info = EditionCreateIn.parse_obj(crud.edition.get(session, id=update_info.ISBN))
                    logger.debug("Edition to add", new_edition=update_info.edition_info)
                except ValidationError:
                    # The caller didn't give us information, and we don't
                    # have this edition in the database. We will skip and report this to the caller.
                    skipped_editions.append(update_info.ISBN)
            else:

                editions_to_add.append(update_info.edition_info)
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
                        CollectionItem.edition.has(Edition.ISBN == update_info.ISBN)

                        # this is a more manual way that emits an IN instead of an EXISTS
                        # CollectionItem.edition_id.in_(
                        #     select(Edition.id).where(Edition.ISBN == update_info.ISBN).scalar_subquery()
                        # )

                        # TODO consider/try just using unit of work approach. Get the CollectionItem and update the
                        # fields directly, then at the end commit them.

                    )
                    .values(
                        copies_total=update_info.copies_total,
                        copies_available=update_info.copies_available
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
                        select(Edition.id).where(Edition.ISBN.in_(isbns_to_remove))
                    )
                )
                .execution_options(synchronize_session="fetch")
        )
        logger.info("Delete stmt", stmts=str(stmt))
        session.execute(stmt)

    if len(editions_to_add) > 0:
        logger.info(f"Adding {len(editions_to_add)} editions to collection")
        await add_editions_to_collection(session, editions_to_add, school, account)

    logger.info(f"Committing transaction")
    session.commit()

    return {
        'msg': "updated",
        "skipped": skipped_editions
    }
