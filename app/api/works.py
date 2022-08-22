from typing import List, Optional

from fastapi import APIRouter, Depends, Path
from fastapi.params import Query
from fastapi_permissions import All, Allow, Authenticated
from sqlalchemy import func
from sqlalchemy.orm import Session
from structlog import get_logger

from app import crud
from app.api.common.pagination import PaginatedQueryParams
from app.api.dependencies.security import get_current_active_user_or_service_account
from app.db.session import get_session
from app.models import Work
from app.models.edition import Edition
from app.models.work import WorkType
from app.permissions import Permission
from app.schemas.work import WorkBrief, WorkDetail, WorkUpdateIn

"""
Access control rules applying to all Works endpoints.

No further access control is applied on a per Work basis.
"""
bulk_work_access_control_list = [
    (Allow, "role:admin", All),
    (Allow, "role:educator", All),
    (Allow, Authenticated, "read"),
]

router = APIRouter(
    tags=["Books"], dependencies=[Depends(get_current_active_user_or_service_account)]
)

logger = get_logger()


def get_work(
    work_id: int = Path(
        ...,
        description="Identifier for a unique creative work in the Wriveted database",
    ),
    session: Session = Depends(get_session),
) -> Work:
    return crud.work.get_or_404(db=session, id=work_id)


@router.get(
    "/works",
    response_model=List[WorkBrief],
)
async def get_works(
    query: Optional[str] = Query(None, description="Query string"),
    isbn: Optional[str] = Query(None, description="Isbn"),
    type: Optional[WorkType] = Query(WorkType.BOOK),
    pagination: PaginatedQueryParams = Depends(),
    session: Session = Depends(get_session),
):
    works_query = crud.work.get_all_query(session).where(Work.type == type)

    if query is not None:
        works_query = works_query.where(func.lower(Work.title).contains(query.lower()))

    if isbn is not None:
        works_query = works_query.where(Work.editions.any(Edition.isbn == isbn))
    else:
        # Ensure there is one or more editions...
        works_query = works_query.where(Work.editions.any())

    works = (
        session.execute(
            crud.work.apply_pagination(
                works_query, skip=pagination.skip, limit=pagination.limit
            )
        )
        .scalars()
        .all()
    )

    output = []
    for work in works:
        brief = {}
        brief["id"] = work.id
        brief["type"] = work.type
        brief["title"] = work.title
        brief["authors"] = [
            {
                "id": author.id,
                "first_name": author.first_name,
                "last_name": author.last_name,
            }
            for author in work.authors
        ]
        output.append(brief)

    return output
    # return crud.work.apply_pagination(works_query, skip=pagination.skip, limit=pagination.limit)


@router.get("/work/{work_id}", response_model=WorkDetail)
async def get_work_by_id(work: Work = Depends(get_work)):
    return work


@router.patch(
    "/work/{work_id}",
    response_model=WorkDetail,
    dependencies=[
        Permission("update", bulk_work_access_control_list),
    ],
)
async def update_work(
    changes: WorkUpdateIn,
    work_orm: Work = Depends(get_work),
    session: Session = Depends(get_session),
):
    logger.info("Updating work", target_work=work_orm, changes=changes)
    if changes.labelset is not None:
        labelset_update = changes.labelset
        logger.info("Updating labels", label_updates=labelset_update)
        labelset = crud.labelset.get_or_create(session, work_orm, False)
        labelset = crud.labelset.patch(session, labelset, labelset_update, False)

        del changes.labelset
    updated = crud.work.update(db=session, db_obj=work_orm, obj_in=changes)
    logger.info("Updated work", updated=updated)
    return updated
