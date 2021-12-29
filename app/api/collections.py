import datetime
from typing import List

from fastapi import APIRouter, Depends, Query, HTTPException, Path, Security
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from structlog import get_logger

from app import crud
from app.api.common.pagination import PaginatedQueryParams
from app.api.dependencies.school import get_school_from_path
from app.api.dependencies.security import get_current_active_user, get_current_active_user_or_service_account, \
    get_account_allowed_to_update_school
from app.db.session import get_session
from app.models import CollectionItem, Event, School, Edition
from app.schemas.collection import CollectionItemBrief, CollectionUpdate, CollectionUpdateType
from app.schemas.edition import EditionCreateIn
from app.services.events import create_event

logger = get_logger()

router = APIRouter(
    tags=["Schools"],
    dependencies=[
        Security(get_current_active_user_or_service_account)
    ]
)


@router.get("/school/{country_code}/{school_id}/collection",
            response_model=List[CollectionItemBrief])
async def get_school_collection(
        country_code: str = Path(...,
                                 description="ISO 3166-1 Alpha-3 code for a country. E.g New Zealand is NZL, and Australia is AUS"),
        school_id: str = Path(..., description="Official school Identifier. E.g in ACARA ID"),
        pagination: PaginatedQueryParams = Depends(),
        session: Session = Depends(get_session)
):
    school = crud.school.get_by_official_id_or_404(
        db=session,
        country_code=country_code,
        official_id=school_id
    )
    collection_items = session.scalars(
        school.collection.statement.offset(pagination.skip).limit(pagination.limit)
    ).all()
    logger.debug("Loading collection", collection_size=len(collection_items))
    return collection_items


@router.post(
    "/school/{country_code}/{school_id}/collection",
    dependencies=[
        Security(get_account_allowed_to_update_school),
    ]
)
async def set_school_collection(
        collection_data: List[EditionCreateIn],
        school: School = Depends(get_school_from_path),
        account = Depends(get_account_allowed_to_update_school),
        session: Session = Depends(get_session)
):
    """
    Replace a school library collection entirely
    """
    logger.info("Resetting the entire collection for school", school=school, account=account)
    session.execute(delete(CollectionItem).where(CollectionItem.school == school))

    school.collection = []

    # get all the existing editions in one query
    isbns = {e.ISBN for e in collection_data if len(e.ISBN) > 0}
    existing_editions = crud.edition.get_multi(session, ids=isbns)
    logger.info(f"Got {len(existing_editions)} existing editions")
    existing_isbns = {e.ISBN for e in existing_editions}
    isbns_to_create = isbns.difference(existing_isbns)

    logger.info(f"Will have to create {len(isbns_to_create)} new editions")
    new_edition_data = [data for data in collection_data if data.ISBN in isbns_to_create]
    crud.edition.create_in_bulk(session, bulk_edition_data=new_edition_data)
    logger.info("Created new editions")

    create_event(
        session=session,
        title="Updating collection",
        description=f"Updating {len(existing_editions)} existing editions, adding {len(isbns_to_create)} new editions",
        school=school,
        account=account
    )

    # Now all editions should exist
    for edition in crud.edition.get_multi(session, ids=isbns):
        school.collection.append(
            CollectionItem(
                edition=edition,
                info={
                    "Updated": str(datetime.datetime.utcnow())
                },
            )
        )
    logger.info("Commiting collection to database")

    session.add(school)
    session.commit()

    return {
        'msg': "updated"
    }



@router.put(
    "/school/{country_code}/{school_id}/collection",
    dependencies=[
        Security(get_account_allowed_to_update_school),
    ]
)
async def update_school_collection(
        collection_update_data: List[CollectionUpdate],
        school: School = Depends(get_school_from_path),
        account = Depends(get_account_allowed_to_update_school),
        session: Session = Depends(get_session)
):
    """
    Update a school library collection with a list of changes.
    """
    logger.info("Updating collection for school", school=school, account=account)

    isbns_to_delete = []

    for update in collection_update_data:
        if update.action == CollectionUpdateType.REMOVE:
            isbns_to_delete.append(update.ISBN)

        else:
            raise NotImplemented("TODO...")

    if len(isbns_to_delete) > 0:
        logger.info(f"Removing {len(isbns_to_delete)} items from collection")

        editions = session.scalars(
            crud.edition.get_multi_query(session, ids=isbns_to_delete)
        )

        edition_ids = [e.id for e in editions]

        logger.info("Editions to delete", ids=edition_ids)

        stmt = delete(CollectionItem).where(CollectionItem.school_id == school.id).where(
            CollectionItem.edition_id.in_(edition_ids))
        session.execute(stmt)
        session.commit()


