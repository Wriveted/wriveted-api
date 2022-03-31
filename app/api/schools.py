from typing import List, Optional, Union

from fastapi import APIRouter, Depends, HTTPException, Security, Query
from fastapi_permissions import Allow, Authenticated, Deny, has_permission
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette import status
from structlog import get_logger

from app import crud
from app.api.common.pagination import PaginatedQueryParams

from app.api.dependencies.security import (
    get_active_principals,
    get_current_active_user_or_service_account,
    get_current_user,
)
from app.db.session import get_session
from app.models import School, ServiceAccount, EventLevel
from app.models.user import User
from app.permissions import Permission
from app.schemas.school import (
    SchoolBookbotInfo,
    SchoolBrief,
    SchoolDetail,
    SchoolCreateIn,
    SchoolPatchOptions,
    SchoolSelectorOption,
    SchoolUpdateIn,
)
from app.api.dependencies.school import (
    get_school_from_wriveted_id,
    get_school_from_raw_id,
)
from app.services.events import create_event
from app.services.experiments import get_experiments

logger = get_logger()

router = APIRouter(
    tags=["Schools"],
    dependencies=[Security(get_current_active_user_or_service_account)],
)

public_router = APIRouter(tags=["Public", "Schools"])

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
    ],
)
async def get_schools(
    country_code: Optional[str] = Query(None, description="Filter schools by country"),
    state: Optional[str] = Query(None, description="Filter schools by state"),
    postcode: Optional[str] = Query(None, description="Filter schools by postcode"),
    q: Optional[str] = Query(None, description="Filter schools by name"),
    is_active: Optional[bool] = Query(
        None, description="Return active or inactive schools. Default is all."
    ),
    official_identifier: Optional[str] = Query(
        None,
        description="Official identifier for the school - Country specific and usually government issued",
    ),
    pagination: PaginatedQueryParams = Depends(),
    principals: List = Depends(get_active_principals),
    session: Session = Depends(get_session),
):
    """
    List of schools showing only publicly available information.
    Available to any valid user, primarily for selection upon signup.

    Provide any of country code, state/region, postcode, and/or school name query to further filter the schools.
    Admins can also optionally filter active/inactive schools using the "is_active" query parameter.
    """
    admin = has_permission(principals, "details", bulk_school_access_control_list)

    schools = crud.school.get_all_with_optional_filters(
        session,
        country_code=country_code,
        state=state,
        postcode=postcode,
        query_string=q,
        is_active=is_active if admin else None,
        official_identifier=official_identifier,
        skip=pagination.skip,
        limit=pagination.limit,
    )

    logger.debug(f"Returning {len(schools)} schools")

    if not admin:
        for school in schools:
            school.state = None

    return schools


@router.get("/school/{wriveted_identifier}", response_model=SchoolDetail)
async def get_school(school: School = Permission("read", get_school_from_wriveted_id)):
    """
    Detail on a particular school
    """
    return school


@public_router.get("/school/{wriveted_identifier}/exists")
async def school_exists(school: School = Depends(get_school_from_wriveted_id)):
    """
    Whether a school exists. Used for the publicly-accessible Bookbot chat links.
    """
    # dependency will automatically 404 if school doesn't exist
    return True


@public_router.get("/school/{wriveted_identifier}/bot")
async def get_school_bookbot_type(
    school: School = Depends(get_school_from_wriveted_id),
):
    """
    Returns the bookbot type for a school, i.e. whether they've opted for Huey's Collection,
    or their own. Used for the publicly-accessible Bookbot chat links.
    """
    # dependency will automatically 404 if school doesn't exist
    return school.bookbot_type


# Intended to be deprecated if wriveted_identifier is promoted to primary key
@router.get("/school_raw/{id}", response_model=SchoolBookbotInfo, deprecated=True)
async def get_school(school: School = Permission("read", get_school_from_raw_id)):
    """
    Detail on a particular school, accessed via raw sql id (integer)
    """
    return school


@router.get("/school/{wriveted_identifier}/bookbot", response_model=SchoolBookbotInfo)
async def get_school(school: School = Permission("read", get_school_from_wriveted_id)):
    """
    Retrieve bookbot related info on a particular school.
    """
    return school


@router.patch("/school/{wriveted_identifier}/admin")
async def bind_school(
    school: School = Permission("bind", get_school_from_wriveted_id),
    user: User = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """
    Binds the current user to a school as its administrator.
    Will fail if target school already has an admin.
    """
    if school.admin is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "School already bound to an admin user."
        )

    school.admin_id = user.id
    user.school_id_as_admin = school.id
    session.commit()

    return school.admin_id


@router.patch("/school/{wriveted_identifier}")
async def update_school_extras(
    patch: SchoolPatchOptions,
    school: School = Permission("update", get_school_from_wriveted_id),
    account: Union[User, ServiceAccount] = Depends(
        get_current_active_user_or_service_account
    ),
    session: Session = Depends(get_session),
):
    """
    Optional patch updates to less-essential parts of a school object.
    Only available to users with the "update" permission for the
    selected school; i.e. superusers, and its admin/owner.
    """
    output = {}

    if patch.status:
        if patch.status != school.state:
            create_event(
                session=session,
                title=f"School account made {patch.status.upper()}",
                description=f"School '{school.name}' status updated to {patch.status.upper()}",
                school=school,
                account=account,
            )
        output["original_status"] = school.state
        school.state = patch.status
        output["new_status"] = school.state
    if patch.bookbot_type:
        output["original_bookbot_type"] = school.bookbot_type
        school.bookbot_type = patch.bookbot_type
        output["new_bookbot_type"] = school.bookbot_type

    if patch.lms_type:
        output["original_lms_type"] = school.lms_type
        school.lms_type = patch.lms_type
        output["new_bookbot_type"] = school.lms_type

    session.commit()

    return output


@router.post(
    "/schools",
    dependencies=[
        Permission("batch", bulk_school_access_control_list),
    ],
)
async def bulk_add_schools(
    schools: List[SchoolCreateIn],
    account: Union[User, ServiceAccount] = Depends(
        get_current_active_user_or_service_account
    ),
    session: Session = Depends(get_session),
):
    """Bulk API to add schools"""

    new_schools = [
        crud.school.create(db=session, obj_in=school_data, commit=False)
        for school_data in schools
    ]

    for school in new_schools:
        school.info["experiments"] = get_experiments(school=school)

    create_event(
        session=session,
        title="Bulk created schools",
        description=f"Added {len(new_schools)} schools to database.",
        properties={
            'identifiers': [s.wriveted_identifier for s in new_schools]
        },
        account=account,
        commit=False,
    )
    try:
        session.commit()
        return {"msg": f"Added {len(new_schools)} new schools"}
    except:
        logger.warning("there was an issue importing bulk school data")
        raise HTTPException(500, "Error bulk importing schools")


@router.post(
    "/school",
    dependencies=[
        Permission("create", bulk_school_access_control_list),
    ],
    response_model=SchoolDetail,
)
async def add_school(
    school: SchoolCreateIn,
    account: Union[User, ServiceAccount] = Depends(
        get_current_active_user_or_service_account
    ),
    session: Session = Depends(get_session),
):
    try:
        school_orm = crud.school.create(db=session, obj_in=school, commit=False)
        school_orm.info["experiments"] = get_experiments(school=school_orm)
        session.commit()
        create_event(
            session=session,
            title="New school created",
            description=f"{account.name} created school '{school.name}'",
            school=school_orm,
            account=account,
        )
        return school_orm
    except IntegrityError as e:
        logger.warning("Database integrity error while adding school", exc_info=e)
        raise HTTPException(
            status_code=422,
            detail="Couldn't add school to database. It might already exist? Check the country code.",
        )


@router.put("/school/{wriveted_identifier}", response_model=SchoolDetail)
async def update_school(
    school_update_data: SchoolUpdateIn,
    school: School = Permission("update", get_school_from_wriveted_id),
    account=Depends(get_current_active_user_or_service_account),
    session: Session = Depends(get_session),
):
    create_event(
        session=session,
        title="School Updated",
        description=f"School '{school.name}' in {school.country.name} updated.",
        school=school,
        account=account,
    )
    updated_orm_object = crud.school.update(
        db=session, obj_in=school_update_data, db_obj=school
    )
    return updated_orm_object


@router.delete("/school/{wriveted_identifier}", response_model=SchoolBrief)
async def delete_school(
    school: School = Permission("delete", get_school_from_wriveted_id),
    account=Depends(get_current_active_user_or_service_account),
    session: Session = Depends(get_session),
):
    logger.info("Deleting a school", account=account, school=school)
    create_event(
        session=session,
        title="School Deleted",
        description=f"School {school.name} in {school.country.name} deleted.",
        account=account,
    )
    return crud.school.remove(db=session, obj_in=school)
