from tokenize import String
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Security, Query
from fastapi_permissions import Allow, Authenticated, Deny, has_permission
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from structlog import get_logger

from app import crud
from app.api.common.pagination import PaginatedQueryParams

from app.api.dependencies.security import get_active_principals, get_current_active_user_or_service_account, get_optional_user
from app.db.session import get_session
from app.models import School
from app.models.school import SchoolState
from app.models.user import User
from app.permissions import Permission
from app.schemas.school import SchoolBrief, SchoolDetail, SchoolCreateIn, SchoolSelectorOption, SchoolStatus, SchoolUpdateIn
from app.api.dependencies.school import get_school_from_path, get_school_from_wriveted_id
from app.services.events import create_event

logger = get_logger()

router = APIRouter(
    tags=["Schools"],
    dependencies=[
        Security(get_current_active_user_or_service_account)
    ]
)

bulk_school_access_control_list = [
    (Allow, Authenticated, "read"),
    # if a user finds their school in the list,
    # proceeding with onboarding will "bind" their account
    # to the selected school, and mark its status as pending
    (Allow, Authenticated, "bind"),
    (Allow, Authenticated, "update"),
    # if a user can't find their school in the list,
    # we need to create a school with their provided details
    (Allow, Authenticated, "create"),
    (Allow, "role:admin", "create"),
    (Allow, "role:admin", "batch"),
    (Allow, "role:admin", "details"),

    (Allow, "role:lms", "read"),
    # The following explicitly blocks LMS accounts from creating new schools
    (Deny, "role:lms", "create"),
    (Deny, "role:lms", "batch"),
]


@router.get(
    "/schools",
    response_model=List[SchoolSelectorOption],
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
        country_code: Optional[str] = Query(None, description="Filter schools by country"),
        state: Optional[str] = Query(None, description="Filter schools by state"),
        postcode: Optional[str] = Query(None, description="Filter schools by postcode"),
        q: Optional[str] = Query(None, description='Filter schools by name'),
        is_active: Optional[bool] = Query(None, description="Return active or inactive schools. Default is all."),
        pagination: PaginatedQueryParams = Depends(),
        principals: List = Depends(get_active_principals),
        session: Session = Depends(get_session)
):
    """
    List of schools showing only publicly available information.
    Available to any valid user, primarily for selection upon signup.

    Provide any of country code, state/region, postcode, and/or school name query to further filter the schools.
    Admins can also opt the "is_active" query.
    """
    admin = has_permission(principals, "details", bulk_school_access_control_list)

    schools = crud.school.get_all_with_optional_filters(
        session,
        country_code=country_code,
        state=state,
        postcode=postcode,
        query_string=q,
        is_active=is_active if admin else None,
        skip=pagination.skip, 
        limit=pagination.limit
    )
    
    logger.debug(f"Returning {len(schools)} schools")

    if not admin :
        for school in schools:
            school.state = None
            
    return schools


@router.get("/school/{country_code}/{school_id}", response_model=SchoolDetail)
async def get_school(school: School = Permission("read", get_school_from_path)):
    """
    Detail on a particular school
    """
    return school


@router.patch(
    "/school/{wriveted_identifier}/admin",
    dependencies=[
        Permission('bind', bulk_school_access_control_list)
    ]
)
async def bind_school(
    school: School = Depends(get_school_from_wriveted_id),
    user: Optional[User] = Depends(get_optional_user),
    session: Session = Depends(get_session)):
    """
    Binds the current user to a school as its administrator.
    Will fail if target school already has an admin.
    """
    if school.admin is not None:
        raise HTTPException(409, "School already bound to an admin user.")

    if user is None:
        raise HTTPException(401, "Couldn't find a user associated with that token.")

    school.admin_id = user.id
    user.school_id_as_admin = school.id
    session.commit()

    return school


@router.patch(
    "/school/{wriveted_identifier}/status",
    dependencies=[
        Permission('update', bulk_school_access_control_list)
    ]
)
async def update_school_status(
    status: SchoolStatus,
    school: School = Permission("update", get_school_from_wriveted_id),    
    session: Session = Depends(get_session)):
    """
    Updates the SchoolState of the school to the input value.
    Only available to users with the "update" principal for the
    selected school; i.e. superusers, and its admin/owner.
    """
    school.state = status.status
    session.commit()

    return { "original_status": status.status, "new_status": school.state }


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


@router.delete(
    "/school/{country_code}/{school_id}",
    response_model=SchoolBrief
)
async def delete_school(
        school: School = Permission("delete", get_school_from_path),
        account=Depends(get_current_active_user_or_service_account),
        session: Session = Depends(get_session)
):
    logger.info("Deleting a school", account=account, school=school)
    create_event(
        session=session,
        title="Deleting school",
        description=f"School {school.name} in {school.country.name} deleted.",
        account=account,
    )
    return crud.school.remove(db=session, obj_in=school)
