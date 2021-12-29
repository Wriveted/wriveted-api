from typing import List

from fastapi import APIRouter, Depends, HTTPException, Security
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from structlog import get_logger

from app import crud
from app.api.common.pagination import PaginatedQueryParams

from app.api.dependencies.security import get_current_active_superuser_or_backend_service_account, get_current_active_user_or_service_account, \
    get_account_allowed_to_update_school
from app.db.session import get_session
from app.models import School
from app.schemas.school import SchoolBrief, SchoolDetail, SchoolCreateIn, SchoolUpdateIn
from app.api.dependencies.school import get_school_from_path

logger = get_logger()

router = APIRouter(
    tags=["Schools"],
    dependencies=[
        Security(get_current_active_user_or_service_account)
    ]
)


@router.get("/schools", response_model=List[SchoolBrief])
async def get_schools(
        pagination: PaginatedQueryParams = Depends(),
        session: Session = Depends(get_session)
):
    return crud.school.get_all(session, skip=pagination.skip, limit=pagination.limit)


@router.get("/school/{country_code}/{school_id}", response_model=SchoolDetail)
async def get_school(school: School = Depends(get_school_from_path)):
    return school


@router.post(
    "/schools",
    dependencies=[
        Depends(get_current_active_superuser_or_backend_service_account)
    ]
)
async def bulk_add_schools(
        schools: List[SchoolCreateIn],
        session: Session = Depends(get_session)
):
    logger.info("Bulk adding schools")
    # Create a dict for each school
    new_schools = [
        crud.school.create(
            db=session,
            obj_in=school_data,
            commit=False
        )
        for school_data in schools]
    logger.debug(f"created {len(new_schools)} school orm objects")
    try:
        session.commit()
        logger.debug("committed now school orm objects")
        return {"msg": f"Added {len(new_schools)} new schools"}
    except:
        logger.warning("there was an issue importing bulk school data")
        raise HTTPException(500, "Error bulk importing schools")


@router.post(
    "/school",
    dependencies=[
        Depends(get_current_active_superuser_or_backend_service_account)
    ],
    response_model=SchoolDetail
)
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


@router.put(
    "/school/{country_code}/{school_id}",
    response_model=SchoolDetail)
async def update_school(
        school_update_data: SchoolUpdateIn,
        school = Depends(get_school_from_path),
        account = Depends(get_account_allowed_to_update_school),
        session: Session = Depends(get_session)
):
    logger.info("School update", account=account, school=school)
    return crud.school.update(db=session, obj_in=school_update_data, db_obj=school)

