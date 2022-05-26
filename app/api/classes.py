from typing import List, Optional, Union
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.params import Param, Query
from fastapi_permissions import Allow, Authenticated, has_permission, All, Deny
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette import status
from structlog import get_logger

from app import crud
from app.api.common.pagination import PaginatedQueryParams
from app.api.dependencies.booklist import get_booklist_from_wriveted_id
from app.api.dependencies.classes import get_class_from_wriveted_id, get_school_from_class_wriveted_id
from app.api.dependencies.school import get_school_from_wriveted_id
from app.api.dependencies.security import (
    get_active_principals,
    get_current_active_user_or_service_account,
)
from app.db.session import get_session
from app.models import BookList, ServiceAccount, User, School
from app.models.booklist import ListType
from app.permissions import Permission
from app.schemas.classes import ClassBriefWithJoiningCode, ClassCreateIn, ClassListResponse, ClassDetail, ClassBrief, \
    ClassUpdateIn

from app.schemas.pagination import Pagination

logger = get_logger()


router = APIRouter(
    tags=["Schools"],
    dependencies=[Security(get_current_active_user_or_service_account)],
)

"""
Bulk access control rules apply to calling the create and get classes endpoints.

Further access control is applied inside each endpoint.
"""
bulk_class_access_control_list = [
    (Allow, "role:admin", All),
    (Allow, "role:teacher", All),
    (Allow, "role:student", "read"),
]


@router.get(
    "/classes",
    response_model=ClassListResponse,
    dependencies=[
        Permission("read", bulk_class_access_control_list),
    ]
)
async def get_filtered_classes(
    school_id: UUID = Query(None, description="Filter classes from a particular school"),
    query: str = Query(None, description="Search for class by name"),
    pagination: PaginatedQueryParams = Depends(),
    principals: List = Depends(get_active_principals),
    session: Session = Depends(get_session),
):
    """
    Retrieve a filtered list of classes.

    🔒 The classes returned will be filtered depending on your user account privileges.
    """

    # We will filter the classes before returning them, but we want to avoid
    # querying the database for all classes if the user isn't allowed to get them.
    if school_id is None:
        # Only admins can get classes for all schools
        if "role:admin" not in principals:
            logger.warning("Denying request by non admin user for all classes")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"The current account is not allowed to request all classes."
                       f" Try filtering by your school.",
            )

        school = None
    else:
        school = crud.school.get_by_wriveted_id_or_404(
            db=session, wriveted_id=school_id
        )
        if not has_permission(principals, "read", school):
            logger.warning("Lack of read permission on school", target_school=school)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"The current account is not allowed to view classes associated with that school",
            )
    # At this point we know that we have either a school id, or the request is from an admin
    # In both cases we are allowed to "read" the school.

    # # TODO: Actually get the classes
    # class_list = crud.classes.get_all_with_optional_filters(
    #     session,
    #     query_string=query,
    #     school=school,
    #     skip=pagination.skip,
    #     limit=pagination.limit,
    # )
    #
    # # We may not need this - we could assume we have class read permission via the school
    # filtered_class_list = [c for c in class_list if has_permission(principals, "read", c)]
    filtered_class_list = []

    return ClassListResponse(
        pagination=Pagination(**pagination.to_dict(), total=None),
        data=filtered_class_list
    )


@router.post(
    "/school/{wriveted_identifier}/class",
    dependencies=[
        Permission("create", bulk_class_access_control_list),
    ],
    response_model=ClassBriefWithJoiningCode,
)
async def add_class(
    class_data: ClassCreateIn,
    school: School = Permission("update", get_school_from_wriveted_id),
    account: Union[User, ServiceAccount] = Depends(
        get_current_active_user_or_service_account
    ),
    session: Session = Depends(get_session),
):
    logger.info("Creating a class", school=school)
    new_class_orm = crud.classes.create(db=session, obj_in=class_data)
    crud.event.create(
        session=session,
        title="New class created",
        description=f"{account.name} created class '{new_class_orm.name}'",
        school=school,
        account=account,
    )
    return new_class_orm


@router.get(
    "/class/{wriveted_identifier}",
    response_model=ClassDetail,
    dependencies=[
        Permission("read", get_school_from_class_wriveted_id)
    ]
)
async def get_class_detail(
    class_orm: ClassGroup = Permission("read", get_class_from_wriveted_id),
):
    return class_orm


@router.patch(
    "/class/{wriveted_identifier}",
    response_model=ClassDetail,
)
async def update_class(
    changes: ClassUpdateIn,
    class_orm: ClassGroup = Permission("update", get_class_from_wriveted_id),
    school: School = Permission("read", get_school_from_class_wriveted_id),
    session: Session = Depends(get_session),
):
    logger.debug("Updating class", target_class=class_orm)
    updated_class = crud.classes.update(db=session, db_obj=class_orm, obj_in=changes)
    return updated_class


@router.delete(
    "/class/{wriveted_identifier}",
    response_model=ClassBrief,
)
async def delete_class(
    class_orm: ClassGroup = Permission("delete", get_class_from_wriveted_id),
    school: School = Permission("update", get_school_from_class_wriveted_id),
    account=Depends(get_current_active_user_or_service_account),
    session: Session = Depends(get_session),
):
    """
    Delete a class.

    🔒 caller needs `delete` permission on the class, and `update` permission
    on the school.
    """
    crud.event.create(
        session=session,
        title="Class Deleted",
        description=f"Class {class_orm.name} in {school.name} deleted.",
        account=account,
        school=school
    )
    return crud.classes.remove(db=session, obj_in=school)
