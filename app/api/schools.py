from typing import List

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi_permissions import Allow, Authenticated, has_permission, Deny
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from structlog import get_logger

from app import crud
from app.api.common.pagination import PaginatedQueryParams

from app.api.dependencies.security import get_current_active_superuser_or_backend_service_account, \
    get_current_active_user_or_service_account, \
    get_active_principals
from app.db.session import get_session
from app.models import School
from app.permissions import Permission
from app.schemas.school import SchoolBrief, SchoolDetail, SchoolCreateIn, SchoolUpdateIn
from app.api.dependencies.school import get_school_from_path

logger = get_logger()

router = APIRouter(
    tags=["Schools"],
    dependencies=[
        Security(get_current_active_user_or_service_account)
    ]
)


bulk_school_access_control_list = [
    (Allow, Authenticated, "read"),
    (Allow, "role:admin", "create"),
    (Allow, "role:admin", "batch"),

    # Should we let LMS accounts create new schools?
    (Deny, "role:lms", "create"),
    (Deny, "role:lms", "batch"),
]


@router.get(
    "/schools",
    response_model=List[SchoolBrief],
    dependencies=[
        # allow batch schools operations for any Authenticated user
        # that has the "read" permission - added in the school ACL.
        # Note we also filter the schools given the principals' permission
        # to ensure only schools that the account is allowed to see are
        # returned. Ref: https://github.com/holgi/fastapi-permissions/issues/3
        Permission("read", bulk_school_access_control_list)
    ]
)
async def get_schools(
        pagination: PaginatedQueryParams = Depends(),
        session: Session = Depends(get_session),
        principals: List = Depends(get_active_principals),
):
    """
    List of schools the current account has permission to view.
    """

    schools = crud.school.get_all(session, skip=pagination.skip, limit=pagination.limit)
    allowed_schools = [school for school in schools
                       if has_permission(principals, "read", school)]

    logger.debug(f"Returning {len(allowed_schools)}")
    return allowed_schools


@router.get("/school/{country_code}/{school_id}", response_model=SchoolDetail)
async def get_school(school: School = Permission("read", get_school_from_path)):
    """
    Detail on a particular school
    """
    return school


@router.post(
    "/schools",
    dependencies=[
        Permission('batch', bulk_school_access_control_list),
    ]
)
async def bulk_add_schools(
        schools: List[SchoolCreateIn],
        session: Session = Depends(get_session)
):
    """Bulk API to add schools"""

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
        Permission('create', bulk_school_access_control_list),
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
    response_model=SchoolDetail
)
async def update_school(
        school_update_data: SchoolUpdateIn,
        school: School = Permission("update", get_school_from_path),
        account=Depends(get_current_active_user_or_service_account),
        session: Session = Depends(get_session)
):
    logger.info("School update", school=school, account=account)
    return crud.school.update(db=session, obj_in=school_update_data, db_obj=school)
