from typing import List

from fastapi import APIRouter, Depends, Security
from sqlalchemy import delete
from sqlalchemy.orm import Session
from structlog import get_logger

from app import crud
from app.api.common.pagination import PaginatedQueryParams
from app.api.dependencies.school import get_school_from_path
from app.api.dependencies.security import get_current_active_user_or_service_account
from app.db.session import get_session
from app.models import CollectionItem, School
from app.permissions import Permission
from app.schemas.collection import CollectionItemBrief, CollectionUpdate, CollectionUpdateType
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
    collection_items = session.scalars(
        school.collection.statement.offset(pagination.skip).limit(pagination.limit)
    ).all()
    logger.debug("Loading collection", collection_size=len(collection_items))
    return collection_items


@router.post(
    "/school/{country_code}/{school_id}/collection",
)
async def set_school_collection(
        collection_data: List[EditionCreateIn],
        school: School = Permission("batch", get_school_from_path),
        account = Depends(get_current_active_user_or_service_account),
        session: Session = Depends(get_session)
):
    """
    Replace a school library collection entirely
    """
    logger.info("Resetting the entire collection for school", school=school, account=account)
    session.execute(delete(CollectionItem).where(CollectionItem.school == school))
    session.commit()

    await add_editions_to_collection(session, collection_data, school, account)

    return {
        'msg': "updated"
    }


@router.put("/school/{country_code}/{school_id}/collection",)
async def update_school_collection(
    collection_update_data: List[CollectionUpdate],
    school: School = Permission("batch", get_school_from_path),
    account = Depends(get_current_active_user_or_service_account),
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
    - `update` - still need to work this one out

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
    skipped_edditions: List[str] = []

    for update in collection_update_data:
        if update.action == CollectionUpdateType.REMOVE:
            isbns_to_remove.append(update.ISBN)
        elif update.action == CollectionUpdateType.ADD:
            if update.edition_info is None:
                # this is a bit hacky
                update.edition_info = EditionCreateIn.parse_obj(crud.edition.get(session, id=update.ISBN))

            if update.edition_info is None:
                # If update.edition_info is still None then the caller didn't give us information, and we don't
                # have this edition in the database. We will skip and report this to the caller.
                skipped_edditions.append(update.ISBN)
            else:
                logger.info("Edition to add", new_edition=update.edition_info)
                editions_to_add.append(update.edition_info)
        else:
            raise NotImplemented("TODO, work out what updating a collection looks like...")

    if len(isbns_to_remove) > 0:
        logger.info(f"Removing {len(isbns_to_remove)} items from collection")

        editions = session.scalars(
            crud.edition.get_multi_query(session, ids=isbns_to_remove)
        )

        edition_ids = [e.id for e in editions]

        logger.info("Editions to delete", ids=edition_ids)

        stmt = delete(CollectionItem).where(CollectionItem.school_id == school.id).where(
            CollectionItem.edition_id.in_(edition_ids))
        session.execute(stmt)
        session.commit()

    if len(editions_to_add) > 0:
        logger.info(f"Adding {len(editions_to_add)} editions to collection")

        await add_editions_to_collection(session, editions_to_add, school, account)


    return {
        'msg': "updated",
        "skipped": skipped_edditions
    }