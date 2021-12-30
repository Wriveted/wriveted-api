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
    """
    logger.info("Updating collection for school", school=school, account=account)

    isbns_to_remove = []
    editions_to_add: List[EditionCreateIn] = []

    for update in collection_update_data:
        if update.action == CollectionUpdateType.REMOVE:
            isbns_to_remove.append(update.ISBN)
        elif update.action == CollectionUpdateType.ADD:
            if update.edition_info is None:
                # this is a bit hacky
                update.edition_info = EditionCreateIn.parse_obj(crud.edition.get(session, id=update.ISBN))
            logger.info("Edition to add", new_edition=update.edition_info)
            editions_to_add.append(update.edition_info)
        else:
            raise NotImplemented("TODO...")

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
        'msg': "updated"
    }