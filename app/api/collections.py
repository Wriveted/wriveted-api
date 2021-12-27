import datetime
from typing import List

from fastapi import APIRouter, Depends, Query, HTTPException, Path
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from structlog import get_logger

from app import crud
from app.api.common.pagination import PaginatedQueryParams
from app.db.session import get_session
from app.models import CollectionItem
from app.schemas.collection import SchoolCollection
from app.schemas.edition import EditionCreateIn

logger = get_logger()

router = APIRouter(
    tags=["Schools"]
)


@router.get("/school/{country_code}/{school_id}/collection",
            response_model=SchoolCollection)
async def get_school_collection(
        country_code: str = Path(...,
                                 description="ISO 3166-1 Alpha-3 code for a country. E.g New Zealand is NZL, and Australia is AUS"),
        school_id: str = Path(..., description="Official school Identifier. E.g in ACARA ID"),
        session: Session = Depends(get_session)
):
    school = crud.school.get_by_official_id_or_404(
        db=session,
        country_code=country_code,
        official_id=school_id
    )

    return school


@router.post("/school/{country_code}/{school_id}/collection")
async def set_school_collection(
        collection_data: List[EditionCreateIn],
        country_code: str = Path(...,
                                 description="ISO 3166-1 Alpha-3 code for a country. E.g New Zealand is NZL, and Australia is AUS"),
        school_id: str = Path(..., description="Official school Identifier. E.g in ACARA ID"),

        session: Session = Depends(get_session)
):
    # first get the school
    school = crud.school.get_by_official_id_or_404(
        db=session,
        country_code=country_code,
        official_id=school_id
    )
    logger.info("Resetting the entire collection for school", school=school)
    school.collection = []

    # We could probably get all the existing editions in one query
    isbns = {e.ISBN for e in collection_data if len(e.ISBN) > 0}
    existing_editions = crud.edition.get_multi(session, ids=isbns)
    logger.info(f"Got {len(existing_editions)} existing editions")
    existing_isbns = {e.ISBN for e in existing_editions}
    isbns_to_create = isbns.difference(existing_isbns)

    logger.info(f"Will have to create {len(isbns_to_create)} new editions")
    new_edition_data = [data for data in collection_data if data.ISBN in isbns_to_create]
    crud.edition.create_in_bulk(session, bulk_edition_data=new_edition_data)
    logger.info("Created new editions")

    # Now all editions should exist
    for edition in crud.edition.get_multi(session, ids=isbns):
        school.collection.append(
            CollectionItem(
                work=edition.work,
                edition=edition,
                info={
                    "Updated": str(datetime.datetime.utcnow())
                },
            )
        )
    logger.info("Commiting collection to database")
    session.add(school)
    session.commit()
