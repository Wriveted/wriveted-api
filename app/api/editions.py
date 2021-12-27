from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from structlog import get_logger

from app import crud
from app.api.common.pagination import PaginatedQueryParams
from app.db.session import get_session
from app.models import Edition
from app.models.work import WorkType
from app.schemas.edition import EditionDetail, EditionBrief, EditionCreateIn
from app.schemas.work import WorkCreateIn

logger = get_logger()
router = APIRouter(
    tags=["Books"]
)


@router.get("/editions", response_model=List[EditionBrief])
async def get_editions(
        work_id: Optional[str] = Query(None, description="Filter editions by work"),
        query: Optional[str] = Query(None, description="Query string"),
        pagination: PaginatedQueryParams = Depends(),
        session: Session = Depends(get_session)
):
    if work_id is not None:
        work = crud.work.get_or_404(session, id=work_id)
        return work.editions[pagination.skip:pagination.skip + pagination.limit]
    elif query is not None:
        statement = crud.edition.get_all_query(session).where(Edition.title.match(query))
        return session.execute(statement).scalars().all()
    else:
        return crud.edition.get_all(session, skip=pagination.skip, limit=pagination.limit)


@router.get("/edition/{isbn}", response_model=EditionDetail)
async def get_book_by_isbn(isbn: str, session: Session = Depends(get_session)):
    return crud.edition.get_or_404(db=session, id=isbn)


@router.post("/edition", response_model=EditionDetail)
async def add_edition(
        edition_data: EditionCreateIn,
        session: Session = Depends(get_session)
):
    return crud.edition.create_new_edition(session, edition_data)


@router.post("/editions")
async def bulk_add_editions(
        bulk_edition_data: List[EditionCreateIn],
        session: Session = Depends(get_session)
):
    editions = crud.edition.create_in_bulk(session, bulk_edition_data=bulk_edition_data)

    return {
        "msg": f"Bulk load of {len(editions)} editions complete"
    }


