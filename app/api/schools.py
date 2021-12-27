from typing import List

from fastapi import APIRouter, Depends, Query, HTTPException, Path
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from structlog import get_logger

from app import crud
from app.api.common.pagination import PaginatedQueryParams
from app.db.session import get_session
from app.schemas.school import SchoolBrief, SchoolDetail, SchoolCreateIn, SchoolUpdateIn

logger = get_logger()

router = APIRouter(
    tags=["Schools"]
)


@router.get("/schools", response_model=List[SchoolBrief])
async def get_schools(
        pagination: PaginatedQueryParams = Depends(),
        session: Session = Depends(get_session)
):
    return crud.school.get_all(session, skip=pagination.skip, limit=pagination.limit)


@router.get("/school/{country-code}/{school-id}", response_model=SchoolDetail)
async def get_school(
        country_code: str = Path(...,
                                 description="ISO 3166-1 Alpha-3 code for a country. E.g New Zealand is NZL, and Australia is AUS"),
        school_id: str = Path(..., description="Official school Identifier. E.g in ACARA ID"),
        session: Session = Depends(get_session)
):
    return crud.school.get_by_official_id_or_404(
        db=session,
        country_code=country_code,
        official_id=school_id
    )


@router.post("/schools")
async def bulk_add_schools(
        schools: List[SchoolCreateIn],
        session: Session = Depends(get_session)
):
    # Create a dict for each school
    bulk_mapping = [s.dict() for s in schools]

    crud.school.create_in_bulk(
        db=session,
        bulk_mappings_in=bulk_mapping
    )
    return "done"


@router.post("/school", response_model=SchoolDetail)
async def add_school(
        school: SchoolCreateIn,
        session: Session = Depends(get_session)
):
    try:
        return crud.school.create(
            db=session,
            obj_in=school
        )
    except IntegrityError as e:
        logger.warning("Database integrity error while adding school", exc_info=e)
        raise HTTPException(
            status_code=422,
            detail="Couldn't add school to database. It might already exist? Check the country code."
        )


@router.put("/school/{country-code}/{school-id}", response_model=SchoolDetail)
async def update_school(
        school: SchoolUpdateIn,
        country_code: str = Path(..., description="ISO 3166-1 Alpha-3 code for a country. E.g New Zealand is NZL, and Australia is AUS"),
        school_id: str = Path(..., description="Official school Identifier. E.g in ACARA ID"),
        session: Session = Depends(get_session)
):
    school_orm = crud.school.get_by_official_id_or_404(
        db=session,
        country_code=country_code,
        official_id=school_id
    )
    return crud.school.update(db=session, obj_in=school, db_obj=school_orm)
