from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Security
from sqlalchemy import select
from sqlalchemy.orm import Session
from structlog import get_logger

from app import crud
from app.api.common.pagination import PaginatedQueryParams
from app.api.dependencies.security import get_current_active_user_or_service_account
from app.db.session import get_session
from app.models import Edition
from app.schemas.edition import (
    EditionDetail,
    EditionBrief,
    EditionCreateIn,
    KnownAndTaggedEditionCounts,
)
from app.services.collections import create_missing_editions
from app.services.editions import compare_known_editions, get_definitive_isbn


logger = get_logger()
router = APIRouter(
    tags=["Books"], dependencies=[Security(get_current_active_user_or_service_account)]
)


@router.get("/editions", response_model=List[EditionBrief])
async def get_editions(
    work_id: Optional[str] = Query(None, description="Filter editions by work"),
    query: Optional[str] = Query(None, description="Query string"),
    pagination: PaginatedQueryParams = Depends(),
    session: Session = Depends(get_session),
):
    if work_id is not None:
        work = crud.work.get_or_404(session, id=work_id)
        return work.editions[pagination.skip : pagination.skip + pagination.limit]
    elif query is not None:
        statement = crud.edition.get_all_query(session).where(
            Edition.title.match(query)
        )
        return session.execute(statement).scalars().all()
    else:
        return crud.edition.get_all(
            session, skip=pagination.skip, limit=pagination.limit
        )


@router.post("/editions/compare", response_model=KnownAndTaggedEditionCounts)
async def compare_bulk_editions(
    isbn_list: List[str], session: Session = Depends(get_session)
):
    """
    Compares a list of ISBNs against the db to determine how many are known,
    and how many have been fully tagged and checked.
    The provided list should be a raw JSON list, i.e:

    ```json
    [
        "1234567890",
        "1234567899",
        "1234567898"
    ]
    ```

    """
    known, fully_tagged = await compare_known_editions(session, isbn_list)

    return {
        "num_provided": len(isbn_list),
        "num_known": known,
        "num_fully_tagged": fully_tagged,
    }


@router.get("/edition/{isbn}", response_model=EditionDetail)
async def get_book_by_isbn(isbn: str, session: Session = Depends(get_session)):
    try:
        isbn = get_definitive_isbn(isbn)
        return crud.edition.get_or_404(db=session, id=isbn)
    except:
        raise HTTPException(422, "Invalid isbn")
    

@router.post("/edition", response_model=EditionDetail)
async def add_edition(
    edition_data: EditionCreateIn, session: Session = Depends(get_session)
):
    return crud.edition.create_new_edition(session, edition_data)


@router.post("/editions")
async def bulk_add_editions(
    bulk_edition_data: List[EditionCreateIn], session: Session = Depends(get_session)
):
    isbns, created, existing = await create_missing_editions(
        session, new_edition_data=bulk_edition_data
    )

    return {
        "msg": f"Bulk load of {len(isbns)} editions complete. Created {len(created)} new editions."
    }