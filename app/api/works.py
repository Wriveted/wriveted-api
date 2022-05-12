from typing import List, Optional

from fastapi import APIRouter, Depends
from fastapi.params import Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app import crud
from app.api.common.pagination import PaginatedQueryParams
from app.api.dependencies.security import get_current_active_user_or_service_account
from app.db.session import get_session
from app.models import Work
from app.models.edition import Edition
from app.models.work import WorkType
from app.schemas.work import WorkBrief, WorkDetail

router = APIRouter(
    tags=["Books"], dependencies=[Depends(get_current_active_user_or_service_account)]
)


@router.get("/works", response_model=List[WorkBrief])
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
async def get_work_by_id(work_id: int, session: Session = Depends(get_session)):
    return crud.work.get_or_404(db=session, id=work_id)
